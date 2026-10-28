"""
Smart Security Camera — main.py
Local tracking, face recognition and dashboard preview
"""

import os
import time
from pathlib import Path
import cv2
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from loguru import logger

os.environ.setdefault("DEEPFACE_HOME", str(__import__("pathlib").Path(__file__).resolve().parent / ".runtime"))
from src.local_runtime import STOP, FRAME, update_status, publish_frame
from src.logger_config import setup_logger
from src.detector import PersonDetectorTracker
from src.timer_manager import TimerManager
from src.capture import BestFaceCapture, save_visit_image, save_alert_images
from src.alert import send_visit_alert, send_30s_alert
from src.face_recognizer import FaceRecognizer
from src.database import init_database, log_event, log_detection
from config import CAMERA_INDEX, ALERT_THRESHOLD_SECONDS

setup_logger()
RECOGNITION_INTERVAL = 15


def handle_exit(track_id, entry_time, exit_time,
                duration, alerted, identity,
                best_frame, best_face, alert_frame_path):
    """
    Called when ANY person leaves frame.
    < 30s  → 1 Telegram image (clarity face + info)
    ≥ 30s  → 2 Telegram images (full frame + clarity face)
    """
    logger.info(f"handle_exit — ID:{track_id} | {duration}s | alerted:{alerted}")
    logger.info(f"best_face:{best_face is not None} | best_frame:{best_frame is not None}")

    # Save visit image for every person
    visit_path = save_visit_image(
        best_face  = best_face,
        best_frame = best_frame,
        track_id   = track_id,
        identity   = identity,
        entry_time = entry_time,
        exit_time  = exit_time,
        duration   = duration
    )
    logger.info(f"visit_path: {visit_path}")

    # Log detection
    log_detection(
        track_id   = track_id,
        name       = identity.get("name", "UNKNOWN"),
        is_known   = identity.get("is_known", False),
        confidence = identity.get("confidence", 0.0),
        duration   = duration,
        alerted    = alerted
    )

    if alerted:
        # ≥ 30s — send 2 images
        logger.info(f"Sending 30s alert — ID:{track_id}")
        send_30s_alert(
            frame_image_path = alert_frame_path,
            visit_image_path = visit_path,
            track_id         = track_id,
            elapsed          = duration,
            identity         = identity,
            entry_time       = entry_time,
            exit_time        = exit_time
        )
    else:
        # < 30s — send 1 image
        logger.info(f"Sending visit alert — ID:{track_id}")
        send_visit_alert(
            visit_image_path = visit_path,
            track_id         = track_id,
            elapsed          = duration,
            identity         = identity,
            entry_time       = entry_time,
            exit_time        = exit_time
        )


