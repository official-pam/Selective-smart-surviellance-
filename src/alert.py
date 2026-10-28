import smtplib
import requests
import winsound
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path
from datetime import datetime
from loguru import logger
from config import (
    ALERT_METHOD, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
)


def play_alert_sound():
    """3 beeps for 30s alert."""
    try:
        for _ in range(3):
            winsound.Beep(1000, 500)
    except Exception as e:
        logger.warning(f"Sound failed: {e}")


def _format_duration(elapsed: float) -> str:
    mins = int(elapsed) // 60
    secs = elapsed % 60
    return f"{mins}m {secs:.1f}s" if mins > 0 else f"{secs:.1f} seconds"


def _build_info_message(track_id, elapsed, identity,
                        entry_time, exit_time, is_30s_alert):
    """Build the info text for Telegram caption."""
    dur_text   = _format_duration(elapsed)
    entry_text = entry_time if entry_time else "Unknown"

    if identity and identity["is_known"]:
        status_line  = "✅ KNOWN PERSON"
        name_line    = f"👤 {identity['name']}"
        conf_line    = f"Confidence : {identity['confidence']}%"
    else:
        status_line  = "🚨 UNKNOWN PERSON"
        name_line    = "👤 Unknown"
        conf_line    = "No match in database"

    if is_30s_alert:
        header = "🔴 30s SECURITY ALERT"
    else:
        header = "📋 VISIT LOG"

    return (
        f"{header}\n"
        f"{'─' * 26}\n"
        f"{status_line}\n"
        f"{name_line}\n"
        f"{'─' * 26}\n"
        f"🕐 In time    : {entry_text}\n"
        f"🚪 Out time   : {exit_time}\n"
        f"⏱ Duration   : {dur_text}\n"
        f"🆔 Track ID   : {track_id}\n"
        f"{conf_line}"
    )


def _send_photo(image_path: str, caption: str):
    """Send single photo to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path, "rb") as img:
            response = requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                files={"photo": img},
                timeout=15
            )
        if response.status_code == 200:
            logger.success(f"Telegram photo sent.")
        else:
            logger.error(f"Telegram error: {response.text}")
    except Exception as e:
        logger.error(f"Telegram failed: {e}")


def send_visit_alert(visit_image_path: str,
                     track_id: int,
                     elapsed: float,
                     identity: dict,
                     entry_time: str,
                     exit_time: str):
    """
    Called when person leaves BEFORE 30 seconds.
    Sends 1 image only — clarity face with info overlay.
    No sound.
    """
    if not visit_image_path:
        return

    message = _build_info_message(
        track_id     = track_id,
        elapsed      = elapsed,
        identity     = identity,
        entry_time   = entry_time,
        exit_time    = exit_time,
        is_30s_alert = False
    )

    if ALERT_METHOD == "telegram":
        _send_photo(visit_image_path, message)
    elif ALERT_METHOD == "email":
        _send_email_single(visit_image_path, message)

    logger.info(f"Visit alert sent — ID:{track_id} | {elapsed:.1f}s")


def send_30s_alert(frame_image_path: str,
                   visit_image_path: str,
                   track_id: int,
                   elapsed: float,
                   identity: dict,
                   entry_time: str,
                   exit_time: str):
    """
    Called when person stays ≥ 30 seconds.
    Sends 2 images:
      Image 1 → Full frame at 30s mark (FIRST — immediate alert)
      Image 2 → Best clarity face + info overlay
    Plays sound.
    """
    # Play sound immediately
    play_alert_sound()

    message_1 = (
        f"🔴 30s ALERT — PERSON IN FRAME\n"
        f"{'─' * 26}\n"
        f"🕐 In time  : {entry_time}\n"
        f"⏱ So far   : {_format_duration(elapsed)}\n"
        f"🆔 Track ID : {track_id}"
    )

    message_2 = _build_info_message(
        track_id     = track_id,
        elapsed      = elapsed,
        identity     = identity,
        entry_time   = entry_time,
        exit_time    = exit_time,
        is_30s_alert = True
    )

    if ALERT_METHOD == "telegram":
        # Image 1 first — full frame at 30s
        if frame_image_path:
            _send_photo(frame_image_path, message_1)

        # Image 2 — clarity face with full details
        if visit_image_path:
            _send_photo(visit_image_path, message_2)

    elif ALERT_METHOD == "email":
        paths = [p for p in [frame_image_path, visit_image_path] if p]
        _send_email_multi(paths, message_2)

    logger.success(f"30s alert sent — ID:{track_id} | {elapsed:.1f}s")


def _send_email_single(image_path: str, body: str):
    msg            = MIMEMultipart()
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVER
    msg["Subject"] = "📋 Security Visit Log"
    msg.attach(MIMEText(body, "plain"))
    if image_path:
        with open(image_path, "rb") as f:
            img = MIMEImage(f.read(), name=Path(image_path).name)
            msg.attach(img)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        logger.success("Email sent.")
    except Exception as e:
        logger.error(f"Email failed: {e}")


def _send_email_multi(image_paths: list, body: str):
    msg            = MIMEMultipart()
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVER
    msg["Subject"] = "🔴 30s Security Alert"
    msg.attach(MIMEText(body, "plain"))
    for path in image_paths:
        with open(path, "rb") as f:
            img = MIMEImage(f.read(), name=Path(path).name)
            msg.attach(img)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        logger.success("Email sent.")
    except Exception as e:
        logger.error(f"Email failed: {e}")