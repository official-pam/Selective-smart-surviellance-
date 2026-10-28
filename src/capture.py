"""
Capture Module
- Scores every frame for best face (sharpness x area x eye bonus)
- Eye detection prioritizes open-eyes photos
- enhance_image improves clarity for alert photos
"""

import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from loguru import logger
from config import CAPTURES_DIR


def enhance_image(image: np.ndarray) -> np.ndarray:
    """Denoise + CLAHE contrast + unsharp sharpen."""
    if image is None or image.size == 0:
        return image
    denoised  = cv2.fastNlMeansDenoisingColored(
        image, None, 6, 6, 7, 21
    )
    lab       = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b   = cv2.split(lab)
    clahe     = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l         = clahe.apply(l)
    enhanced  = cv2.cvtColor(cv2.merge((l,a,b)), cv2.COLOR_LAB2BGR)
    gaussian  = cv2.GaussianBlur(enhanced, (0,0), 2.0)
    sharpened = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)
    return cv2.convertScaleAbs(sharpened, alpha=1.1, beta=10)


class BestFaceCapture:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye.xml"
        )
        self._best_frames:     dict[int, np.ndarray] = {}
        self._best_scores:     dict[int, float]      = {}
        self._best_face_crops: dict[int, np.ndarray] = {}

    def _score_face(self, face_crop: np.ndarray) -> float:
        """Score = area × sharpness × eye_bonus (2x if eyes open)."""
        if face_crop is None or face_crop.size == 0:
            return 0.0
        h, w      = face_crop.shape[:2]
        gray      = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        eyes      = self.eye_cascade.detectMultiScale(
            gray, 1.1, 5, minSize=(15,15)
        )
        eye_bonus = 2.0 if len(eyes) >= 2 else 1.0
        return (w * h) * sharpness * eye_bonus

    def update(self, frame, active_track_ids, tracked_objects):
        for obj in tracked_objects:
            tid          = obj["track_id"]
            x1,y1,x2,y2 = obj["bbox"]
            person_crop  = frame[max(0,y1):y2, max(0,x1):x2]
            if person_crop.size == 0:
                continue

            gray  = cv2.cvtColor(person_crop, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, 1.1, 5, minSize=(30,30)
            )

            # No face — store full frame as fallback
            if len(faces) == 0:
                if tid not in self._best_frames:
                    self._best_frames[tid]    = frame.copy()
                    self._best_scores[tid]    = 0.0
                continue

            for (fx, fy, fw, fh) in faces:
                # Preserve context for the same OpenCV face alignment used at enrollment.
                pad = int(0.25 * max(fw, fh))
                face_crop = person_crop[max(0,fy-pad):fy+fh+pad, max(0,fx-pad):fx+fw+pad]
                if face_crop.size == 0:
                    continue
                score = self._score_face(face_crop)
                if score > self._best_scores.get(tid, -1):
                    self._best_scores[tid]     = score
                    self._best_frames[tid]     = frame.copy()
                    self._best_face_crops[tid] = face_crop.copy()

        # Clean vanished
        for tid in list(self._best_frames.keys()):
            if tid not in active_track_ids:
                self._best_frames.pop(tid, None)
                self._best_scores.pop(tid, None)
                self._best_face_crops.pop(tid, None)

    def get_best_frame(self, tid):
        return self._best_frames.get(tid)

    def get_best_face_crop(self, tid):
        return self._best_face_crops.get(tid)

    def pop_all(self, tid) -> tuple:
        """Return and remove all stored data for this ID."""
        frame = self._best_frames.pop(tid, None)
        crop  = self._best_face_crops.pop(tid, None)
        self._best_scores.pop(tid, None)
        return frame, crop

    def clear(self, tid):
        self._best_frames.pop(tid, None)
        self._best_scores.pop(tid, None)
        self._best_face_crops.pop(tid, None)


