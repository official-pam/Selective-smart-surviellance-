"""Person detection, ByteTrack association, and zone annotations.

One instance per video stream. Identity labels must come from a separate
recognizer; tracker IDs are temporary associations, not personal identities.
"""
import math
import cv2
import numpy as np
from ultralytics import YOLO
from config import (
    CONFIDENCE_THRESHOLD, PERSON_CLASS_ID, ZONE_ENABLED, ZONE_NORM,
    ALERT_THRESHOLD_SECONDS,
)


class PersonDetectorTracker:
    def __init__(self, model_name="yolov8n.pt"):
        self.model = YOLO(model_name)
        names = self.model.names
        if PERSON_CLASS_ID not in names or str(names[PERSON_CLASS_ID]).lower() != "person":
            raise ValueError("PERSON_CLASS_ID must refer to the person class in these weights.")
        if not 0 < CONFIDENCE_THRESHOLD <= 1:
            raise ValueError("CONFIDENCE_THRESHOLD must be in (0, 1].")
        points = np.asarray(ZONE_NORM, dtype=np.float32)
        if ZONE_ENABLED and (
            points.ndim != 2 or points.shape[1] != 2 or len(points) < 3
            or not np.isfinite(points).all() or np.any(points < 0) or np.any(points > 1)
        ):
            raise ValueError("ZONE_NORM requires at least three normalized (x, y) points.")
        self.frame_count = 0
        self.last_results = []
        self.all_people = []
        self.zone = None
        self._shape = None

    def _build_zone(self, frame):
        height, width = frame.shape[:2]
        self.zone = np.rint(
            np.asarray(ZONE_NORM) * np.array([width - 1, height - 1])
        ).astype(np.int32)
        if abs(cv2.contourArea(self.zone)) < 1:
            raise ValueError("Zone polygon has zero area at this resolution.")
        self._shape = (height, width)

    def in_zone(self, bbox):
        if self.zone is None:
            raise RuntimeError("Build the zone before testing a bounding box.")
        x1, _, x2, y2 = bbox
        return cv2.pointPolygonTest(
            self.zone, (float((x1 + x2) / 2), float(y2)), False
        ) >= 0

    def process_frame(self, frame):
        if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3 or frame.size == 0:
            raise ValueError("Expected a nonempty BGR frame with three channels.")
        self.frame_count += 1
        if ZONE_ENABLED and self._shape != frame.shape[:2]:
            self._build_zone(frame)
        # Avoid returning stale detections for skipped frames.
        results = self.model.track(
            source=frame, persist=True, tracker="bytetrack.yaml",
            classes=[PERSON_CLASS_ID], conf=CONFIDENCE_THRESHOLD, verbose=False,
        )
        people = []
        boxes = results[0].boxes if results else None
        if boxes is not None and boxes.id is not None:
            coordinates = boxes.xyxy.cpu().numpy()
            identifiers = boxes.id.int().cpu().tolist()
            confidences = boxes.conf.cpu().tolist()
            height, width = frame.shape[:2]
            for coords, track_id, confidence in zip(coordinates, identifiers, confidences):
                coords = np.rint(coords).astype(int)
                coords[[0, 2]] = np.clip(coords[[0, 2]], 0, width - 1)
                coords[[1, 3]] = np.clip(coords[[1, 3]], 0, height - 1)
                if coords[2] <= coords[0] or coords[3] <= coords[1]:
                    continue
                people.append({
                    "track_id": track_id, "bbox": coords,
                    "confidence": float(confidence),
                    "in_zone": self.in_zone(coords) if ZONE_ENABLED else True,
                })
        self.all_people = people
        self.last_results = [obj for obj in people if obj["in_zone"]]
        return self.last_results

    def draw_annotations(self, frame, tracked_objects, timer_info, identities=None):
        annotated = frame.copy()
        identities = identities or {}
        if ZONE_ENABLED and self.zone is not None:
            cv2.polylines(annotated, [self.zone], True, (0, 255, 255), 2)
        for obj in self.all_people:
            if not obj["in_zone"]:
                x1, y1, x2, y2 = obj["bbox"]
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (180, 180, 180), 1)
        known = unknown = pending = 0
        for obj in tracked_objects:
            tid = obj["track_id"]
            x1, y1, x2, y2 = map(int, obj["bbox"])
            identity = identities.get(tid)
            elapsed = float(timer_info.get(tid, 0))
            elapsed = max(0.0, elapsed) if math.isfinite(elapsed) else 0.0
            if identity is None:
                pending += 1
                color, label = (0, 255, 255), f"ID:{tid} Identifying..."
            elif identity.get("is_known", False):
                known += 1
                color = (0, 255, 0)
                label = f"ID:{tid} {identity.get('name', 'Known')}"
            else:
                unknown += 1
                color, label = (0, 0, 255), f"ID:{tid} Unknown"
            # Similarity scores are not calibrated probabilities; do not label them '%'.
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            remaining = max(0.0, ALERT_THRESHOLD_SECONDS - elapsed)
            timer = f"{elapsed:.1f}s | " + (f"Alert in {remaining:.1f}s" if remaining else "Threshold reached")
            height, width = annotated.shape[:2]
            for index, text in enumerate((label, timer)):
                text = text.encode("ascii", errors="replace").decode("ascii")
                size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                left = max(0, min(x1, width - size[0] - 6))
                baseline = min(height - 4, max(16, y1 - 24) + 19 * index)
                cv2.rectangle(annotated, (left, baseline - 14),
                              (min(width - 1, left + size[0] + 6), baseline + 4), color, -1)
                cv2.putText(annotated, text, (left + 3, baseline),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        summary = f"In zone: {len(tracked_objects)} | Known: {known} | Unknown: {unknown} | Pending: {pending}"
        cv2.putText(annotated, summary, (10, 28), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 2)
        return annotated
