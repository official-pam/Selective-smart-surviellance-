# System architecture

## Real-time flow

```text
Phone running DroidCam
        |  Wi-Fi or USB to DroidCam PC client / supported stream
        v
OpenCV camera reader on the laptop
        |
        +------------------------------> Streamlit dashboard
        |                                  | live camera preview
        |                                  | draw and save restricted boundary
        |                                  | camera status, events and notices
        v
YOLO person detection -> ByteTrack track IDs
        |
        v
Check the person's foot point against the saved region
        | outside / no boundary crossing       | zone-entry transition
        v                                      v
Keep monitoring                          Person crop -> YuNet face detection
                                                -> SFace embedding + gallery match
                                                -> Known / Unknown / Uncertain
                                                |  or face unclear / error
                                                v
                                         Save local event in SQLite
                                                |
                                                v
                                         Show an on-screen dashboard notice
```

The system code is Python. Streamlit is the operator dashboard, not a model. There is no Telegram or external messaging service. Unknown means that the enrolled gallery did not produce an accepted match; it does not prove that a person is a threat. Errors and unclear faces should be reported as verification problems, separately from identity decisions. DroidCam documents Wi-Fi and USB PC connections; Bluetooth is not an assumed connection method. See the [DroidCam connection guide](https://www.dev47apps.com/droidcam/connect/).

## Modules and responsibilities

1. **Camera and dashboard — Ugochukwu:** connect to the selected webcam/stream/video, show the live view, and let the operator define a region on that camera view.
2. **Person detection and zone transitions — Williams:** detect people, track them across frames, and report when each track enters or exits the polygon.
3. **Face enrolment and recognition — Emmanuel:** create reference embeddings and compare an entrant crop against the enrolled gallery. A match score is cosine similarity, not a probability.
4. **Event storage and alert policy — Abubakar:** save an event and any approved evidence locally, manage retention/cooldown, and make dashboard notices available.
5. **Integration — Josiah:** pass camera frames and zone geometry through the modules, keep track IDs attached to the right observations, and produce one consistent event record.
6. **Scenario evaluation — Joseph:** evaluate accuracy, speed, error cases and attack scenarios using a held-out protocol; record results rather than claims.

## What the supplied code currently does

The current controller reads a frame, resizes it to 960 by 540, runs person tracking and checks the selected zone. When a track enters, it attempts face recognition once on that frame and stores an event. Unknown matches can create a local dashboard alert; Known entries are informational; inconclusive results are logged and shown as needing review. The dashboard also supports replaying a local video for repeatable scenario evaluation.

The repository contains a short-lived recognition-cache helper, but the controller does not yet use it. It also does not retry unclear faces on later frames. The fixed-size resize may distort the image and lower face detail. These are planned improvements, not current capabilities.

## Timing, privacy and failure behaviour

- The dashboard requests a frame update about every 0.2 seconds. That is a target update interval, not evidence of system FPS. Measure actual frames per second and entry-to-notice delay on the test laptop.
- Keep face galleries, event databases and evidence images in ignored `private_data/`. Do not store evidence unless needed for the agreed evaluation and consent.
- A missing face is not an Unknown match. A model exception is an operational error, not an identity result.
- If the camera disconnects, show the disconnected state and avoid creating an entry from a failed frame.
- The dashboard should distinguish Known entry, identity-not-matched notice, needs-review notice, and system error.
- There is no anti-spoofing or liveness detector in the supplied model pipeline. Report acceptance of printed-photo, screen and replay attacks as a vulnerability metric unless a liveness method is added and evaluated.
