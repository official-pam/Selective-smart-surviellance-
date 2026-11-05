"""Adapt Emmanuel's original SFace module to the team's shared result record."""

from datetime import datetime, timezone

import numpy as np

from selective_surveillance.contracts import RecognitionResult, RecognitionStatus
from selective_surveillance.facial_recognition.face_processing import FaceProcessor
from selective_surveillance.facial_recognition.gallery import FaceGallery
from selective_surveillance.facial_recognition.recognition import FaceRecognitionService


class RecognitionAdapter:
    """Return a shared result while preserving unclear faces and system errors."""

    def __init__(
        self,
        processor: FaceProcessor,
        gallery: FaceGallery,
        threshold: float,
        margin: float,
    ) -> None:
        self._service = FaceRecognitionService(processor, gallery, threshold, margin)

    def recognise(self, track_id: int, face_crop: np.ndarray | None) -> RecognitionResult:
        """Recognise one track crop. A missing/multi-face crop is not Unknown."""
        checked_at = datetime.now(timezone.utc).isoformat()
        if face_crop is None or face_crop.size == 0:
            return RecognitionResult(
                track_id=track_id,
                status=RecognitionStatus.FACE_UNCLEAR,
                checked_at=checked_at,
                reason="No usable face crop was supplied.",
            )

        try:
            result = self._service.recognize(face_crop)
        except ValueError as error:
            return RecognitionResult(
                track_id=track_id,
                status=RecognitionStatus.FACE_UNCLEAR,
                checked_at=checked_at,
                reason=str(error),
            )
        except Exception as error:
            return RecognitionResult(
                track_id=track_id,
                status=RecognitionStatus.ERROR,
                checked_at=checked_at,
                reason=f"Face-recognition module error: {type(error).__name__}",
            )

        status = RecognitionStatus(result["status"].lower())
        return RecognitionResult(
            track_id=track_id,
            status=status,
            checked_at=checked_at,
            name=result["name"] if status is RecognitionStatus.KNOWN else None,
            similarity=result["similarity"],
            reason=result["reason"],
        )
