# Detection, tracking and restricted zone

**Owner: Williams Emehel.** Implement pretrained YOLO person detection, ByteTrack persistent IDs, polygon zone membership, entry/exit state, dwell time and a suitable upper-person crop. Return shared `TrackedPerson` records from `contracts.py` in original-frame pixel coordinates.

The starter settings are in `configs/default.toml`. The zone polygon is only an example and must be redrawn for the demonstration camera. Measure person precision/recall, zone accuracy, ID switches and FPS. Do not make identity or alert decisions in this module.
