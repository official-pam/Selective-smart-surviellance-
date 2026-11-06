# Selective Smart Surveillance System

This is a Python-only, real-time restricted-zone monitoring project. A phone running DroidCam can send its live feed to the laptop; the Streamlit dashboard connects to that camera, shows the live frames, lets the operator draw the restricted area, and presents event notices. The Python pipeline detects and tracks people, checks a face when a person enters the zone, and records the result locally.

The supplied ZIP already includes connected camera, detection, recognition, local database and Streamlit code. Those pieces have now been placed in the project package folders and their imports have been aligned. The project has **not yet been run or evaluated from this cleaned structure**. See [the project audit](docs/PROJECT_AUDIT.md) for what is present and the work still needed.

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

Use Python 3.12. From the project root, install the project dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Put the model files in the ignored local `models/` folder:

- `best.pt` — the person detector weights supplied in the ZIP;
- `face_detection_yunet_2023mar.onnx` — YuNet face detector;
- `face_recognition_sface_2021dec.onnx` — SFace embedding model.

Do not commit model weights or participant data. Then start the dashboard on the laptop:

```powershell
python -m streamlit run src/selective_surveillance/dashboard/app.py --server.address 127.0.0.1
```

Connect DroidCam using the phone and PC client. In the dashboard, choose the matching webcam index or supported phone stream address, connect the camera, draw and save the restricted zone over its frame, then start monitoring. The region is held for the current Streamlit session and can be downloaded; automatic restoration after restarting the app is still to be implemented. The exact source value depends on the DroidCam setup on that computer. For an offline scenario replay, the dashboard can also use a local video file.

## Project map

```text
configs/                         Shared safe defaults and ByteTrack settings
docs/                            Architecture, roles, audit, interfaces and evaluation plan
notebooks/                       Python-only, cell-by-cell experiments by owner/scenario
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

Enroll only consenting participants. The gallery, captures, event database and evidence images stay in the ignored `private_data/` directory. Use localhost during the student demonstration. The current face-recognition pipeline has no liveness or anti-spoof model; photo and screen attacks must be treated as evaluation scenarios, not as attacks the current code can detect.
