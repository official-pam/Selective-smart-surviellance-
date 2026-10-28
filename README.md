# Group Selective Surveillance System for Security

Refinement of [IRFAN18727/smart-security-cam](https://github.com/IRFAN18727/smart-security-cam).
The existing Streamlit dashboard and camera engine are the application.
See [INTEGRATION_NOTES.md](INTEGRATION_NOTES.md) for architecture, changes and limits.

## Run locally (Windows, Python 3.12)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements-local-engine.txt
.\.venv\Scripts\python.exe -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8502
```

On this laptop, `start-dashboard.ps1` can also use the already installed shared
runtime from the adjacent clone. It prefers this repository's own environment
when present. First use may download the pretrained model weights. Local
requirements are the tested Windows route; the original requirements/Docker
files retain upstream dependency assumptions.

Open http://127.0.0.1:8502. In **Face onboarding and matching check**, enroll clear
reference photos of one consenting person at a time. References are saved as
local embeddings; uploaded onboarding photos are not saved by this feature.
Use separate photos to check matching and inspect the scores/rejection reason.
The browser snapshot option may need the live camera stopped first.

Under **Live camera**, select the laptop webcam (`0`), a phone stream URL, or
**Upload a video**, then click **Start camera**. **Stop camera** releases the
source. Uploaded clips stay under ignored `.runtime/inputs/`; captures and event
logs remain local. Uploaded videos use clip time for alert timers. Processing
speed depends on the laptop. No Telegram bot or external inference API is needed.
Keep the server bound to loopback; this dashboard has no authentication and is
intended for local demonstrations.

The repository must have the required local packages to start the camera.
Models are downloaded automatically when first used. The old `models-ready`
marker from this laptop is not required for another machine.

## Matching and validation

The fixed pipeline is **Facenet128 + OpenCV face detection/alignment + base
normalization + L2 normalization + cosine similarity**. Standalone Facenet512
embeddings cannot be reused. The old gallery is preserved separately. Existing
`known_faces/` reference photos can be imported using the dashboard button.

Threshold **0.60**, separation margin **0.05**, minimum face size and blur gate
are provisional. A score is not an identity probability. New enrollment does
not train weights. No model-weight fine-tuning has been performed.

For real calibration, create an ignored `validation/calibration_pairs.csv`:

```csv
image_a,image_b,same_person
photos/person_a_session1.jpg,photos/person_a_session2.jpg,1
photos/person_a_session1.jpg,photos/person_b_session2.jpg,0
```

Include many consenting people, genuine and impostor pairs, and realistic phone
lighting, pose and blur. Keep enrollment, calibration and final test captures
separate. Avoid adjacent video frames across splits. The CSV labels must be
checked manually; the tool does not infer ground truth from names.

```powershell
.\.venv\Scripts\python.exe score_validation_pairs.py validation/calibration_pairs.csv --output validation/calibration_scores.csv
.\.venv\Scripts\python.exe calibrate_threshold.py validation/calibration_scores.csv --target-far 0.01
.\.venv\Scripts\python.exe score_validation_pairs.py validation/test_pairs.csv --output validation/test_scores.csv
.\.venv\Scripts\python.exe calibrate_threshold.py validation/test_scores.csv --evaluate embeddings/threshold.json
```

The policy is read by both onboarding checks and live matching. Calibration
reports empirical false-accept/reject rates, not guaranteed deployment rates.
The held-out test does not change the policy. Pair verification does not measure
live multi-person identification, tracking IDs, or the ambiguity margin. Evaluate
those separately on labelled videos, including people absent from the gallery.
If no threshold meets the target the tool fails without replacing the policy.

## Checks and GitHub

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Face data, embeddings, credentials, videos, logs and weights are ignored. Review
`git diff` and `git status` before committing. Origin points to the upstream
repository; choose your group's GitHub repository before pushing. No push has
been made. Do not copy wildlife assignment weights into this project.
