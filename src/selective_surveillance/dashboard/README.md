# Dashboard

**Owner: Ugochukwu Okoroji; Abubakar connects local event data.** The supplied Streamlit application is in `app.py`. It provides:

- connect to the laptop's DroidCam webcam source (or a configured camera stream URL) and show camera connection status;
- display the live feed and provide draw, save, edit and reset controls for the restricted-zone polygon on that view;
- save the selected polygon to private, local configuration, not to Git;
- show tracked people, zone-entry events, current alert status and recent events;
- raise a visible in-app alert as soon as integration reports an unknown, uncertain or face-unclear zone entry;
- provide a stop/start control and a clear camera-disconnected state.

Run the project from its root after installing it with `python -m pip install -e .`:

```powershell
python -m streamlit run src/selective_surveillance/dashboard/app.py --server.address 127.0.0.1
```

All UI and backend application code is Python. The dashboard can connect to a local camera index, a DroidCam stream address, or a test video. The boundary is kept in the current Streamlit session and can be downloaded; it is not automatically restored after restarting the app. Camera changes clear the selected boundary, and camera movement requires drawing and saving it again. There is no Telegram bot or external notification service. Keep evidence access private and bind the student demonstration to localhost until access control is configured.
