# Selective Smart Surveillance System

This is a Python-only, real-time restricted-zone monitoring project. A phone running DroidCam can send its live feed to the laptop; the Streamlit dashboard connects to that camera, shows the live frames, lets the operator draw the restricted area, and presents event notices. The Python pipeline detects and tracks people, retries face checks over successive frames while a person is inside the zone, and records one local event per entry. The live preview can be hidden while monitoring continues.

The supplied ZIP already includes connected camera, detection, recognition, local database and Streamlit code. Those pieces have now been placed in the project package folders and their imports have been aligned. The cleaned project now installs and initializes on Python 3.13, and its automated checks pass. Real camera scenarios have not yet been measured. See [the project audit](docs/PROJECT_AUDIT.md) for what is present and what still needs field testing.

## Team folders

| Teammate | Work area | What belongs there |
|---|---|---|
| Williams Emehel | `src/selective_surveillance/detection/` | YOLO person detection, ByteTrack tracking and zone transitions |
| Emmanuel John | `src/selective_surveillance/facial_recognition/` | Face enrollment, embeddings, matching and recognition decisions |
| Abubakar Ahmed | `src/selective_surveillance/storage/` and `src/selective_surveillance/alerting/` | SQLite events, local evidence, cooldowns and dashboard alert policy |
| Ugochukwu Okoroji | `src/selective_surveillance/dashboard/` | Streamlit camera view, boundary editor, event history and notices |
| Josiah Frank Achile | `src/selective_surveillance/integration/` | Connect camera, vision, recognition, storage and dashboard inputs |
| Joseph Ekuma | `evaluation/`, `tests/` and scenario notebooks | Scenario design, metrics, repeatable evaluation and results |

Each owner commits within their assigned folder. Shared changes to `contracts.py`, configuration, dependencies or interfaces should be coordinated with Josiah and reviewed by the team. Step-by-step experiments go in `notebooks/` and use Python kernels only. The local live app remains ordinary Python code launched by Streamlit.

## Current processing flow

```text
DroidCam phone feed -> laptop camera input -> Streamlit live view / zone drawing
          -> YOLO person detection + ByteTrack IDs
          -> restricted-zone entry check
          -> YuNet face detection + SFace matching
          -> local SQLite event / evidence -> visible dashboard notice
```

The local dashboard does not send Telegram or other external notifications. An unrecognized face means the gallery did not match it; it is not proof that the person is dangerous. An uncertain or unclear face is shown for review, not asserted as an intruder. DroidCam's documented PC connection options are Wi-Fi and USB; the setup must not assume Bluetooth.

## Run locally

Use Python 3.13 (Python 3.11 or 3.12 also meets the declared version range). On Windows, create the environment in the shorter `Documents\Codex` folder so PyTorch does not hit Windows' long-path limit. Run these commands in PowerShell from the project root:

```powershell
$env:PROJECT_ENV = "$env:USERPROFILE\Documents\Codex\.venvs\surveillance"
python -m venv $env:PROJECT_ENV
& "$env:PROJECT_ENV\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install -e .
```

For the scenario notebook and automated checks, install the optional development tools with `python -m pip install -e ".[dev]"` instead.

Put the model files in the ignored local `models/` folder:

- `best.pt` — copy the person detector weights from the supplied project ZIP;
- `face_detection_yunet_2023mar.onnx` and `face_recognition_sface_2021dec.onnx` — download and checksum-verify both OpenCV Zoo face models by running `python scripts/download_face_models.py`.

The detector weights are not downloaded or committed because their training data and redistribution details were missing from the ZIP. See [the model provenance record](docs/MODEL_PROVENANCE.md). Do not commit model weights or participant data. Then start the dashboard on the laptop:

```powershell
python -m streamlit run src/selective_surveillance/dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Connect DroidCam using the phone and PC client. In the dashboard, choose the matching webcam index or supported phone stream address, connect the camera, draw and save the restricted zone over its frame, then start monitoring. The dashboard stores the boundary locally for that camera source and restores it when the same source is selected; the camera address itself is not written into the boundary file. Camera frames are fitted inside the drawing area without stretching. For an offline replay, open **Live Monitoring** and either upload a video or enter its local file path. A Google Drive or YouTube link must first be saved as a video file on this computer.

The **Face Enrollment** page accepts at least three separate images of the same consenting person. It previews four mild variations per image and saves one averaged face template to ignored local storage. These generated variations are not independent test samples and are not an anti-spoofing feature. A new gallery profile is kept only on this computer. Shadow detail is enhanced for face detection and dashboard viewing, but the camera still needs enough visible or infrared light to capture identity details; low-light performance must be measured on the actual camera.

## Project map

```text
configs/                         Shared safe defaults and ByteTrack settings
docs/                            Architecture, roles, audit, model provenance and evaluation plan
notebooks/                       Python-only, cell-by-cell experiments by owner/scenario
scripts/                         Python model-download and setup helpers
src/selective_surveillance/
  detection/                     Williams's person and zone module
  facial_recognition/            Emmanuel's YuNet/SFace module
  alerting/                       Abubakar's local dashboard alert policy
  storage/                        Abubakar's event and evidence storage support
  dashboard/                      Ugochukwu's Streamlit application
  integration/                    Josiah's end-to-end controller
  contracts.py                    Shared typed records
evaluation/                       Joseph's scenario metrics and results
tests/                            Automated code checks
```

## Privacy

Enroll only consenting participants. The gallery, event database, evidence images and zone settings are stored locally in `%LOCALAPPDATA%\SelectiveSmartSurveillance` on Windows (or the operating system's local application-data folder). Set `SELECTIVE_SURVEILLANCE_DATA_DIR` to choose another local folder. If that folder is not writable in a managed environment, the app uses the ignored project-local `runtime_data/` folder. Use localhost during the student demonstration. The current face-recognition pipeline has no liveness or anti-spoof model; photo and screen attacks must be treated as evaluation scenarios, not as attacks the current code can detect.
