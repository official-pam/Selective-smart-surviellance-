"""Regression tests for decisions/integration, not measured recognition accuracy."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from src.face_gallery import FaceGallery, normalize, rank_match, load_policy, PIPELINE
from calibrate_threshold import calibrate


def vector(index=0):
    result = np.zeros(128)
    result[index] = 1
    return result


class MatchingTests(unittest.TestCase):
    def test_foreign_embedding_and_zero_rejected(self):
        for value in (np.ones(512), np.zeros(128), np.full(128, np.nan)):
            with self.assertRaises(ValueError):
                normalize(value)

    def test_threshold_boundary_ambiguity_and_person_aggregation(self):
        query = vector()
        accepted = rank_match(query, [("A", query)], 1.0, .05)
        self.assertTrue(accepted["is_known"])
        rejected = rank_match(query, [("A", vector(1))], .6, .05)
        self.assertFalse(rejected["is_known"])
        ambiguous = rank_match(query, [("A", query), ("B", query)], .6, .05)
        self.assertFalse(ambiguous["is_known"])
        one_person = rank_match(query, [("A", query), ("A", query)], .6, .05)
        self.assertTrue(one_person["is_known"])
        self.assertEqual(len(one_person["scores"]), 1)
        self.assertIsNone(rank_match(query, [], .6, .05)["similarity"])

    def test_gallery_persists_deduplicates_and_isolates_pipeline(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "gallery.sqlite3"
            gallery = FaceGallery(path)
            self.assertEqual(gallery.enroll("Person", [vector()], ["same-image"]), 1)
            self.assertEqual(gallery.enroll("Person", [vector()], ["same-image"]), 0)
            self.assertEqual(FaceGallery(path).people(), [("Person", 1)])
            self.assertEqual(len(gallery.records()), 1)
            with self.assertRaises(ValueError):
                gallery.enroll(" ", [vector()])

    def test_foreign_policy_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "policy.json"
            path.write_text(json.dumps({"pipeline": "Facenet512", "threshold": .7}))
            with self.assertRaises(ValueError):
                load_policy(path)

    def test_calibration_includes_just_above_negative_boundary(self):
        rows = [{"similarity": .8, "same_person": "1", "pipeline": PIPELINE},
                {"similarity": .2, "same_person": "0", "pipeline": PIPELINE}]
        report = calibrate(rows, 0)
        self.assertEqual(report["validation"]["false_accept_rate"], 0)
        self.assertEqual(report["validation"]["false_reject_rate"], 0)
        with self.assertRaises(ValueError):
            calibrate(rows[:1], 0)
        with self.assertRaises(ValueError):
            calibrate([{**row, "pipeline": "Facenet512"} for row in rows], 0)


class DetectorTests(unittest.TestCase):
    def test_video_timer_uses_clip_time_and_exit_grace(self):
        from src.timer_manager import TimerManager
        timer = TimerManager(threshold_seconds=30)
        timer.on_exit = MagicMock()
        self.assertEqual(timer.update([1], current_time=1000), [])
        self.assertEqual(timer.update([1], current_time=1030), [(1, 30)])
        self.assertEqual(timer.get_elapsed(current_time=1031), {1: 31})
        self.assertEqual(timer.update([1], current_time=1031), [])
        timer.update([], current_time=1033)
        timer.on_exit.assert_called_once()

    def test_every_frame_no_stale_boxes_and_resizing(self):
        from src import detector
        model = MagicMock()
        model.names = {0: "person"}
        boxes = MagicMock()
        boxes.id.int.return_value.cpu.return_value.tolist.return_value = [3]
        boxes.xyxy.cpu.return_value.numpy.return_value = np.array([[-10, 10, 300, 210]])
        boxes.conf.cpu.return_value.tolist.return_value = [.9]
        present = MagicMock(boxes=boxes)
        absent = MagicMock(boxes=None)
        model.track.side_effect = [[present], [absent], [absent]]
        with patch.object(detector, "YOLO", return_value=model), patch.object(detector, "ZONE_ENABLED", True):
            tracker = detector.PersonDetectorTracker()
            tracker.process_frame(np.zeros((240, 320, 3), dtype=np.uint8))
            self.assertEqual(tracker.all_people[0]["bbox"][0], 0)
            zone = tracker.zone.copy()
            self.assertEqual(tracker.process_frame(np.zeros((240, 320, 3), dtype=np.uint8)), [])
            tracker.process_frame(np.zeros((480, 640, 3), dtype=np.uint8))
            self.assertFalse(np.array_equal(zone, tracker.zone))
            self.assertEqual(model.track.call_count, 3)

    def test_summary_counts_only_current_tracks(self):
        from src import detector
        model = MagicMock(names={0: "person"})
        with patch.object(detector, "YOLO", return_value=model), patch.object(detector.cv2, "putText") as put:
            tracker = detector.PersonDetectorTracker()
            people = [{"track_id": 1, "bbox": [10, 40, 100, 200]}]
            tracker.draw_annotations(np.zeros((240, 320, 3), dtype=np.uint8), people, {}, {99: {"is_known": True}})
            summary = put.call_args.args[1]
            self.assertIn("Known: 0", summary)
            self.assertIn("Pending: 1", summary)


if __name__ == "__main__":
    unittest.main()
