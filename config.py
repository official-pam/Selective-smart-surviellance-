"""Application settings. PERSON_CLASS_ID must match the trained dataset."""
CONFIDENCE_THRESHOLD = 0.25
PERSON_CLASS_ID = 0
# Process every frame to keep ByteTrack state current.
DETECTION_FRAME_SKIP = 1
ZONE_ENABLED = True
ZONE_NORM = ((0.15, 0.15), (0.85, 0.15), (0.85, 0.95), (0.15, 0.95))
ALERT_THRESHOLD_SECONDS = 10.0
