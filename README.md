# Person detection and tracking — Emmanuel John

Refined source based on the supplied YOLOv8/ByteTrack module. This package does
not contain trained weights or a face recognition model. Code cleanup and
parameter changes do not constitute model fine-tuning.

## Setup and detector fine-tuning

Use Python 3.10 or later in a virtual environment:

```sh
pip install -r requirements.txt
python train_detector.py --data /path/to/data.yaml --device 0
```

Use `--device cpu` when no CUDA GPU is available. Supply a YOLO bounding-box
dataset with person annotations and separate training/validation splits.
Do not use the earlier four-class wildlife weights for person detection.
After training, use the printed `best.pt` path:

```python
from detector import PersonDetectorTracker

detector = PersonDetectorTracker(model_name="runs/detect/person_finetune/weights/best.pt")
# For each consecutive BGR video frame:
people = detector.process_frame(frame)
annotated = detector.draw_annotations(frame, people, timer_info={}, identities={})
```

`frame` comes from your existing camera/video loop. This snippet plugs into that
loop; it is not a standalone video runner. Update PERSON_CLASS_ID in config.py
if the person class has a different index. The constructor verifies its name.
For a new or restarted video, create a new detector instance. Do not share one
instance between streams.

## Changes from the pasted module

- Restored Python formatting and the `__init__` constructor.
- Tracks every frame instead of reusing stale boxes on skipped frames. Existing
  DETECTION_FRAME_SKIP imports remain compatible, but this module ignores it.
- Rebuilds the normalized zone polygon when frame size changes; uses foot-point
  membership and clips bounding boxes to the frame.
- Clears current people when no IDs are available; pending/unconfirmed boxes
  without track IDs are not sent into the identity/timer pipeline.
- Counts identities only for current in-zone tracks and separates pending IDs.
- Removes misleading percentage labels for uncalibrated identity scores.

Timers, actual alerts, face crops, recognition, and identity cache expiry remain
the responsibility of your existing pipeline. Expire identity entries when a
track ends, and clear them on stream resets. A track ID is not a face identity.

## Face recognition work still needed

The supplied text contains no face detector, embedding extractor, gallery,
matching threshold, or training dataset. Provide that module and identify its
library before changing it. Improving recognition thresholds requires labelled
same-person/different-person validation pairs; training model weights requires
labelled face images and a supported training pipeline. Neither has been done
in this package. Use held-out people/captures to measure false accepts and false
rejects; do not describe raw similarity as a probability.

## GitHub

Copy these source files into your project and review the integration. Keep face
images, embeddings, credentials, and videos out of the repository. The included
.gitignore excludes them and large model weights. Publish weights separately if
appropriate. Check the Ultralytics license terms for your intended distribution.

Validation: source compilation only; no training, GPU inference, face accuracy,
or camera integration has been tested in this environment. After installing,
record your working dependency versions with `pip freeze > requirements.lock.txt`.

## Face enrollment UI and threshold calibration

This standalone reference UI uses DeepFace Facenet512 with OpenCV detection,
alignment and cosine similarity. It has not been integrated with your existing
UI because that source and your recognizer were not supplied.

```sh
pip install -r requirements-face.txt
streamlit run app.py --server.address 127.0.0.1
```

Use Enroll faces to enter a name and upload photos or take a webcam photo.
Exactly one detected face and a minimum 80-pixel face size are required.
Samples are stored as embeddings in local SQLite, not raw photos. Repeated
names add samples to the same identity; use distinct names for distinct people.
The recognition tab uses a separate photo to test matches. Manage people allows
deletion. This is a local prototype, without authentication, liveness protection,
or a continuous video recognition loop. Do not expose the enrollment UI publicly.

The default 0.70 threshold and 0.05 ambiguity margin are provisional, not claimed
accuracy improvements. To select a threshold, prepare a private CSV with columns
`similarity,same_person`, one row per labelled face pair. Labels are 1 for the
same person and 0 otherwise. Compute similarity using dot products of normalized
embeddings from extract_embedding, using separate captures rather than the same
photo twice. Include realistic lighting/pose and difficult negative pairs.

```sh
python calibrate_threshold.py private_validation_pairs.csv --target-far 0.01
```

This writes embeddings/threshold.json, which the UI reads on the next rerun.
The selected operating point meets the requested FAR only on the provided
validation sample; it does not guarantee production FAR. A small number of
negative pairs cannot establish a low false-accept rate reliably. Evaluate on
separate held-out images/people, including unknown queries against the entire
gallery. Pair verification scores are not a substitute for open-set identification
evaluation. Revalidate whenever the gallery, model, preprocessing, or margin changes.

To connect to the detector, use gallery.match(extract_embedding(person_crop),
threshold) and place the returned dictionary in identities[track_id]. Reject
multi-face crops and clear identities when tracks end or streams restart. This
integration remains to be implemented in your camera loop.

API references: https://docs.ultralytics.com/modes/track/ and
https://github.com/serengil/deepface . No trained weights are supplied.
