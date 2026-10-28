"""Generate scores with the same preprocessing/model used by the live application.

Input CSV: image_a,image_b,same_person. Paths are relative to the manifest.
Use separate capture sessions for validation, and a separate held-out manifest.
"""
import argparse
import csv
from pathlib import Path
import cv2
import numpy as np
from src.face_gallery import PIPELINE, extract_embedding


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.manifest.open(newline="", encoding="utf-8-sig") as handle:
        pairs = list(csv.DictReader(handle))
    cache, scored = {}, []
    for row in pairs:
        if row["same_person"] not in {"0", "1"}:
            raise ValueError("same_person must be 0 or 1.")
        paths = [(args.manifest.parent / row[key]).resolve() for key in ("image_a", "image_b")]
        if paths[0] == paths[1]:
            raise ValueError("Do not compare an image with itself.")
        for path in paths:
            if path not in cache:
                image = cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
                try:
                    cache[path] = extract_embedding(image)
                except ValueError as exc:
                    raise ValueError(f"{path.name}: {exc}") from exc
        score = float(np.clip(cache[paths[0]] @ cache[paths[1]], -1, 1))
        scored.append({"similarity": score, "same_person": row["same_person"], "pipeline": PIPELINE})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["similarity", "same_person", "pipeline"])
        writer.writeheader()
        writer.writerows(scored)
    print(f"Scored {len(scored)} labelled pairs. No model training performed.")


if __name__ == "__main__":
    main()
