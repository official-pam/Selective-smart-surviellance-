# Storage

**Owner: Abubakar Ahmed.** Store timestamp, zone, tracking ID, identity status, accepted name, similarity, face/frame evidence paths and alert delivery state. Store images below the ignored `private_data/evidence/` directory. Add a documented retention/deletion job and restrict access to biometric evidence.

Write event records before alert delivery. Dashboard queries must read saved events, not sample data. Keep credentials, participant names and image files out of commits.
