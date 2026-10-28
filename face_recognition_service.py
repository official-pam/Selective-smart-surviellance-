"""Face enrollment and matching using a fixed DeepFace embedding pipeline."""
from contextlib import closing
import json
import math
import sqlite3
from pathlib import Path
import numpy as np

PIPELINE = "Facenet512:opencv:aligned:cosine:v1"


def normalize(vector):
    value = np.asarray(vector, dtype=float)
    if value.shape != (512,) or not np.isfinite(value).all():
        raise ValueError("Expected one finite 512-dimensional embedding.")
    norm = np.linalg.norm(value)
    if norm <= 0:
        raise ValueError("Embedding must have nonzero norm.")
    return value / norm


def extract_embedding(image_bgr):
    from deepface import DeepFace
    representations = DeepFace.represent(
        img_path=image_bgr, model_name="Facenet512", detector_backend="opencv",
        enforce_detection=True, align=True,
    )
    if len(representations) != 1:
        raise ValueError("Use an image with exactly one detected face.")
    area = representations[0]["facial_area"]
    if min(area["w"], area["h"]) < 80:
        raise ValueError("Face is too small. Move closer and take another picture.")
    return normalize(representations[0]["embedding"])


class FaceGallery:
    def __init__(self, path="embeddings/gallery.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS faces (id INTEGER PRIMARY KEY, name TEXT NOT NULL, pipeline TEXT NOT NULL, embedding TEXT NOT NULL)")

    def enroll(self, name, embeddings):
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError("Enter a name of 1 to 80 characters.")
        vectors = [normalize(v) for v in embeddings]
        if not vectors:
            raise ValueError("Provide at least one face sample.")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executemany("INSERT INTO faces(name,pipeline,embedding) VALUES(?,?,?)",
                           [(name, PIPELINE, json.dumps(v.tolist())) for v in vectors])

    def people(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            return db.execute("SELECT name,COUNT(*) FROM faces WHERE pipeline=? GROUP BY name", (PIPELINE,)).fetchall()

    def delete(self, name):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DELETE FROM faces WHERE name=? AND pipeline=?", (name, PIPELINE))

    def match(self, embedding, threshold, margin=0.05):
        if not math.isfinite(threshold) or not -1 <= threshold <= 1:
            raise ValueError("Threshold must be a finite cosine similarity in [-1, 1].")
        if not math.isfinite(margin) or not 0 <= margin <= 2:
            raise ValueError("Margin must be in [0, 2].")
        query = normalize(embedding)
        with closing(sqlite3.connect(self.path)) as db, db:
            records = db.execute("SELECT name,embedding FROM faces WHERE pipeline=?", (PIPELINE,)).fetchall()
        scores = {}
        for name, vector in records:
            score = float(np.clip(query @ normalize(json.loads(vector)), -1, 1))
            scores[name] = max(scores.get(name, -1.0), score)
        ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
        if not ranked:
            return {"name": "Unknown", "is_known": False, "similarity": None}
        name, similarity = ranked[0]
        separated = len(ranked) == 1 or similarity - ranked[1][1] >= margin
        accepted = similarity >= threshold and separated
        return {"name": name if accepted else "Unknown", "is_known": accepted,
                "similarity": similarity}