def save_visit_image(best_face: np.ndarray,
                     best_frame: np.ndarray,
                     track_id: int,
                     identity: dict,
                     entry_time: str,
                     exit_time: str,
                     duration: float) -> str:
    """
    Save ONE image for EVERY person who enters frame.
    Shows: face crop + status overlay (known/unknown, times, duration).
    Returns saved filepath.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Use best face crop, fall back to full frame
    if best_face is not None:
        h, w = best_face.shape[:2]
        if w < 300:
            scale    = 300 / w
            best_face = cv2.resize(
                best_face,
                (int(w*scale), int(h*scale)),
                interpolation=cv2.INTER_CUBIC
            )
        img = enhance_image(best_face)
    elif best_frame is not None:
        img = enhance_image(best_frame)
    else:
        return None

    # Add info overlay at bottom
    name       = identity.get("name", "UNKNOWN") if identity else "UNKNOWN"
    is_known   = identity.get("is_known", False) if identity else False
    confidence = identity.get("confidence", 0.0) if identity else 0.0

    # Format duration
    mins = int(duration) // 60
    secs = duration % 60
    dur_text = f"{mins}m {secs:.1f}s" if mins > 0 else f"{secs:.1f}s"

    status_color = (0, 200, 0) if is_known else (0, 0, 220)
    status_text  = "KNOWN" if is_known else "UNKNOWN"

    overlay_lines = [
        f"Status   : {status_text}",
        f"Name     : {name}",
        f"Similarity: {confidence / 100:.4f}",
        f"In time  : {entry_time}",
        f"Out time : {exit_time}",
        f"Duration : {dur_text}",
    ]

    line_h    = 22
    padding   = 10
    overlay_h = len(overlay_lines) * line_h + padding * 2
    canvas    = np.zeros(
        (img.shape[0] + overlay_h, max(img.shape[1], 320), 3),
        dtype=np.uint8
    )
    canvas[:img.shape[0], :img.shape[1]] = img

    # Dark overlay panel
    cv2.rectangle(
        canvas,
        (0, img.shape[0]),
        (canvas.shape[1], canvas.shape[0]),
        (20, 20, 20), -1
    )

    # Status bar color line
    cv2.rectangle(
        canvas,
        (0, img.shape[0]),
        (canvas.shape[1], img.shape[0] + 4),
        status_color, -1
    )

    for i, line in enumerate(overlay_lines):
        y = img.shape[0] + padding + (i * line_h) + 12
        cv2.putText(
            canvas, line, (10, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.52,
            (220, 220, 220), 1, cv2.LINE_AA
        )

    filepath = str(
        Path(CAPTURES_DIR) /
        f"visit_ID{track_id}_{timestamp}.jpg"
    )
    cv2.imwrite(filepath, canvas, [cv2.IMWRITE_JPEG_QUALITY, 95])
    logger.success(f"Visit image saved: {filepath}")
    return filepath


def save_alert_images(best_face: np.ndarray,
                      best_frame: np.ndarray,
                      track_id: int) -> dict:
    """
    Save 2 alert images for ≥30s persons:
    1. best_face     → clearest face (open eyes, enhanced)
    2. enhanced_frame → full frame enhanced
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved     = {}

    # Image 1 — best face
    if best_face is not None:
        h, w = best_face.shape[:2]
        if w < 300:
            scale    = 300 / w
            best_face = cv2.resize(
                best_face,
                (int(w*scale), int(h*scale)),
                interpolation=cv2.INTER_CUBIC
            )
        face_path = str(
            Path(CAPTURES_DIR) /
            f"alert_face_ID{track_id}_{timestamp}.jpg"
        )
        cv2.imwrite(face_path, enhance_image(best_face),
                    [cv2.IMWRITE_JPEG_QUALITY, 97])
        saved["best_face"] = face_path
        logger.success(f"Alert face saved: {face_path}")

    # Image 2 — enhanced full frame
    src = best_frame
    if src is not None:
        enhanced_path = str(
            Path(CAPTURES_DIR) /
            f"alert_frame_ID{track_id}_{timestamp}.jpg"
        )
        cv2.imwrite(enhanced_path, enhance_image(src),
                    [cv2.IMWRITE_JPEG_QUALITY, 97])
        saved["enhanced_frame"] = enhanced_path
        logger.success(f"Alert frame saved: {enhanced_path}")

    return saved