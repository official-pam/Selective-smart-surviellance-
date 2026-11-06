# Project audit: supplied ZIP

## What the ZIP contains

The ZIP has more implementation than the earlier repository scaffold:

- **Detection:** YOLO person detection, ByteTrack tracking, foot-point zone checks, entry/exit transitions and annotated frames.
- **Face recognition:** the supplied YuNet/SFace face-processing and gallery code.
- **Integration:** a controller that opens a camera or video source, passes frames through detection, matches a face on zone entry, and stores event information.
- **Dashboard:** a Streamlit interface with camera settings, live monitoring controls, region drawing, event history and CSV export.
- **Local alerts/storage:** SQLite event history, evidence images, retention and a cooldown. There is no Telegram dependency in this supplied ZIP.

The frontend README calls the controls and sample events “demo” features, but the supplied controller and interface code are connected. The code still needs to be run from the cleaned project layout before we claim that the end-to-end path works on our laptop.

## What was placed in the cleaned structure

Source code and the small tracker configuration were placed in the tracked project structure. The three model files from the ZIP were also extracted into the locally ignored `models/` folder so this workspace can run them; they are excluded from Git:

| ZIP contribution | Clean project location | Owner |
|---|---|---|
| Detection engine | `src/selective_surveillance/detection/engine.py` | Williams |
| Face-processing, gallery and matcher files | `src/selective_surveillance/facial_recognition/` | Emmanuel |
| Backend controller | `src/selective_surveillance/integration/controller.py` | Josiah |
| Local dashboard-alert policy/service | `src/selective_surveillance/alerting/` | Abubakar |
| SQLite event and evidence store | `src/selective_surveillance/storage/event_store.py` | Abubakar |
| Storage exception type | `src/selective_surveillance/storage/exceptions.py` | Abubakar |
| Streamlit interface | `src/selective_surveillance/dashboard/app.py` | Ugochukwu |
| ByteTrack configuration | `configs/bytetrack.yaml` | Williams |

The code now imports through the `selective_surveillance` Python package and reads its model, alert and storage settings from `configs/default.toml`. The ZIP also contains a test video, generated event images, an SQLite database, bytecode caches and macOS metadata. Those artifacts were not copied into the source folders or committed.

## What is present and what is missing

| Area | Present in the supplied code | Still needed |
|---|---|---|
| Live camera | OpenCV camera index or stream address; phone stream and camera settings in Streamlit | Confirm the actual DroidCam source on our laptop; handle frame timeouts, disconnect recovery and real measured frame rate |
| Boundaries | Dashboard canvas draws a polygon or rectangle; detection checks the person's bottom-centre point; changing camera source clears the current region | Saved geometry is held in the Streamlit session and can be downloaded, but is not automatically restored from a local file; validate coordinates, avoid stretching the frame, and verify zone accuracy after camera movement |
| Person detection | YOLO weights are supplied in the ZIP; ByteTrack-based IDs and entry/exit transitions are implemented | Record model provenance, training data, class labels and validation results; verify tracking and detection in our camera conditions |
| Face recognition | YuNet/SFace matching; gallery enrollment; Known/Unknown/Uncertain decisions | Gallery currently keeps one reference embedding per person; add a clear multi-capture enrollment workflow and evaluate suitable augmentation without treating generated copies as independent evidence |
| Rechecks/cache | A recognition-cache helper exists in the repository | The controller does not use it. Recognition happens at the entry transition, so an unclear face is not automatically checked again on later frames |
| Alerts | Unknown matches can create a local dashboard notification; SQLite cooldown and evidence retention exist | Define the reviewed policy for uncertain/unclear faces, keep Known entries informational, and avoid calling any unknown match an “intruder” or threat without human review |
| Anti-spoofing | Test ideas can be described in the scenario plan | No liveness/anti-spoof model is implemented. Printed photos, phone screens and replay video can be evaluation attacks, but current code cannot claim to detect them |
| Evaluation | A scenario plan and a threshold helper exist | No scenario `.ipynb` results, independent test set, confusion-matrix metrics, low-light/twin/cap/print/replay measurements, FPS, latency or hardware report are in the ZIP |
| Training/research record | Model files and source README claims are present | No detector training notebook, labelled dataset, training log, model card, experiment results or research bibliography was found in the ZIP |
| Shared interfaces/config | Typed contracts and TOML settings exist | The controller and detector still exchange dictionaries rather than `contracts.py`; `default.toml` drives model, tracker, face-decision, alert-cooldown and retention settings, but camera selection and saved drawing state remain in Streamlit session state |

