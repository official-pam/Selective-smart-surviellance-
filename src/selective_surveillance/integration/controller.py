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


class SurveillanceController:

    def __init__(self, project_root, zone_points=None):

        self.project_root = Path(project_root)
        self.zone_points = zone_points or []
        settings_path = self.project_root / "configs" / "default.toml"
        with settings_path.open("rb") as settings_file:
            self.settings = tomllib.load(settings_file)

        self.camera = None
        self.camera_fps = 30.0
        self.camera_connected = False
        self.monitoring = False

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

        self.gallery_path = (
            self.project_root
            / "private_data"
            / "face_gallery.json"
        )

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
        database_path = self.project_root / storage_settings["database_path"]
        evidence_directory = self.project_root / storage_settings["evidence_directory"]

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

        for detection_event in detection_events:

            event = dict(detection_event)

            if event["event"] != "zone_entry":
                processed_events.append(event)
                continue

            track_id = event["track_id"]

            person_crop = self.detector.latest_person_crops.get(track_id)

            identity = {
                "status": "Uncertain",
                "name": None,
                "candidate": None,
                "similarity": None,
                "reason": "Face recognition was not completed."
            }

            face_image_bytes = None
            face_status = "not_captured"

            # -------------------------------------
            # FACE CAPTURE AND RECOGNITION
            # -------------------------------------

            if person_crop is not None:

                try:

                    _, aligned_face = self.face_processor.extract(person_crop)

                    face_image_bytes = self.encode_image(aligned_face)

                    face_status = "captured"

                    if self.gallery.references():

                        identity = self.recognition.recognize(person_crop)

                    else:

                        identity["reason"] = (
                            "No registered identities in the gallery."
                        )

                except ValueError as error:

                    face_status = "face_not_detected"
                    identity["reason"] = str(error)

                except Exception as error:

                    face_status = "processing_error"
                    identity["reason"] = str(error)

            # -------------------------------------
            # RECOGNITION STATUS
            # -------------------------------------

            if identity["status"] == "Known":
                known = True

            elif identity["status"] == "Unknown":
                known = False

            else:
                known = None

            # -------------------------------------
            # STORE EVENT
            # -------------------------------------

            full_frame_bytes = self.encode_image(frame)

            storage_result = self.alerting.record_event(
                known=known,
                similarity=identity.get("similarity"),
                zone=event["zone_id"],
                track_id=track_id,
                occurred_at=event["recorded_at"],
                face_status=face_status,
                face_image=face_image_bytes,
                full_frame=full_frame_bytes
            )

            event["identity"] = identity
            event["storage"] = storage_result

            processed_events.append(event)

        return annotated_frame, processed_events

    # -----------------------------------------
    # RESET
    # -----------------------------------------

    def reset(self):

        self.detector.reset()

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