def main():
    update_status("loading", message="Loading local tracking and recognition models...")
    init_database()
    STOP.unlink(missing_ok=True)
    FRAME.unlink(missing_ok=True)

    source = os.environ.get("CAMERA_SOURCE", str(CAMERA_INDEX)).strip()
    source = int(source) if source.isdecimal() else source
    cap = cv2.VideoCapture(source, cv2.CAP_DSHOW) if isinstance(source, int) else cv2.VideoCapture(source)
    if not cap.isOpened():
        logger.critical("Cannot open webcam.")
        update_status("error", message="Cannot open camera. Stop the other camera app or choose another camera source.")
        cap.release()
        return

    is_video = isinstance(source, str) and Path(source).is_file()
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if not 0 < video_fps < 1000:
        video_fps = 30.0
    video_epoch = time.time()

    detector   = PersonDetectorTracker()
    timer_mgr  = TimerManager(threshold_seconds=ALERT_THRESHOLD_SECONDS)
    face_cap   = BestFaceCapture()
    recognizer = FaceRecognizer(
        known_faces_dir="known_faces",
        model_name="Facenet"
    )

    identities:        dict[int, dict]    = {}
    best_frames:       dict[int, object]  = {}   # tid → best frame
    best_faces:        dict[int, object]  = {}   # tid → best face crop
    alert_frame_paths: dict[int, str]     = {}   # tid → saved frame at 30s
    frame_count:       int = 0
    preview_time = 0.0
    started = time.monotonic()
    update_status("running", frames=0)
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="face-match")
    pending = {}
    last_recognition = {}
    visit_threads = []
    camera_failed = False

    # ── Exit callback ────────────────────────────────────
    def on_person_exit(track_id, entry_time, exit_time,
                       duration, alerted):
        # Grab copies before they get cleaned
        identity         = identities.pop(track_id, {
            "name": "UNKNOWN", "confidence": 0.0, "is_known": False
        })
        last_recognition.pop(track_id, None)
        best_frame       = best_frames.pop(track_id, None)
        best_face        = best_faces.pop(track_id, None)
        alert_frame_path = alert_frame_paths.pop(track_id, None)

        visit_thread = threading.Thread(
            target = handle_exit,
            args   = (
                track_id, entry_time, exit_time,
                duration, alerted, identity,
                best_frame, best_face, alert_frame_path
            ),
            daemon = True
        )
        visit_threads[:] = [thread for thread in visit_threads if thread.is_alive()]
        visit_threads.append(visit_thread)
        visit_thread.start()

    timer_mgr.on_exit = on_person_exit

    logger.info("System started. Use Stop camera in the dashboard to quit.")

    while not STOP.exists():
        ret, frame = cap.read()
        if not ret:
            camera_failed = not is_video
            if camera_failed:
                update_status("error", message="Camera stopped delivering frames.")
            break

        frame_count += 1

        # Detect + track
        tracked_objects = detector.process_frame(frame)
        active_ids      = [obj["track_id"] for obj in tracked_objects]

        # Update face capture
        face_cap.update(frame, active_ids, tracked_objects)

        # ✅ Update best frames/faces every frame
        for tid in active_ids:
            bf = face_cap.get_best_frame(tid)
            bc = face_cap.get_best_face_crop(tid)
            if bf is not None:
                best_frames[tid] = bf.copy()
            if bc is not None:
                best_faces[tid] = bc.copy()

        # Collect results on the main thread only. Discard results for vanished tracks.
        visible = set(active_ids)
        for tid, future in list(pending.items()):
            if future.done():
                if tid in visible:
                    identities[tid] = future.result()
                pending.pop(tid)
        # Keep at most one task in flight, so slow inference cannot build a queue.
        if frame_count % RECOGNITION_INTERVAL == 0 and not pending:
            for tid in sorted(active_ids, key=lambda t: last_recognition.get(t, 0)):
                face_crop = best_faces.get(tid)
                if face_crop is not None:
                    pending[tid] = executor.submit(recognizer.identify, face_crop.copy())
                    last_recognition[tid] = time.monotonic()
                    break

        # Update timers
        frame_time = video_epoch + (frame_count - 1) / video_fps if is_video else None
        triggered = timer_mgr.update(active_ids, current_time=frame_time)
        elapsed_map = timer_mgr.get_elapsed(current_time=frame_time)

        # ✅ Handle 30s trigger — save frame immediately
        for (tid, actual_elapsed) in triggered:
            identity = identities.get(tid, {
                "name": "UNKNOWN", "confidence": 0.0, "is_known": False
            })

            # Save full frame at 30s mark
            saved = save_alert_images(
                best_face  = best_faces.get(tid),
                best_frame = best_frames.get(tid),
                track_id   = tid
            )
            alert_frame_paths[tid] = saved.get("enhanced_frame")

            logger.info(
                f"🚨 30s — ID:{tid} | "
                f"{identity.get('name','UNKNOWN')} | "
                f"frame saved: {alert_frame_paths[tid]}"
            )

            # Log to DB
            log_event(
                track_id   = tid,
                name       = identity.get("name", "UNKNOWN"),
                is_known   = identity.get("is_known", False),
                confidence = identity.get("confidence", 0.0),
                duration   = actual_elapsed,
                image_path = saved.get("best_face"),
                alert_sent = False
            )

        # Draw
        annotated = detector.draw_annotations(
            frame, tracked_objects, elapsed_map, identities
        )
        if time.monotonic() - preview_time >= 0.2:
            publish_frame(annotated)
            match_rows = [
                {"Track": tid, "Result": identities[tid]["name"],
                 "Similarity": identities[tid].get("similarity"),
                 "Threshold": identities[tid].get("threshold"),
                 "Reason": identities[tid].get("reason", "")}
                for tid in active_ids if tid in identities
            ]
            update_status(
                "running", frames=frame_count, tracks=len(tracked_objects),
                fps=round(frame_count / max(0.01, time.monotonic()-started), 1),
                identities=match_rows,
            )
            preview_time = time.monotonic()

    cap.release()
    end_time = video_epoch + max(0, frame_count - 1) / video_fps if is_video else time.time()
    timer_mgr.update([], current_time=end_time + timer_mgr.GRACE_PERIOD + 0.1)
    for thread in visit_threads:
        thread.join(timeout=10)
    executor.shutdown(wait=False, cancel_futures=True)
    if not camera_failed:
        update_status("stopped", frames=frame_count, message="Video finished." if is_video and not STOP.exists() else "Camera stopped.")
    STOP.unlink(missing_ok=True)
    FRAME.unlink(missing_ok=True)
    logger.info("System shut down.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        update_status("error", message=f"{type(exc).__name__}: {exc}")
        logger.exception("Camera engine stopped")
        raise
    