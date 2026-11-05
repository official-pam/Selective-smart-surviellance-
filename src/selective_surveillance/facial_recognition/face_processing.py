"""Face detection, alignment and SFace embedding extraction."""

from pathlib import Path
import cv2
import numpy as np

from .config import (
    DETECTOR_MODEL,
    RECOGNITION_MODEL,
    MAX_IMAGE_SIDE,
    DETECTION_THRESHOLD,
    NMS_THRESHOLD,
)


class FaceProcessor:
    """Load models once and process one face per input image."""

    def __init__(self, models_dir):
        models_dir = Path(models_dir)

        detector_path = models_dir / DETECTOR_MODEL
        recognition_path = models_dir / RECOGNITION_MODEL

        # Fail clearly if either pretrained model is missing.
        for path in (detector_path, recognition_path):
            if not path.is_file():
                raise FileNotFoundError(f"Missing model: {path}")

        self.detector = cv2.FaceDetectorYN.create(
            str(detector_path), "", (320, 320),
            score_threshold=DETECTION_THRESHOLD,
            nms_threshold=NMS_THRESHOLD
        )

        self.recognizer = cv2.FaceRecognizerSF.create(
            str(recognition_path), ""
        )

    def extract(self, image_bgr):
        """Return a normalized embedding and the aligned BGR face."""

        # OpenCV expects a nonempty, three-channel uint8 BGR image.
        if (
            not isinstance(image_bgr, np.ndarray)
            or image_bgr.size == 0
            or image_bgr.ndim != 3
            or image_bgr.shape[2] != 3
            or image_bgr.dtype != np.uint8
        ):
            raise ValueError("Expected a nonempty uint8 BGR colour image.")

        # Preserve the original proportions while limiting image size.
        height, width = image_bgr.shape[:2]
        scale = min(1.0, MAX_IMAGE_SIDE / max(height, width))

        resized = cv2.resize(
            image_bgr,
            (max(1, round(width * scale)), max(1, round(height * scale)))
        )

        # Detect faces using the resized image's dimensions.
        h, w = resized.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(resized)

        # Avoid choosing an identity from an ambiguous multi-face image.
        if faces is None or len(faces) != 1:
            raise ValueError("Expected exactly one detectable face.")

        # Align and encode using the same image and landmark coordinates.
        aligned = self.recognizer.alignCrop(resized, faces[0])
        vector = self.recognizer.feature(aligned).flatten()

        length = np.linalg.norm(vector)

        if (
            vector.shape != (128,)
            or not np.isfinite(vector).all()
            or length == 0
        ):
            raise ValueError("Invalid SFace embedding.")

        return (vector / length).astype(np.float32), aligned
