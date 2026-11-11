"""Central controller for the Smart Surveillance System."""

from pathlib import Path
import tomllib

import cv2

from selective_surveillance.alerting.service import AlertingService
from selective_surveillance.detection.engine import PersonZoneDetector
from selective_surveillance.facial_recognition.face_processing import FaceProcessor
from selective_surveillance.facial_recognition.augmentation import (
    average_normalized_embeddings,
    create_face_augmentations,
)
from selective_surveillance.facial_recognition.gallery import FaceGallery
from selective_surveillance.facial_recognition.recognition import FaceRecognitionService
from selective_surveillance.storage.paths import get_private_data_directory


class SurveillanceController:

    def __init__(self, project_root, zone_points=None):

        self.project_root = Path(project_root)
        self.private_data_directory = get_private_data_directory(self.project_root)
        self.zone_points = zone_points or []
        settings_path = self.project_root / "configs" / "default.toml"
        with settings_path.open("rb") as settings_file:
            self.settings = tomllib.load(settings_file)

        self.camera = None
        self.camera_fps = 30.0
        self.camera_connected = False
        self.monitoring = False
        self.face_checks = {}
        self.face_check_interval = 3
        self.max_face_attempts = 12

        # -----------------------------------------
        # DETECTION
        # -----------------------------------------

        detector_settings = self.settings["person_detection"]
        face_settings = self.settings["face_recognition"]

        self.detector = PersonZoneDetector(
            model_path=self.project_root / detector_settings["model"],
            tracker_path=self.project_root / detector_settings["tracker"],
            confidence=float(detector_settings["confidence_threshold"]),
            zone_id=self.settings["restricted_zone"]["id"],
        )

        # -----------------------------------------
        # FACIAL RECOGNITION
        # -----------------------------------------

        self.face_processor = FaceProcessor(
            models_dir=self.project_root / "models",
            detector_model=Path(face_settings["detector_model"]).name,
            recognition_model=Path(face_settings["recognition_model"]).name,
            detection_threshold=float(face_settings["detection_threshold"]),
        )

        self.gallery_path = self.private_data_directory / "face_gallery.json"

        if self.gallery_path.exists():
            self.gallery = FaceGallery.load(self.gallery_path)
        else:
            self.gallery = FaceGallery()

        self.recognition = FaceRecognitionService(
            processor=self.face_processor,
            gallery=self.gallery,
            threshold=float(face_settings["similarity_threshold"]),
            margin=float(face_settings["ambiguity_margin"]),
        )

        # -----------------------------------------
        # ALERTING AND DATABASE
        # -----------------------------------------

        storage_settings = self.settings["storage"]
        # Keep private records outside the checkout. This also avoids permission
        # errors when a cloned project folder is read-only or protected by Windows.
        database_path = (
            self.private_data_directory
            / Path(storage_settings["database_path"]).name
        )
        evidence_directory = (
            self.private_data_directory
            / Path(storage_settings["evidence_directory"]).name
        )

        self.alerting = AlertingService(
            database_path=str(database_path),
            image_dir=str(evidence_directory),
            cooldown_seconds=self.settings["alerting"]["cooldown_seconds"],
            retention_days=storage_settings["retention_days"],
        )

        print("Surveillance backend initialized successfully.")

    # -----------------------------------------
    # CAMERA CONNECTION
    # -----------------------------------------

    def connect_camera(self, source):

        self.disconnect_camera()

        if source is None or str(source).strip() == "":
            raise ValueError("Enter a camera stream address or camera index.")

        source = str(source).strip()

        # Allow local camera index, e.g. 0
        camera_source = int(source) if source.isdigit() else source

        self.camera = cv2.VideoCapture(camera_source)

        if not self.camera.isOpened():
            self.camera.release()
            self.camera = None
            raise RuntimeError("Unable to connect to the selected camera.")

        success, frame = self.camera.read()

        if not success or frame is None:
            self.camera.release()
            self.camera = None
            raise RuntimeError("Camera connected but no video frame was received.")

        fps = self.camera.get(cv2.CAP_PROP_FPS)

        if fps and fps > 0:
            self.camera_fps = fps

        self.camera_connected = True

        return frame

    def disconnect_camera(self):

        self.monitoring = False

        if self.camera is not None:
            self.camera.release()
            self.camera = None

        self.camera_connected = False

    # -----------------------------------------
    # READ CAMERA FRAME
    # -----------------------------------------

    def read_camera_frame(self):

        if self.camera is None or not self.camera.isOpened():
            return None

        success, frame = self.camera.read()

        if not success:
            return None

        return frame

    # -----------------------------------------
    # RESTRICTED ZONE
    # -----------------------------------------

    def set_zone(self, zone_points):

        if not zone_points or len(zone_points) < 3:
            raise ValueError("The restricted zone requires at least three points.")

        self.zone_points = [
            (int(x), int(y))
            for x, y in zone_points
        ]

        self.detector.reset()

    # -----------------------------------------
    # START MONITORING
    # -----------------------------------------

    def start_monitoring(self):

        if not self.camera_connected:
            raise RuntimeError("Connect a camera before starting monitoring.")

        if len(self.zone_points) < 3:
            raise RuntimeError("Save a restricted region before monitoring.")

        self.detector.reset()
        self.face_checks.clear()
        self.monitoring = True

    # -----------------------------------------
    # STOP MONITORING
    # -----------------------------------------

    def stop_monitoring(self):

        self.monitoring = False

    # -----------------------------------------
    # IMAGE ENCODING
    # -----------------------------------------

    @staticmethod
    def encode_image(image):

        if image is None:
            return None

        success, buffer = cv2.imencode(".jpg", image)

        if not success:
            return None

        return buffer.tobytes()

    # -----------------------------------------
    # ENROLL A PERSON
    # -----------------------------------------

    def enroll_person(self, first_name, surname, face_image):
        """Enroll one consenting person's image, with mild safe augmentations."""
        result = self.enroll_person_from_images(
            first_name,
            surname,
            [face_image],
        )
        return result["name"]

    def enroll_person_from_images(self, first_name, surname, face_images):
        """Build one template from multiple real captures and mild variations."""
        if not face_images:
            raise ValueError("Upload at least one face image.")

        embeddings = []
        preview_images = []

        # Validate every capture before updating the saved gallery.
        for image_number, face_image in enumerate(face_images, start=1):
            embedding, aligned_face = self.face_processor.extract(face_image)
            embeddings.append(embedding)

            variants = create_face_augmentations(aligned_face)
            preview_images.extend(
                (f"Capture {image_number}: {label}", image)
                for label, image in variants.items()
            )

            # The original is already encoded by extract(); encode its
            # brightness, contrast and flip variations with the same model.
            for label, augmented_image in variants.items():
                if label == "Original":
                    continue
                embeddings.append(
                    self.face_processor.embedding_from_aligned_face(
                        augmented_image
                    )
                )

        template = average_normalized_embeddings(embeddings)
        full_name = self.gallery.enroll(first_name, surname, template)
        self.gallery.save(self.gallery_path)

        return {
            "name": full_name,
            "capture_count": len(face_images),
            "augmentation_count": len(preview_images) - len(face_images),
            "preview_images": preview_images,
        }

    # -----------------------------------------
    # PROCESS FRAME
    # -----------------------------------------

    def process_frame(self, frame):

        if not self.monitoring:
            return frame, []

        if len(self.zone_points) < 3:
            raise RuntimeError("No valid restricted zone is configured.")

        annotated_frame, detection_events = self.detector.process_frame(
            frame,
            self.zone_points,
            self.camera_fps
        )

        processed_events = []
        events_by_track = {event["track_id"]: event for event in detection_events}

        # Create one event record as soon as someone enters. Face matching can
        # then retry on later frames without making duplicate zone events.
        for track_id, event in events_by_track.items():
            if event["event"] == "zone_exit":
                state = self.face_checks.pop(track_id, None)
                exit_event = dict(event)
                if state and not state["finalized"]:
                    identity = state["identity"]
                    known = True if identity.get("status") == "Known" else (
                        False if identity.get("status") == "Unknown" else None
                    )
                    state["storage"] = self.alerting.update_event_identity(
                        event_id=state["event_id"],
                        known=known,
                        similarity=identity.get("similarity"),
                        face_status=state["face_status"],
                        face_image=state["face_image"],
                    )
                    exit_event["identity"] = identity
                processed_events.append(exit_event)
                continue

            identity = {
                "status": "Checking",
                "name": None,
                "candidate": None,
                "similarity": None,
                "reason": "Looking for a clear face while the person is inside the zone.",
            }
            storage = self.alerting.record_event(
                known=None,
                similarity=None,
                zone=event["zone_id"],
                track_id=track_id,
                occurred_at=event["recorded_at"],
                face_status="pending",
                full_frame=self.encode_image(frame),
            )
            self.face_checks[track_id] = {
                "event_id": storage["event_id"],
                "zone_id": event["zone_id"],
                "occurred_at": event["recorded_at"],
                "attempts": 0,
                "last_attempt_frame": -self.face_check_interval,
                "identity": identity,
                "face_status": "pending",
                "face_image": None,
                "finalized": False,
                "storage": storage,
            }
            entry = dict(event)
            entry.update(identity=identity, storage=storage, face_attempts=0)
            processed_events.append(entry)

        # Run face detection only for tracked people currently inside the
        # restricted region. Retry over successive frames because a single
        # entry frame often has a turned, small, or shadowed face.
        for track_id, track in self.detector.latest_tracks.items():
            state = self.face_checks.get(track_id)
            if not track["inside_zone"] or state is None or state["finalized"]:
                continue

            frame_number = self.detector.frame_number
            if frame_number - state["last_attempt_frame"] < self.face_check_interval:
                continue

            state["last_attempt_frame"] = frame_number
            state["attempts"] += 1
            person_crop = self.detector.latest_person_crops.get(track_id)
            identity = {
                "status": "Uncertain", "name": None, "candidate": None,
                "similarity": None, "reason": "No face crop was available.",
            }
            face_status = "face_not_detected"
            face_image_bytes = None

            if person_crop is not None:
                try:
                    embedding, aligned_face = self.face_processor.extract(person_crop)
                    face_image_bytes = self.encode_image(aligned_face)
                    face_status = "captured"
                    if self.gallery.references():
                        identity = self.recognition.recognize_embedding(embedding)
                    else:
                        identity["reason"] = "No registered identities in the gallery."
                except ValueError as error:
                    identity["reason"] = str(error)
                except Exception as error:
                    face_status = "processing_error"
                    identity["reason"] = str(error)

            # Keep the clearest/highest-scoring observation for this track.
            previous = state["identity"]
            score = identity.get("similarity")
            previous_score = previous.get("similarity")
            if score is not None and (previous_score is None or score > previous_score):
                state["identity"] = identity
                state["face_image"] = face_image_bytes
                state["face_status"] = face_status
            elif identity["status"] == "Known":
                state["identity"] = identity
                state["face_image"] = face_image_bytes
                state["face_status"] = face_status
            elif previous.get("status") == "Checking":
                state["identity"] = identity
                state["face_image"] = face_image_bytes
                state["face_status"] = face_status

            identity = state["identity"]
            # A clear known or clear no-match is decisive immediately. Retry
            # unclear/no-face frames, then finish as inconclusive at the limit.
            final = identity.get("status") in {"Known", "Unknown"} or (
                state["attempts"] >= self.max_face_attempts
            )
            if final:
                known = True if identity["status"] == "Known" else (
                    False if identity["status"] == "Unknown" else None
                )
                state["storage"] = self.alerting.update_event_identity(
                    event_id=state["event_id"],
                    known=known,
                    similarity=identity.get("similarity"),
                    face_status=state["face_status"],
                    face_image=state["face_image"],
                )
                state["finalized"] = True

            update = {
                "event": "face_update",
                "track_id": track_id,
                "zone_id": state["zone_id"],
                "identity": identity,
                "storage": state["storage"],
                "face_attempts": state["attempts"],
                "face_final": state["finalized"],
                "recorded_at": state["occurred_at"],
            }
            processed_events.append(update)

        # Add a clear face-check label to the tracked person, so zone presence
        # and identity checking are visibly separate steps.
        for track_id, track in self.detector.latest_tracks.items():
            x1, y1, _, _ = track["box"]
            state = self.face_checks.get(track_id)
            if track["inside_zone"] and state:
                label = state["identity"]["status"].upper()
                if not state["finalized"] and label != "KNOWN":
                    label = f"CHECKING FACE {state['attempts']}/{self.max_face_attempts}"
                color = (0, 220, 255) if not state["finalized"] else (80, 220, 80)
                cv2.putText(
                    annotated_frame, f"FACE: {label}", (x1, max(y1 - 32, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
                )

        return annotated_frame, processed_events

    # -----------------------------------------
    # RESET
    # -----------------------------------------

    def reset(self):

        self.detector.reset()
        self.face_checks.clear()

    # -----------------------------------------
    # RETRIEVE EVENTS
    # -----------------------------------------

    def get_events(self, limit=100):

        return self.alerting.list_events(limit)

    # -----------------------------------------
    # LATEST ALERT
    # -----------------------------------------

    def get_latest_alert(self):

        return self.alerting.latest_dashboard_alert()
