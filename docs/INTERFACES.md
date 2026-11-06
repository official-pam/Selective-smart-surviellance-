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

Allowed status values: `KNOWN`, `UNKNOWN`, `UNCERTAIN`, `FACE_UNCLEAR`, `ERROR`. `ERROR` is operational failure, not an identity judgement, and should appear as a system problem rather than an intruder decision. A recognition status alone does not trigger an alert: the selection policy also requires a new entry into the configured zone.

## Selection to event storage

```python
SecurityEvent(
    event_id="unique ID",
    occurred_at="UTC ISO timestamp",
    track_id=12,
    zone_id="server-room",
    event_type="unknown_entry",  # or known_entry, uncertain_entry, face_unclear_entry, exit
    recognition_status="UNKNOWN",
    person_name=None,
    similarity=0.23,
    face_image_path="private evidence path or None",
    frame_image_path="private evidence path or None",
    alert_status="dashboard_alert / cooldown / not_applicable",
)
```

Abubakar stores every selected event before it is shown as an alert in the Streamlit dashboard. Dashboard alert state is local to the application; there is no Telegram or external message delivery. The dashboard receives event rows and safe local image references.

## Image and coordinate rules

- Frames and face crops use OpenCV BGR `uint8` arrays while inside Python modules.
- Bounding boxes are pixel coordinates in the original frame, in `(x1, y1, x2, y2)` order, with the top-left origin.
- The current dashboard saves drawing data for a 960 × 540 canvas; the live loop resizes each processed frame to that same size before using pixel coordinates. Preserve this match when modifying frame handling. The target improvement is to preserve camera aspect ratio and store normalized `(x, y)` polygon points, then convert them to frame pixels once per frame size. Do not commit a real facility's zone coordinates.
- All persisted event times use UTC ISO-8601 timestamps.
- A missing face crop is `None`; it is not an empty fake image.
