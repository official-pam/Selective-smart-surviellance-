from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


class PersonZoneDetector:

    def __init__(
        self,
        model_path,
        tracker_path,
        confidence=0.15,
        zone_id="restricted_zone_1"
    ):

        self.model_path = Path(model_path)
        self.tracker_path = Path(tracker_path)

        self.confidence = confidence
        self.zone_id = zone_id

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"YOLO model not found: {self.model_path}"
            )

        if not self.tracker_path.is_file():
            raise FileNotFoundError(
                f"Tracker configuration not found: {self.tracker_path}"
            )

        self.model = YOLO(str(self.model_path))

        self.previous_zone_state = {}
        self.frame_number = 0
        self.latest_person_crops = {}
        self.latest_tracks = {}

    def reset(self):

        self.previous_zone_state.clear()
        self.frame_number = 0
        self.latest_person_crops.clear()
        self.latest_tracks.clear()

        predictor = getattr(self.model, "predictor", None)
        trackers = getattr(predictor, "trackers", [])

        for tracker in trackers:
            reset_tracker = getattr(tracker, "reset", None)
            if callable(reset_tracker):
                reset_tracker()

    def process_frame(self, frame, zone_points, fps=30.0):

        if frame is None:
            raise ValueError("A valid video frame is required.")

        if len(zone_points) < 3:
            raise ValueError(
                "The restricted zone needs at least 3 points."
            )

        self.frame_number += 1

        zone_polygon = np.asarray(
            zone_points,
            dtype=np.int32
        )

        result = self.model.track(
            source=frame,
            tracker=str(self.tracker_path),
            classes=[0],
            conf=self.confidence,
            persist=True,
            verbose=False
        )[0]

        annotated = frame.copy()

        events = []

        self.latest_person_crops = {}
        self.latest_tracks = {}

        cv2.polylines(
            annotated,
            [zone_polygon],
            True,
            (0, 255, 0),
            2
        )

        cv2.putText(
            annotated,
            "RESTRICTED ZONE",
            tuple(map(int, zone_polygon[0])),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2
        )

        if result.boxes is not None and result.boxes.id is not None:

            boxes = result.boxes.xyxy.cpu().numpy()

            track_ids = (
                result.boxes.id.cpu().numpy().astype(int)
            )

            for box, track_id in zip(boxes, track_ids):

                x1, y1, x2, y2 = map(int, box)

                h, w = frame.shape[:2]

                # Correctly crop the detected person.
                cx1 = max(0, x1)
                cy1 = max(0, y1)

                cx2 = min(w, x2)
                cy2 = min(h, y2)

                if cx2 > cx1 and cy2 > cy1:

                    self.latest_person_crops[int(track_id)] = (
                        frame[cy1:cy2, cx1:cx2].copy()
                    )

                foot_x = (x1 + x2) // 2
                foot_y = y2

                inside_zone = (
                    cv2.pointPolygonTest(
                        zone_polygon,
                        (float(foot_x), float(foot_y)),
                        False
                    ) >= 0
                )

                self.latest_tracks[int(track_id)] = {
                    "box": (x1, y1, x2, y2),
                    "inside_zone": inside_zone,
                }

                previous_state = self.previous_zone_state.get(track_id)

                event_type = None

                # Detect first appearance inside the restricted zone.
                if previous_state is None and inside_zone:
                    event_type = "zone_entry"

                elif previous_state is not None:

                    if not previous_state and inside_zone:
                        event_type = "zone_entry"

                    elif previous_state and not inside_zone:
                        event_type = "zone_exit"

                if event_type:

                    safe_fps = fps if fps and fps > 0 else 30.0

                    events.append({
                        "event": event_type,
                        "track_id": int(track_id),
                        "zone_id": self.zone_id,
                        "frame_number": self.frame_number,
                        "timestamp_seconds": round(
                            self.frame_number / safe_fps,
                            2
                        ),
                        "recorded_at": datetime.now().isoformat(
                            timespec="seconds"
                        )
                    })

                self.previous_zone_state[track_id] = inside_zone

                status = (
                    "INSIDE ZONE"
                    if inside_zone
                    else "OUTSIDE ZONE"
                )

                color = (
                    (0, 0, 255)
                    if inside_zone
                    else (255, 0, 0)
                )

                cv2.rectangle(
                    annotated,
                    (x1, y1),
                    (x2, y2),
                    color,
                    2
                )

                cv2.circle(
                    annotated,
                    (foot_x, foot_y),
                    5,
                    (0, 255, 255),
                    -1
                )

                label = f"ID: {track_id} | {status}"

                cv2.putText(
                    annotated,
                    label,
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    color,
                    2
                )

        cv2.putText(
            annotated,
            f"Frame: {self.frame_number}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        return annotated, events
