# Integration

**Owner: Josiah Frank Achile (suggested integration lead).** Connect the live camera source, detector/zone tracker, face-recognition adapter, selection policy, local event store and Streamlit dashboard using `contracts.py`.

The system must join detections and recognition by `track_id`, emit events only on zone transitions, avoid repeated recognition on every frame, and keep operational errors separate from identity decisions. It must save an event before exposing the corresponding alert in the Streamlit dashboard. There is no external message delivery or internet requirement.
