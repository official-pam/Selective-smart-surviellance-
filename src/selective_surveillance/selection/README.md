# Selection policy

The assignment does not name a separate selection-policy owner; implement this as part of integration. Read the detection module's zone state and recognition status. Ignore people outside the restricted zone. Log an entry for a known staff member without an intruder alert. Create an alert candidate for an unknown person or a face-unclear entry. Apply the alert cooldown after recording the event.

Keep `UNKNOWN`, `UNCERTAIN`, `FACE_UNCLEAR` and `ERROR` distinct. An exception/model failure is not evidence that someone is unknown. Only accept a person's name when face recognition returns `KNOWN`.
