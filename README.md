# Group 4: Selective Smart Surveillance System

This project is a real-time prototype for a consent-based, restricted ICT/server room. It watches a configured zone, follows people, checks whether their faces match enrolled staff, records entries, and alerts the responsible security contact when an unrecognised or unclear face enters.

The repository was reorganised around the team assignment. Each person owns a module, and the shared Python records in `src/selective_surveillance/contracts.py` define how those modules exchange information.

## Team ownership

| Owner | Module | Main files |
|---|---|---|
| Williams Emehel | Person detection, tracking and restricted zone | `src/selective_surveillance/detection/` |
| Emmanuel John | Staff enrolment and face recognition | `src/selective_surveillance/facial_recognition/` |
| Abubakar Ahmed | Alerts, image storage and event records | `src/selective_surveillance/alerting/`, `src/selective_surveillance/storage/` |
| Ugochukwu Okoroji | Dashboard, with Abubakar connecting event data | `src/selective_surveillance/dashboard/` |
| Josiah Frank Achile | Integration lead and shared interfaces | `src/selective_surveillance/integration/`, `docs/INTERFACES.md` |
| Joseph Ekuma | End-to-end test lead, results and demonstration | `evaluation/`, `docs/TEST_PLAN.md` |

## Project layout

```text
configs/default.toml                      Shared settings; polygon points are examples
docs/TEAM_ROLES.md                         Responsibilities and handoffs
docs/ARCHITECTURE.md                       Processing flow and module boundaries
docs/INTERFACES.md                         Shared inputs, outputs and decisions
docs/TEST_PLAN.md                          Scenario-based acceptance and reporting
docs/PRIVACY_AND_SECURITY.md               Consent, access, retention and secrets
src/selective_surveillance/contracts.py    Shared typed Python records
src/selective_surveillance/detection/      Person detection, tracking and zone status
src/selective_surveillance/facial_recognition/  YuNet/SFace module from Emmanuel's ZIP
src/selective_surveillance/integration/    Connect modules; cache by tracking ID
src/selective_surveillance/alerting/       Alert only on configured security events
src/selective_surveillance/storage/        Event database and retained image paths
src/selective_surveillance/dashboard/      Read-only view of real event records
evaluation/                                Scenario result analysis and reports
tests/                                     Module and end-to-end checks
```

## Build order

1. Agree on the records in `contracts.py` before changing module interfaces.
2. Complete person tracking and the restricted-zone entry/exit output.
3. Complete face enrolment and calibrated Known/Unknown/Uncertain/Face unclear decisions.
4. Use `evaluation/face_threshold.py` on independent validation scores; connect `integration/recognition_cache.py` to each persistent tracking ID.
5. Record entries and deliver an alert for an unknown or face-unclear person entering the zone.
6. Connect the dashboard to the same event database.
7. Run the scenario plan, fix integration issues, record measured results, and prepare a live demo with a recorded backup.

## Current state

This commit establishes the file structure, team ownership, data contracts, a face-recognition adapter, a short-lived track cache, a validation-threshold helper, settings example and safety/testing plan. It is the shared integration foundation; it is **not yet a running camera application**. Person detection, zone transitions, event storage, alert delivery and the dashboard still need their owners' implementations and integration. The zone polygon and alert contact in the settings are examples that the team must replace.

Team members can add files without using a terminal. The repository owner must first give them Write access. Follow [`CONTRIBUTING.md`](CONTRIBUTING.md) to invite collaborators and upload work using the GitHub website.

Emmanuel's supplied facial-recognition Python files are included in `src/selective_surveillance/facial_recognition/`. The added adapter translates them to the shared result contract. The track cache and threshold-selection helper are starter utilities for review and integration. YuNet and SFace are pretrained; the team does not claim to have trained them. Download the model files separately according to the face module's README. The Colab evaluation notebook remains a separate experiment artifact and is not used as the real-time server.

## Setup target

Python 3.11 or later is required. The team should create a private virtual environment, install the packages from `pyproject.toml`, prepare the model files, review `configs/default.toml`, and implement the remaining owner-labelled modules before starting a live camera. Never commit participant photos, face embeddings, model weights, event databases, captures, `.env` files, or Telegram tokens.
