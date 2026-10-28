"""Live recognition uses the same original Facenet gallery as dashboard onboarding."""
from loguru import logger
from src.face_gallery import FaceGallery, extract_embedding, load_policy


class FaceRecognizer:
    def __init__(self, known_faces_dir="known_faces", model_name="Facenet"):
        if model_name != "Facenet":
            raise ValueError("This gallery supports the original Facenet model only.")
        self.gallery = FaceGallery()
        self.known_faces_dir = known_faces_dir

    def identify(self, face_crop):
        policy = load_policy()
        unknown = {"name": "UNKNOWN", "is_known": False, "confidence": 0.0,
                   "similarity": None, "threshold": policy["threshold"], "scores": []}
        if not self.gallery.people():
            return {**unknown, "reason": "No reference faces are enrolled."}
        try:
            return self.gallery.match(extract_embedding(face_crop))
        except ValueError as exc:
            return {**unknown, "reason": str(exc)}
        except Exception:
            logger.exception("Face recognition failed")
            return {**unknown, "reason": "Recognition failed; inspect the local engine log."}
