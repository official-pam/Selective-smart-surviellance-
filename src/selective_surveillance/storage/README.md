# Storage

**Owner: Abubakar Ahmed.** Store timestamp, zone, tracking ID, identity status, accepted name, similarity, necessary face/frame evidence paths and local dashboard-alert state. Store images below the ignored `private_data/evidence/` directory. Add a documented retention/deletion job and restrict access to biometric evidence.

Write event records before displaying an alert. Dashboard queries must read saved events, not sample data. Keep participant names and image files out of commits.
