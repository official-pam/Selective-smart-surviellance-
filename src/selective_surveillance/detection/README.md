# Detection, tracking and restricted zone

**Owner: Williams Emehel.** `engine.py` implements person detection with Ultralytics YOLO and persistent ByteTrack IDs, polygon membership, entry/exit transitions, and per-track person crops. It reads pixel coordinates from the dashboard/controller. The selected zone and processed frame must use the same image dimensions. The team's detector weights belong at `models/best.pt` and are excluded from Git.

The starter settings are in `configs/default.toml`. The zone polygon is only an example and must be redrawn for the demonstration camera. Measure person precision/recall, zone accuracy, ID switches and FPS. Do not make identity or alert decisions in this module.
