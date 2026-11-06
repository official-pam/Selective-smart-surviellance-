"""Small, predictable face-image variations for enrollment previews."""

import cv2
import numpy as np


def create_face_augmentations(face_image_bgr: np.ndarray) -> dict[str, np.ndarray]:
    """Return the original aligned face and four mild appearance variations.

    Augmented copies help the enrolled template tolerate small brightness and
    contrast shifts. They are still copies of one capture, not independent
    training or test samples and not proof of performance in real conditions.
    """
    if (
        not isinstance(face_image_bgr, np.ndarray)
        or face_image_bgr.size == 0
        or face_image_bgr.ndim != 3
        or face_image_bgr.shape[2] != 3
        or face_image_bgr.dtype != np.uint8
    ):
        raise ValueError("Expected a nonempty uint8 BGR aligned face image.")

    return {
        "Original": face_image_bgr.copy(),
        "Brighter": cv2.convertScaleAbs(face_image_bgr, alpha=1.0, beta=20),
        "Dimmer": cv2.convertScaleAbs(face_image_bgr, alpha=1.0, beta=-20),
        "Higher contrast": cv2.convertScaleAbs(face_image_bgr, alpha=1.15, beta=-15),
        "Flipped": cv2.flip(face_image_bgr, 1),
    }


def average_normalized_embeddings(embeddings: list[np.ndarray]) -> np.ndarray:
    """Create one unit-length gallery template from several sample vectors."""
    if not embeddings:
        raise ValueError("At least one face embedding is required.")

    vectors = [np.asarray(value, dtype=np.float32) for value in embeddings]
    if any(
        vector.shape != (128,) or not np.isfinite(vector).all()
        for vector in vectors
    ):
        raise ValueError("Every face embedding must contain 128 finite values.")

    average = np.mean(vectors, axis=0, dtype=np.float32)
    length = float(np.linalg.norm(average))
    if not np.isfinite(length) or length == 0:
        raise ValueError("The face embeddings could not form a valid template.")
    return (average / length).astype(np.float32)
