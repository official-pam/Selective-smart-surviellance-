from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from evaluation.face_threshold import choose_similarity_threshold
from selective_surveillance.alerting.policy import should_raise_dashboard_alert
from selective_surveillance.facial_recognition.recognition import FaceRecognitionService
from selective_surveillance.facial_recognition.augmentation import (
    average_normalized_embeddings,
    create_face_augmentations,
)
from selective_surveillance.facial_recognition.gallery import FaceGallery
from selective_surveillance.integration.controller import SurveillanceController
from selective_surveillance.dashboard.zone_config import (
    clear_zone,
    load_zone,
    save_zone,
)
from selective_surveillance.storage.event_store import EventStore


def test_dashboard_alert_policy_only_alerts_on_a_clear_unknown():
    assert should_raise_dashboard_alert(False) is True
    assert should_raise_dashboard_alert(True) is False
    assert should_raise_dashboard_alert(None) is False


def test_scenario_threshold_respects_false_accept_limit():
    result = choose_similarity_threshold(
        known_scores=[0.72, 0.81, 0.88],
        unknown_scores=[0.10, 0.35, 0.62],
        max_false_accept_rate=0.0,
    )

    assert result["threshold"] == 0.72
    assert result["false_accept_rate"] == 0.0
    assert result["false_reject_rate"] == 0.0
    assert result["known_validation_count"] == 3
    assert result["unknown_validation_count"] == 3


def test_scenario_threshold_rejects_missing_validation_groups():
    with pytest.raises(ValueError, match="known-person"):
        choose_similarity_threshold([], [0.1])
    with pytest.raises(ValueError, match="unenrolled-person"):
        choose_similarity_threshold([0.8], [])


class FixedProcessor:
    def __init__(self, embedding):
        self.embedding = np.asarray(embedding, dtype=np.float32)

    def extract(self, image):
        return self.embedding, image


class FixedGallery:
    def __init__(self, references):
        self._references = references

    def references(self):
        return self._references


def test_recognition_service_returns_known_unknown_and_uncertain():
    query = np.array([1.0, 0.0], dtype=np.float32)

    known_service = FaceRecognitionService(
        FixedProcessor(query),
        FixedGallery({"Alex One": query, "Sam Two": np.array([0.0, 1.0])}),
        threshold=0.5,
        margin=0.05,
    )
    assert known_service.recognize(object())["status"] == "Known"
    assert known_service.recognize(object())["name"] == "Alex One"

    unknown_service = FaceRecognitionService(
        FixedProcessor(np.array([-1.0, 0.0])),
        FixedGallery({"Alex One": query, "Sam Two": np.array([0.0, 1.0])}),
        threshold=0.5,
        margin=0.05,
    )
    assert unknown_service.recognize(object())["status"] == "Unknown"

    almost_same = np.array([0.99, np.sqrt(1 - 0.99**2)], dtype=np.float32)
    uncertain_service = FaceRecognitionService(
        FixedProcessor(query),
        FixedGallery({"Alex One": query, "Sam Two": almost_same}),
        threshold=0.5,
        margin=0.05,
    )
    assert uncertain_service.recognize(object())["status"] == "Uncertain"


def test_face_augmentation_creates_five_views_and_a_unit_template():
    aligned_face = np.full((112, 112, 3), 80, dtype=np.uint8)

    variations = create_face_augmentations(aligned_face)
    assert list(variations) == [
        "Original", "Brighter", "Dimmer", "Higher contrast", "Flipped"
    ]
    assert np.array_equal(variations["Original"], aligned_face)
    assert variations["Brighter"].mean() > aligned_face.mean()
    assert variations["Dimmer"].mean() < aligned_face.mean()

    template = average_normalized_embeddings([
        np.array([1.0, 0.0] + [0.0] * 126),
        np.array([0.8, 0.6] + [0.0] * 126),
    ])
    assert template.shape == (128,)
    assert np.isclose(np.linalg.norm(template), 1.0)


def test_multiple_capture_enrollment_saves_one_template_and_returns_previews(tmp_path):
    class EnrollmentProcessor:
        def extract(self, image):
            return np.array([1.0] + [0.0] * 127, dtype=np.float32), image

        def embedding_from_aligned_face(self, image):
            return np.array([1.0] + [0.0] * 127, dtype=np.float32)

    controller = object.__new__(SurveillanceController)
    controller.face_processor = EnrollmentProcessor()
    controller.gallery = FaceGallery()
    controller.gallery_path = tmp_path / "private_data" / "face_gallery.json"
    aligned_photo = np.full((112, 112, 3), 90, dtype=np.uint8)

    result = controller.enroll_person_from_images(
        "Ada",
        "Lovelace",
        [aligned_photo.copy(), aligned_photo.copy(), aligned_photo.copy()],
    )

    assert result["name"] == "Ada Lovelace"
    assert result["capture_count"] == 3
    assert result["augmentation_count"] == 12
    assert len(result["preview_images"]) == 15
    restored_gallery = FaceGallery.load(controller.gallery_path)
    assert list(restored_gallery.references()) == ["Ada Lovelace"]


def test_camera_zone_config_is_private_and_saved_for_multiple_sources(tmp_path):
    config_path = tmp_path / "zone.local.json"
    camera_a = "rtsp://camera-a.local/live?password=private"
    camera_b = "0"
    region_a = {"shape": "polygon", "drawing": {"objects": []}}
    region_b = {"shape": "rectangle", "drawing": {"objects": []}}

    save_zone(camera_a, region_a, config_path)
    save_zone(camera_b, region_b, config_path)

    saved_text = config_path.read_text(encoding="utf-8")
    assert "password=private" not in saved_text
    assert load_zone(camera_a, config_path) == region_a
    assert load_zone(camera_b, config_path) == region_b

    clear_zone(camera_a, config_path)
    assert load_zone(camera_a, config_path) is None
    assert load_zone(camera_b, config_path) == region_b

    clear_zone(camera_b, config_path)
    assert not config_path.exists()


def test_event_store_applies_dashboard_alert_and_cooldown(tmp_path):
    store = EventStore(
        database_path=str(tmp_path / "private" / "events.sqlite3"),
        image_dir=str(tmp_path / "private" / "evidence"),
        cooldown_seconds=60,
    )
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)

    first = store.record_event(
        known=False, similarity=0.21, zone="entry", track_id=5,
        occurred_at=start.isoformat(),
    )
    repeated = store.record_event(
        known=False, similarity=0.22, zone="entry", track_id=5,
        occurred_at=(start + timedelta(seconds=20)).isoformat(),
    )
    later = store.record_event(
        known=False, similarity=0.23, zone="entry", track_id=5,
        occurred_at=(start + timedelta(seconds=61)).isoformat(),
    )
    known = store.record_event(
        known=True, similarity=0.91, zone="entry", track_id=7,
        occurred_at=(start + timedelta(seconds=62)).isoformat(),
    )
    unclear = store.record_event(
        known=None, similarity=None, zone="entry", track_id=8,
        face_status="unclear",
        occurred_at=(start + timedelta(seconds=63)).isoformat(),
    )

    assert first["alert_status"] == "dashboard_alert"
    assert repeated["alert_status"] == "cooldown"
    assert later["alert_status"] == "dashboard_alert"
    assert known["alert_status"] == "not_applicable"
    assert unclear["alert_status"] == "not_applicable"
    assert len(store.list_events()) == 5
    assert store.latest_dashboard_alert()["recognition"] == "unknown"
