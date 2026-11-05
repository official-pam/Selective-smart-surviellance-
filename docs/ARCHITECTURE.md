# System architecture

## Processing flow

```text
Camera or video source
        |
        v
YOLO person detection + ByteTrack persistent IDs
        |
        v
Restricted-zone membership and entry/exit
        |
        +---- outside zone ----------------------> ignored by selection policy
        |
        v
Face crop -> YuNet detection/alignment -> SFace similarity
        |                              |
        |                    per-track recognition cache
        v
Known / Unknown / Uncertain / Face unclear
        |
        v
Event policy: record entry; alert only for unknown or unclear face
        |
        +----> event database + retained evidence
        +----> alert sender with cooldown and retry state
        +----> dashboard reads saved events
```

## Module boundaries

1. **Video source** reads frames and supplies a timestamp and frame sequence number. It does not decide identity or whether to alert.
2. **Detection and zone** returns a persistent `track_id`, full-frame bounding box, confidence and zone state for each person. The restricted area is configured as polygon points relative to frame width and height. It reports entry and exit rather than making face decisions.
3. **Face recognition** receives a crop and `track_id`. It returns a decision status, a name only on accepted matches, a cosine similarity score, and a reason for an unclear face. It is evaluated separately on known and unenrolled people.
4. **Integration and selection** joins the detection result to recognition by tracking ID, reuses recent recognition only for a still-valid track, and creates events for zone transitions. It does not equate model similarity with a probability.
5. **Storage and alerting** first save the event and evidence paths. The alert sender then tries delivery, records success/failure and obeys cooldown/retry rules. Local evidence remains recorded if the network is down.
6. **Dashboard** reads saved event records and displays real events. It does not rerun recognition or mutate stored events.

## Timing and cache behaviour to implement

Do not run face detection on every video frame. `integration/recognition_cache.py` provides a starting point to cache an accepted or unknown result by persistent track ID for a short configured interval, then recheck. Do not cache `Uncertain` or `Face unclear` as a final identity. Clear cache entries when a track ends, and force recheck after a long gap, tracker reset, or significant change in face quality. Record cache hits and fresh checks so speed measurements are explainable.

## Failure handling

- Camera read failure: log the failure and stop or reconnect according to an explicit setting.
- Person without a usable face: preserve the track/zone entry and emit `Face unclear`.
- Recognition exception/model unavailable: report a module error; never convert an exception into a confident Unknown decision.
- Database error: show a visible error and do not claim the event was recorded.
- Telegram/network failure: keep the local event, mark the alert pending/failed, and retry under the configured policy.
- Tracker ID reset: clear that track's recognition cache so an old identity is not attached to a new person.
