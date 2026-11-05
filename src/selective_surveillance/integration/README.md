# Integration

**Owner: Josiah Frank Achile (suggested integration lead).** Connect a frame source, detector/zone tracker, face-recognition adapter, selection policy, event store, alert outbox and dashboard using `contracts.py`.

The system must join detections and recognition by `track_id`, emit events only on zone transitions, avoid repeated recognition on every frame, and keep operational errors separate from identity decisions. It must save an event before sending an alert and preserve a pending state when there is no internet.
