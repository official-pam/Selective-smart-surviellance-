import os
from dotenv import load_dotenv
load_dotenv()

# Detection
CONFIDENCE_THRESHOLD = 0.5
PERSON_CLASS_ID = 0
DETECTION_FRAME_SKIP = 1  # Tracking runs on every processed frame; do not reuse stale boxes.

# Optional restricted zone: bottom-centre of each person box determines membership.
ZONE_ENABLED = False
ZONE_NORM = [(0.15, 0.20), (0.85, 0.20), (0.85, 0.95), (0.15, 0.95)]

# Fixed original Facenet pipeline. These are provisional gates, not measured accuracy.
FACE_SIMILARITY_THRESHOLD = 0.60
FACE_AMBIGUITY_MARGIN = 0.05
FACE_MIN_SIZE = 80
FACE_MIN_SHARPNESS = 60.0

# Timer
ALERT_THRESHOLD_SECONDS = 30

# Capture
CAPTURES_DIR = "captures"
os.makedirs(CAPTURES_DIR, exist_ok=True)

# Logging
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# Alert
ALERT_METHOD = os.getenv("ALERT_METHOD", "local")

# Email (leave empty, we use telegram)
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Camera
CAMERA_INDEX = 0
