"""Shared Python records passed between the team-owned modules."""

from dataclasses import dataclass
from enum import StrEnum


class ZoneState(StrEnum):
    INSIDE = "inside"
    OUTSIDE = "outside"


class RecognitionStatus(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    UNCERTAIN = "uncertain"
    FACE_UNCLEAR = "face_unclear"
    ERROR = "error"


class EventType(StrEnum):
    KNOWN_ENTRY = "known_entry"
    UNKNOWN_ENTRY = "unknown_entry"
    UNCERTAIN_ENTRY = "uncertain_entry"
    FACE_UNCLEAR_ENTRY = "face_unclear_entry"
    ZONE_EXIT = "zone_exit"


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Pixel coordinates in the original frame, ordered left, top, right, bottom."""

    x1: int
    y1: int
    x2: int
    y2: int

    def __post_init__(self) -> None:
        if self.x1 < 0 or self.y1 < 0 or self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("Bounding box coordinates must form a positive area.")


@dataclass(frozen=True, slots=True)
class TrackedPerson:
    """One person observation produced by detection and tracking."""

    track_id: int
    box: BoundingBox
    confidence: float
    zone_id: str
    zone_state: ZoneState
    observed_at: str
    face_crop: object | None = None

    def __post_init__(self) -> None:
        if self.track_id < 0:
            raise ValueError("Track IDs must be non-negative.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Detection confidence must be between 0 and 1.")
        if not self.zone_id:
            raise ValueError("Every tracked person must have a zone ID.")


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    """One identity decision. Similarity is cosine similarity, not probability."""

    track_id: int
    status: RecognitionStatus
    checked_at: str
    name: str | None = None
    similarity: float | None = None
    reason: str = ""
    cached: bool = False

    def __post_init__(self) -> None:
        if self.status is RecognitionStatus.KNOWN and not self.name:
            raise ValueError("A Known decision must include an accepted name.")
        if self.status is not RecognitionStatus.KNOWN and self.name is not None:
            raise ValueError("Only a Known decision may include an accepted name.")
        if self.similarity is not None and not -1.0 <= self.similarity <= 1.0:
            raise ValueError("Cosine similarity must be between -1 and 1.")


@dataclass(frozen=True, slots=True)
class SecurityEvent:
    """Event record stored before a local dashboard alert is displayed."""

    event_id: str
    occurred_at: str
    track_id: int
    zone_id: str
    event_type: EventType
    recognition_status: RecognitionStatus
    similarity: float | None = None
    person_name: str | None = None
    face_image_path: str | None = None
    frame_image_path: str | None = None
    alert_status: str = "not_applicable"

    def __post_init__(self) -> None:
        if self.event_type is EventType.KNOWN_ENTRY and self.recognition_status is not RecognitionStatus.KNOWN:
            raise ValueError("Known entry events require a Known recognition result.")
        if self.event_type is EventType.UNKNOWN_ENTRY and self.recognition_status is not RecognitionStatus.UNKNOWN:
            raise ValueError("Unknown entry events require an Unknown recognition result.")
        if self.event_type is EventType.UNCERTAIN_ENTRY and self.recognition_status is not RecognitionStatus.UNCERTAIN:
            raise ValueError("Uncertain entry events require an Uncertain recognition result.")
        if self.event_type is EventType.FACE_UNCLEAR_ENTRY and self.recognition_status is not RecognitionStatus.FACE_UNCLEAR:
            raise ValueError("Face-unclear entry events require a Face unclear result.")
