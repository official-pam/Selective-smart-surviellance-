# Group 4: Selective Smart Surveillance System

This is an end-to-end, Python-only, advanced data science project for consent-based restricted-area monitoring. A phone running DroidCam supplies a live camera feed to the laptop. A local Streamlit dashboard shows the feed and lets an operator draw the restricted zone on the camera image. The system detects and tracks people, checks faces against voluntarily enrolled people, records zone-entry events, and displays an on-screen alert when an unknown or unassessable person enters.

The repository was reorganised around the team assignment. Each person owns a module, and the shared Python records in `src/selective_surveillance/contracts.py` define how those modules exchange information.

## Team ownership

| Owner | Module | Main files |
|---|---|---|
| Williams Emehel | Person detection, tracking and restricted-zone entry/exit | `src/selective_surveillance/detection/` |
| Emmanuel John | Staff enrolment and face recognition | `src/selective_surveillance/facial_recognition/` |
| Abubakar Ahmed | Local event database, evidence storage and dashboard alert records | `src/selective_surveillance/storage/`, `src/selective_surveillance/alerting/` |
| Ugochukwu Okoroji | Streamlit dashboard, live camera controls and zone drawing | `src/selective_surveillance/dashboard/` |
| Josiah Frank Achile | Integration lead and shared interfaces | `src/selective_surveillance/integration/`, `docs/INTERFACES.md` |
| Joseph Ekuma | End-to-end test lead, results and demonstration | `evaluation/`, `docs/TEST_PLAN.md` |

## Project layout

```text
configs/default.toml                      Shared settings; polygon points are examples
notebooks/                                Python-only, cell-by-cell data science work
docs/TEAM_ROLES.md                         Responsibilities and handoffs
docs/ARCHITECTURE.md                       Processing flow and module boundaries
docs/INTERFACES.md                         Shared inputs, outputs and decisions
docs/TEST_PLAN.md                          Scenario-based acceptance and reporting
docs/PRIVACY_AND_SECURITY.md               Consent, access, retention and secrets
src/selective_surveillance/contracts.py    Shared typed Python records
src/selective_surveillance/detection/      Person detection, tracking and zone status
src/selective_surveillance/facial_recognition/  YuNet/SFace module from Emmanuel's ZIP
src/selective_surveillance/integration/    Connect modules; cache by tracking ID
src/selective_surveillance/alerting/       Local dashboard alert policy for security events
src/selective_surveillance/storage/        Event database and retained image paths
src/selective_surveillance/dashboard/      Streamlit live view, zone setup, visible alerts
evaluation/                                Scenario result analysis and reports
tests/                                     Module and end-to-end checks
```

Each teammate's source code and README live in that teammate's own module folder. The assignment table above is also the intended GitHub upload and commit path. Python notebooks for experiments go in `notebooks/`; all notebook kernels must be Python.

## Build order

1. Agree on the records in `contracts.py` before changing module interfaces.
2. Connect the DroidCam phone feed to the laptop as a camera source and show it in Streamlit.
3. Let the operator draw, save, edit and reset the restricted polygon from the live camera view.
4. Complete person detection, persistent tracking and zone-entry/exit output.
5. Complete face enrolment and calibrated Known/Unknown/Uncertain/Face unclear decisions.
6. Use `evaluation/face_threshold.py` on independent validation scores; connect `integration/recognition_cache.py` to each persistent tracking ID.
7. Save entry events locally and display an alert immediately in Streamlit for unknown, uncertain or face-unclear entrants.
8. Run the scenario plan, record measured results, and prepare a live demo with a recorded backup.

## Current state

This repository currently provides the team structure, data contracts, face-recognition adapter, short-lived track cache, validation-threshold helper, example settings and safety/testing plan. It is **not yet a running end-to-end camera application**. Camera capture, dashboard zone drawing, person detection/tracking, zone transitions, event storage and visible alerts still need implementation and integration. The example zone must be drawn for the actual camera view.

Team members can add files without using a terminal. The repository owner must first give them Write access. Follow [`CONTRIBUTING.md`](CONTRIBUTING.md) to invite collaborators and upload work using the GitHub website.

Emmanuel's supplied facial-recognition Python files are included in `src/selective_surveillance/facial_recognition/`. The added adapter translates them to the shared result contract. The track cache and threshold-selection helper are starter utilities for review and integration. YuNet and SFace are pretrained; the team does not claim to have trained them. Download the model files separately according to the face module's README. Use Python `.ipynb` notebooks for cell-by-cell exploration and scenario analysis; the integrated real-time application is ordinary Python modules launched through Streamlit. R is not part of this repository or its runtime.

## Setup target

Python 3.11 or later is required. The team should create a private virtual environment, install the packages from `pyproject.toml`, install/connect DroidCam, prepare the model files, draw the real zone in Streamlit, and implement the remaining owner-labelled modules before a live demonstration. All application, notebook and evaluation code is Python. Never commit participant photos, face embeddings, model weights, event databases, captures or `.env` files.
