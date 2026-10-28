"""Select a cosine threshold using labelled validation-pair scores.

CSV columns: similarity,same_person (0 or 1). Scores must come from this exact
embedding pipeline. This is pair verification calibration, not open-set testing.
"""
import argparse
import csv
import json
import math
from pathlib import Path
from face_recognition_service import PIPELINE


def calibrate(rows, target_far):
    if not 0 <= target_far <= 1:
        raise ValueError("Target FAR must be in [0, 1].")
    positives, negatives = [], []
    for row in rows:
        score, label = float(row["similarity"]), int(row["same_person"])
        if not math.isfinite(score) or not -1 <= score <= 1 or label not in (0, 1):
            raise ValueError("Invalid validation row.")
        (positives if label else negatives).append(score)
    if not positives or not negatives:
        raise ValueError("Supply both same-person and different-person pairs.")
    candidates = sorted(set(positives + negatives + [-1.0, 1.0]))
    options = []
    for threshold in candidates:
        far = sum(s >= threshold for s in negatives) / len(negatives)
        frr = sum(s < threshold for s in positives) / len(positives)
        if far <= target_far:
            options.append((frr, far, -threshold, threshold))
    if not options:
        raise ValueError("No threshold meets the requested empirical FAR.")
    frr, far, _, threshold = min(options)
    return {"pipeline": PIPELINE, "threshold": threshold, "validation_far": far,
            "validation_frr": frr, "positive_pairs": len(positives),
            "negative_pairs": len(negatives), "target_far": target_far}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--target-far", type=float, default=0.01)
    args = parser.parse_args()
    with open(args.csv, newline="", encoding="utf-8") as handle:
        report = calibrate(list(csv.DictReader(handle)), args.target_far)
    output = Path("embeddings/threshold.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
