"""Local-only camera status and preview shared with the Streamlit dashboard."""
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / '.runtime'
RUNTIME.mkdir(exist_ok=True)
STATE = RUNTIME / 'camera.json'
FRAME = RUNTIME / 'preview.jpg'
STOP = RUNTIME / 'stop-camera'


def update_status(status, **fields):
    payload = {'status': status, 'pid': os.getpid(), 'updated': time.time(), **fields}
    temporary = STATE.with_suffix('.tmp')
    try:
        temporary.write_text(json.dumps(payload), encoding='utf-8')
        os.replace(temporary, STATE)
    except OSError:
        pass


def read_status():
    try:
        return json.loads(STATE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'status': 'stopped'}


def publish_frame(frame):
    import cv2
    success, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if success:
        temporary = FRAME.with_suffix('.tmp')
        try:
            temporary.write_bytes(encoded.tobytes())
            os.replace(temporary, FRAME)
        except OSError:
            pass
