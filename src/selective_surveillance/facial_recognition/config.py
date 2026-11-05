"""Shared settings for the facial-recognition module."""

# Identify the preprocessing and embedding pipeline.
PIPELINE_ID = "yunet-sface-2021dec-resize640-align112-l2-v1"

# Model files are downloaded separately, not committed to GitHub.
DETECTOR_MODEL = "face_detection_yunet_2023mar.onnx"
RECOGNITION_MODEL = "face_recognition_sface_2021dec.onnx"

# Resize proportionally before face detection.
MAX_IMAGE_SIDE = 640

# Filter face detections; this is NOT an identity-matching threshold.
DETECTION_THRESHOLD = 0.90
NMS_THRESHOLD = 0.30

# Provisional identity-decision settings, requiring validation.
SIMILARITY_THRESHOLD = 0.40
AMBIGUITY_MARGIN = 0.05
