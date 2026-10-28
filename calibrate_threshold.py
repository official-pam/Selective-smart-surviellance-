"""Calibrate a decision threshold; model weights remain unchanged."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
from src.face_gallery import PIPELINE, POLICY


def labelled_scores(rows):
    positive, negative = [], []
    for row in rows:
        if row.get("pipeline") != PIPELINE:
            raise ValueError("All scores must use the original application's exact Facenet pipeline.")
        score = float(row["similarity"])
        if row["same_person"] not in ("0", "1", 0, 1):
            raise ValueError("same_person must be 0 or 1.")
        if not math.isfinite(score) or not -1 <= score <= 1:
            raise ValueError("Cosine similarity must be finite and in [-1, 1].")
        (positive if int(row["same_person"]) else negative).append(score)
    if not positive or not negative:
        raise ValueError("Both same-person and different-person pairs are required.")
    return positive, negative


def evaluate(rows, threshold):
    positive, negative = labelled_scores(rows)
    return {"false_accept_rate": sum(s >= threshold for s in negative) / len(negative),
            "false_reject_rate": sum(s < threshold for s in positive) / len(positive),
            "positive_pairs": len(positive), "negative_pairs": len(negative)}


def calibrate(rows, target_far):
    if not math.isfinite(target_far) or not 0 <= target_far <= 1:
        raise ValueError("Target FAR must be finite and in [0, 1].")
    rows = list(rows)
    positive, negative = labelled_scores(rows)
    values = set(positive + negative + [-1.0, 1.0])
    # Include just-above-score boundaries: acceptance uses >=, not >.
    values.update(float(np.nextafter(s, np.inf)) for s in positive + negative if s < 1)
    options = []
    for threshold in sorted(values):
        report = evaluate(rows, threshold)
        if report["false_accept_rate"] <= target_far:
            options.append((report["false_reject_rate"], report["false_accept_rate"], -threshold, threshold, report))
    if not options:
        raise ValueError("No valid threshold meets the empirical target FAR.")
    _, _, _, threshold, metrics = min(options)
    return {"pipeline": PIPELINE, "threshold": threshold, "target_far": target_far,
            "status": "calibrated on supplied pairs; held-out evaluation required",
            "validation": metrics, "margin_status": "not calibrated",
            "note": "Pair verification rates are not live open-set identification accuracy. Correlated pairs are not independent trials."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", help="Output from score_validation_pairs.py")
    parser.add_argument("--target-far", type=float, default=0.01)
    parser.add_argument("--output", type=Path, default=POLICY)
    parser.add_argument("--evaluate", type=Path, help="Evaluate a frozen threshold on held-out scores; never changes the policy")
    args = parser.parse_args()
    with open(args.csv, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if args.evaluate:
        report = json.loads(args.evaluate.read_text(encoding="utf-8"))
        if report["pipeline"] != PIPELINE:
            raise ValueError("Policy pipeline mismatch.")
        print(json.dumps(evaluate(rows, float(report["threshold"])), indent=2))
    else:
        report = calibrate(rows, args.target_far)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
        temporary.replace(args.output)
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
