# Storage

**Owner: Abubakar Ahmed.** `event_store.py` writes and reads SQLite event rows, saves optional evidence images, applies cooldown timestamps and purges expired rows and images. Database and evidence files go under the ignored `private_data/` directory. Keep the gallery, event database and captures local; never commit them.

Write event records before displaying an alert. Dashboard queries must read saved events, not sample data. Keep participant names and image files out of commits.