## Important code-review findings

- The live Streamlit loop polls frames every 0.2 seconds and runs model processing in that same UI flow. That is a five-update-per-second target, not a measured FPS guarantee; heavy inference can slow the dashboard. Measure it before presenting the system as real-time.
- The dashboard resizes every frame to 960 by 540 before zone checking. The zone and detector currently share those resized coordinates, but this can distort a camera with a different aspect ratio and reduces detail for face matching. Preserve aspect ratio and transform the saved zone consistently.
- The supplied detector reloaded YOLO weights on reset. The cleaned version resets tracker state while keeping the model loaded; this performance improvement still needs measurement on the laptop.
- Recognition is called once on the zone-entry frame. Use subsequent frames to retry when a face is unclear, and cache only stable final decisions for active tracks.
- In the supplied database schema, a column called `confidence` received the SFace cosine similarity. The cleaned event store now uses `similarity` and migrates that old column name when it encounters an existing database.
- The supplied event-history UI labeled every zone-entry row as an “intrusion,” including Known entries. The cleaned UI uses neutral “Restricted Zone Entry” wording, reserves the red notice for an Unknown match, and gives Known and inconclusive results separate notices.
- One saved zone is tied to one camera view. If the camera moves, the operator must recalibrate and save the zone again.

## Clean working layout

```text
configs/
  default.toml
  bytetrack.yaml
docs/
  ARCHITECTURE.md
  PROJECT_AUDIT.md
  TEAM_ROLES.md
  INTERFACES.md
  TEST_PLAN.md
notebooks/                         Python-only scenario and data-science notebooks
src/selective_surveillance/
  detection/                       Williams: person/zone implementation
  facial_recognition/              Emmanuel: enrollment and matching
  storage/                         Abubakar: private event/evidence storage support
  alerting/                        Abubakar: local dashboard alert policy
  dashboard/                       Ugochukwu: Streamlit UI and live boundary editor
  integration/                     Josiah: end-to-end controller
  contracts.py                     Shared records
evaluation/                        Joseph: metrics and experiment results
tests/                             Automated code checks
models/                            Local-only model weights; excluded from Git
private_data/                      Local-only gallery, DB and evidence; excluded from Git
```

Each teammate should commit only their assigned module folder and their own notebook folder. Shared contracts, requirements and architecture changes need team review. Keep notebooks Python-only. Use them for experiments and explanations; launch the continuously updating Streamlit camera app as an application, not as a sequence of notebook cells.

## Suggested next steps

1. Review this folder structure and agree on the neutral event/alert wording.
2. Put the three required model files in local `models/` and keep them out of Git.
3. Connect the controller through the shared `contracts.py` records; the current controller still passes plain dictionaries between modules.
4. Improve camera frame handling, zone coordinate scaling and recognition retries/cache.
5. Add a Python notebook for the scenario protocol and results: normal light, dim light, caps/occlusion, twins enrolled separately, unknown people, printed photo, phone-screen image and replay video.
6. Report false acceptance/rejection, uncertain/unclear outcomes, presentation-attack acceptance, zone accuracy, entry-to-dashboard-alert delay, end-to-end FPS and hardware. Do not claim anti-spoof detection unless a liveness method is implemented and tested.
7. Run the full live-camera path on the team's laptop, fix findings, then prepare the research slides with cited sources and measured results.
