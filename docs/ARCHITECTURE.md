# System architecture

## Intended end-to-end flow

```text
Phone camera running DroidCam
        |  Wi-Fi (or supported USB connection)
        v
DroidCam PC client / webcam source on laptop
        |
        +---------------------> Streamlit live dashboard
        |                         | draw / save / edit / reset zone polygon
        |                         | show live feed, status, recent events/alerts
        v
Python camera reader -> YOLO person detection -> ByteTrack tracking IDs
        |
        v
Restricted-zone membership + entry/exit transition
        | outside zone                         | newly entered zone
        v                                      v
Continue monitoring, no intruder alert    Crop face -> YuNet -> SFace
                                               | per-track cache
                                               v
                                     Known / Unknown / Uncertain / Face unclear
                                               |
                                               v
                                     Save event and necessary evidence locally
                                               |
                                               v
                                     Immediate visible Streamlit alert
                                     for unknown / uncertain / unclear entry
```

The application is a local, Python-only system. Streamlit is the operator interface; it controls and presents the pipeline but does not replace the camera or recognition models. The real-time mode reads a live camera source; uploaded video is reserved for repeatable, offline evaluation. DroidCam's documented PC connection methods are Wi-Fi and USB, so the project must not assume Bluetooth input. The actual webcam source and device index depend on the laptop setup. See the [DroidCam connection guide](https://www.dev47apps.com/droidcam/connect/).

## Module boundaries

1. **Camera input** reads live frames from the laptop's DroidCam webcam source or a configured stream address. It supplies timestamps and frame sequence numbers, but does not decide identity or alert policy.
2. **Dashboard and zone setup** previews the live camera, lets an authorised operator draw/edit/save/reset the restricted polygon, and displays camera/model status, people, events and visible alerts. Polygon points are normalized so they scale with frame resolution.
3. **Detection and tracking** returns a persistent `track_id`, bounding box, confidence and inside/outside state. It reports zone transitions; it does not decide identity.
4. **Face recognition** checks an entrant's face crop and returns Known, Unknown, Uncertain, Face unclear or Error. A name is returned only for an accepted Known match.
5. **Integration and selection** applies zone-entry policy, connects recognition to its tracking ID, uses short-lived cache entries only for active tracks, and prevents repeated alerts for the same continuing entry.
6. **Local storage and dashboard alerting** save an event and the minimum necessary evidence, then raise an immediate visible Streamlit alert for an unknown, uncertain or face-unclear entry. No Telegram bot, external alert service or R code is part of the architecture.

## Timing and cache behaviour

Do not run face detection on every video frame. `integration/recognition_cache.py` provides a starting point to cache an accepted or unknown result by persistent track ID for a short configured interval, then recheck. Do not cache `Uncertain`, `Face unclear` or `Error` as a final identity. Clear cache entries when a track ends, and force recheck after a long gap, tracker reset, or significant change in face quality. Record cache hits and fresh checks so speed measurements are explainable.

## Failure handling

- Camera read failure: show an offline/reconnecting state in the dashboard and stop or reconnect according to an explicit setting.
- Person without a usable face: preserve the track/zone entry and emit `Face unclear`.
- Recognition exception/model unavailable: report an operational error; never convert an exception into a confident Unknown decision.
- Database error: show a visible error and do not claim the event was recorded.
- Dashboard alert: display and store the alert locally, and apply a cooldown to avoid flooding while someone remains in the zone.
