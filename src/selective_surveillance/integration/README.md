# Integration

**Owner: Josiah Frank Achile (suggested integration lead).** `controller.py` connects camera capture, detection/zone tracking, face recognition and local event storage behind the Streamlit dashboard. It accepts an integer webcam index or a stream/file address, starts only after a camera and zone are set, checks faces at zone entry, and returns event data for display.

The system must emit events only on zone transitions and keep operational errors separate from identity decisions. Current recognition runs when the tracker reports an entry, not continuously while the entrant remains visible. Recognition caching, retrying unclear faces on later frames, and measured live performance remain to be added. Save events locally before displaying dashboard notices. There is no external message delivery or internet requirement.
