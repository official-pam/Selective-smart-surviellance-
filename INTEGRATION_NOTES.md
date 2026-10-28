# Integration review

The existing clone is `IRFAN18727/smart-security-cam`; the entry points remain
`dashboard.py` and `main.py`. No second application was added.

## What was retained

YOLOv8n person detection, ByteTrack, DeepFace **Facenet** (128 values), OpenCV,
the original capture module, timers, SQLite event logs and Streamlit dashboard.
Alerts remain local when launched from the dashboard. The original upstream
Telegram/email implementation is present but does not need configuration.

## Reference changes integrated

- Repaired detector with current-frame tracking, clipped boxes, resized optional
  restricted zone, and counts from visible tracks only. `ZONE_ENABLED=False`
  retains whole-frame operation. When enabled, only people whose bottom-centre
  point lies in the polygon enter the existing timers/capture pipeline.
- Enrollment, quality rejection, normalized cosine ranking and ambiguity checks
  inside the existing dashboard and live recognizer.
- Match name, score, threshold, per-person scores and rejection reason in the
  image check; current-track scores/reasons beside the live preview.
- Video upload through the same tracking/recognition/alert loop. Recorded clips
  use frame timestamps rather than processing duration for alert timers.
- One recognition worker with bounded outstanding work and rotation between
  visible tracks. Results for departed tracks are discarded.
- Pair scoring and threshold calibration CLI using the application's exact
  embedding pipeline, plus frozen-threshold held-out evaluation.

## What was deliberately not imported

The standalone Streamlit app, its Facenet512 pipeline, its 512-value enrollment
database, provisional 0.70 threshold and optional training script. The standalone
folder and `embeddings/gallery.sqlite3` were left untouched. Reference images
must be enrolled again into this app's separate Facenet128 gallery. The original
`known_faces/` photos can be imported through an explicit dashboard button.

## Training and evidence

No weights were trained or fine-tuned. YOLO and Facenet are pretrained models.
Code repairs, onboarding, quality gates, and threshold calibration do not update
weights. Adding a person stores reference embeddings; it requires no retraining.

The initial cosine-similarity threshold is 0.60, equivalent to the installed
DeepFace Facenet cosine-distance default of 0.40. It is provisional for this
capture pipeline. The ambiguity margin 0.05 and quality gates are also provisional.
Pair calibration does not validate the ambiguity margin or live open-set accuracy.

No labelled validation images, videos or score CSVs were found in the supplied
reference folder. It contains enrollment embeddings, not a held-out evaluation
set. Do not report measured recognition accuracy or a calibrated threshold yet.
Regression tests and blank-video inference check software behaviour only.

Historical SQLite events retain their existing `confidence` column. New events
store cosine similarity multiplied by 100 for schema compatibility; the UI now
labels it as similarity, not probability. Older values were computed differently.

## GitHub preparation

Changes are on `codex/integrate-onboarding-calibration` in the original clone.
The origin still points at the upstream author's repository. Nothing is pushed.
Face galleries, validation data, credentials, captures, videos and weight files
are excluded by `.gitignore`. Review the diff before committing. Retain upstream
attribution and check upstream licensing before redistributing its code.

## Verification completed

- Eight regression tests passed: tracking freshness/zone resizing/clipping,
  visible identity counts, clip-time alerts/exit grace, vector compatibility,
  threshold and ambiguity decisions, gallery persistence/deduplication,
  incompatible calibration rejection, and calibration boundary behaviour.
- Streamlit AppTest rendered the existing dashboard, onboarding and matching
  controls, switched to video upload, and blocked start without a selected clip.
- The actual YOLO/ByteTrack loop processed eight generated blank video frames and
  reached normal EOF. This exercises file input and shutdown, not detection or
  recognition accuracy on people.
- Python source compilation, Git whitespace checks and a sensitive-file/token
  pattern check passed. Private gallery/data/weights paths are ignored.
