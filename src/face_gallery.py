"""Local enrollment and cosine matching for the original 128-value Facenet model."""
from contextlib import closing
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import threading
import cv2
import numpy as np
from config import FACE_SIMILARITY_THRESHOLD, FACE_AMBIGUITY_MARGIN, FACE_MIN_SIZE, FACE_MIN_SHARPNESS

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "embeddings"
GALLERY = DATA / "gallery.sqlite3"
POLICY = DATA / "threshold.json"
PIPELINE = "Facenet128:opencv:aligned:base:l2:cosine:quality-v1"
_MODEL_LOCK = threading.Lock()


def normalize(vector):
    value = np.asarray(vector, dtype=float)
    if value.shape != (128,) or not np.isfinite(value).all():
        raise ValueError("Expected a finite 128-value Facenet embedding; Facenet512 is incompatible.")
    norm = np.linalg.norm(value)
    if norm <= 0:
        raise ValueError("Embedding must have nonzero norm.")
    return value / norm


def extract_embedding(image):
    if not isinstance(image, np.ndarray) or image.ndim != 3 or image.shape[2] != 3 or not image.size:
        raise ValueError("Use a readable colour image.")
    os.environ.setdefault("DEEPFACE_HOME", str(ROOT / ".runtime"))
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    with _MODEL_LOCK:
        from deepface import DeepFace
        faces = DeepFace.represent(img_path=image, model_name="Facenet", detector_backend="opencv",
                                   enforce_detection=True, align=True, normalization="base")
    if len(faces) != 1:
        raise ValueError("Use an image containing exactly one detectable face.")
    area = faces[0]["facial_area"]
    x, y, w, h = (int(area[k]) for k in ("x", "y", "w", "h"))
    crop = image[max(0, y):min(image.shape[0], y+h), max(0, x):min(image.shape[1], x+w)]
    if min(w, h) < FACE_MIN_SIZE or crop.size == 0:
        raise ValueError(f"Face is too small; use at least {FACE_MIN_SIZE} pixels across the face.")
    if cv2.Laplacian(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() < FACE_MIN_SHARPNESS:
        raise ValueError("Face is too blurred. Hold still and improve lighting.")
    return normalize(faces[0]["embedding"])


def load_policy(path=POLICY):
    policy = {"pipeline": PIPELINE, "threshold": FACE_SIMILARITY_THRESHOLD,
              "margin": FACE_AMBIGUITY_MARGIN, "status": "provisional"}
    if not Path(path).exists():
        return policy
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    if report.get("pipeline") != PIPELINE:
        raise ValueError("Calibration uses a different embedding pipeline; recalibrate for Facenet128.")
    threshold = float(report["threshold"])
    if not math.isfinite(threshold) or not -1 <= threshold <= 1:
        raise ValueError("Invalid calibrated threshold.")
    policy.update(report)
    policy["margin"] = FACE_AMBIGUITY_MARGIN  # Pair calibration does not validate this margin.
    return policy


def rank_match(query, records, threshold, margin):
    if not math.isfinite(threshold) or not -1 <= threshold <= 1:
        raise ValueError("Threshold must be in [-1, 1].")
    if not math.isfinite(margin) or not 0 <= margin <= 2:
        raise ValueError("Margin must be in [0, 2].")
    query = normalize(query)
    scores = {}
    for name, vector in records:
        score = float(np.clip(query @ normalize(vector), -1, 1))
        scores[name] = max(scores.get(name, -1.0), score)
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    score = ranked[0][1] if ranked else None
    gap = ranked[0][1] - ranked[1][1] if len(ranked) > 1 else None
    accepted = bool(ranked) and score >= threshold and (gap is None or gap >= margin)
    reason = ("No reference faces are enrolled." if not ranked else
              "Similarity is below the threshold." if score < threshold else
              "The top two identities are too close." if not accepted else "Match accepted.")
    return {"name": ranked[0][0] if accepted else "UNKNOWN", "is_known": accepted,
            "candidate": ranked[0][0] if ranked else None, "similarity": score,
            "threshold": threshold, "margin": margin, "gap": gap, "reason": reason,
            # Compatibility with old event schema. This is NOT a probability.
            "confidence": 100 * score if score is not None else 0.0,
            "scores": [{"Person": n, "Similarity": s} for n, s in ranked]}


class FaceGallery:
    def __init__(self, path=GALLERY):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS faces (id INTEGER PRIMARY KEY, name TEXT NOT NULL, pipeline TEXT NOT NULL, embedding TEXT NOT NULL, sample_hash TEXT)")

    def enroll(self, name, vectors, hashes=None):
        name = name.strip()
        if not name or len(name) > 80 or any(ord(c) < 32 for c in name):
            raise ValueError("Enter a name of 1–80 printable characters.")
        vectors = [normalize(v) for v in vectors]
        if not vectors:
            raise ValueError("Provide at least one face sample.")
        hashes = hashes or [None] * len(vectors)
        if len(hashes) != len(vectors):
            raise ValueError("Sample hashes must match the samples.")
        added = 0
        with closing(sqlite3.connect(self.path)) as db, db:
            for vector, digest in zip(vectors, hashes):
                if digest and db.execute("SELECT 1 FROM faces WHERE name=? AND pipeline=? AND sample_hash=?", (name, PIPELINE, digest)).fetchone():
                    continue
                db.execute("INSERT INTO faces(name,pipeline,embedding,sample_hash) VALUES(?,?,?,?)",
                           (name, PIPELINE, json.dumps(vector.tolist()), digest))
                added += 1
        return added

    def records(self):
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute("SELECT name,embedding FROM faces WHERE pipeline=?", (PIPELINE,)).fetchall()
        return [(name, normalize(json.loads(v))) for name, v in rows]

    def people(self):
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute("SELECT name,COUNT(*) FROM faces WHERE pipeline=? GROUP BY name ORDER BY name", (PIPELINE,)).fetchall()

    def match(self, query):
        policy = load_policy()
        return rank_match(query, self.records(), policy["threshold"], policy["margin"])

    def import_legacy(self, directory):
        added, errors = 0, []
        for path in sorted(Path(directory).glob("*")):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue
            try:
                raw = path.read_bytes()
                image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
                added += self.enroll(path.stem.replace("_", " "), [extract_embedding(image)], [hashlib.sha256(raw).hexdigest()])
            except (ValueError, OSError) as exc:
                errors.append(f"{path.name}: {exc}")
        return added, errors
