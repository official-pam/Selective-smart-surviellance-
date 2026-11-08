# Storage

**Owner: Abubakar Ahmed.** `event_store.py` writes and reads SQLite event rows, saves optional evidence images, applies cooldown timestamps and purges expired rows and images. `paths.py` selects a writable local application-data directory for the gallery, event database, evidence and zone settings. On Windows the default is `%LOCALAPPDATA%\SelectiveSmartSurveillance`; `SELECTIVE_SURVEILLANCE_DATA_DIR` can select a different local folder. Keep biometric and event data local; never commit them.

Write event records before displaying an alert. Dashboard queries must read saved events, not sample data. Keep participant names and image files out of commits.
