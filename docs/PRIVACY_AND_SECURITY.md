# Privacy and security checklist

This prototype handles face images and face embeddings. Before recording anyone, get informed consent and approval from the responsible institution. Use volunteers who understand how images will be collected, tested, stored and deleted.

- Keep participant photos, embeddings, captures, databases and test labels out of Git.
- Keep bot tokens and other credentials in environment variables or a local `.env` file excluded by `.gitignore`.
- Restrict who can enrol people, open face images, query events and change the restricted-zone polygon.
- Save only the evidence needed for the project; apply and document a retention period and deletion procedure.
- Bind a demo dashboard to localhost unless access control and a secure network deployment are explicitly configured.
- Do not treat a face match as proof of liveness, intent or wrongdoing. The result is an identity-system decision with measured error rates.
- Log model errors, unclear faces, alert delivery failures and cache expiry without logging secrets.
- Keep a private consent/ground-truth record separate from public source code and demo materials.

The team must review institutional rules and applicable privacy requirements before any real deployment. This student prototype is not a substitute for a reviewed security system.
