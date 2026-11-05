# Module interfaces

`src/selective_surveillance/contracts.py` is the source of truth for the shared Python data records. Keep its field names stable once integration starts.

## Detection to face recognition

```python
TrackedPerson(
    track_id=12,                 # persistent integer from ByteTrack
    box=BoundingBox(x1, y1, x2, y2),
    confidence=0.91,             # YOLO person-detection confidence
    zone_id="server-room",
    zone_state=ZoneState.INSIDE,
    observed_at="UTC ISO timestamp",
    face_crop=...,               # BGR crop, or None when not usable
)
```

Williams's module supplies one record per tracked person per processed frame. Recognition receives the face crop and tracking ID; the integration layer supplies the frame/crop using the agreed coordinate system.

## Recognition to selection and alerts

```python
RecognitionResult(
    track_id=12,
    status=RecognitionStatus.UNKNOWN,
    name=None,                    # set only when status is KNOWN
    similarity=0.23,             # cosine similarity; not a probability
    reason="No reference passed the threshold.",
    checked_at="UTC ISO timestamp",
    cached=False,
)
```

Allowed status values: `KNOWN`, `UNKNOWN`, `UNCERTAIN`, `FACE_UNCLEAR`, `ERROR`. `ERROR` is operational failure, not an identity judgement. A recognition status alone does not trigger an alert: the selection policy also requires an entry into the configured zone.

## Selection to event storage

```python
SecurityEvent(
    event_id="unique ID",
    occurred_at="UTC ISO timestamp",
    track_id=12,
    zone_id="server-room",
    event_type="unknown_entry",  # or known_entry, face_unclear_entry, exit
    recognition_status="UNKNOWN",
    person_name=None,
    similarity=0.23,
    face_image_path="private evidence path or None",
    frame_image_path="private evidence path or None",
    alert_status="pending / sent / failed / not_required",
)
```

Abubakar stores every selected event before delivery. Telegram alert delivery updates its status without discarding the event. The dashboard receives read-only event rows and safe image references.

## Image and coordinate rules

- Frames and face crops use OpenCV BGR `uint8` arrays while inside Python modules.
- Bounding boxes are pixel coordinates in the original frame, in `(x1, y1, x2, y2)` order, with the top-left origin.
- Zone polygons use normalised `(x, y)` points between 0 and 1. The detector converts to pixels for each frame size.
- All persisted event times use UTC ISO-8601 timestamps.
- A missing face crop is `None`; it is not an empty fake image.
