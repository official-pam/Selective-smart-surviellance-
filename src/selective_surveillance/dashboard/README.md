# Dashboard

**Owner: Ugochukwu Okoroji; Abubakar connects local event data.** Build the Streamlit operator dashboard for the end-to-end live system. It must:

- connect to the laptop's DroidCam webcam source (or a configured camera stream URL) and show camera connection status;
- display the live feed and provide draw, save, edit and reset controls for the restricted-zone polygon on that view;
- save the selected polygon to private, local configuration, not to Git;
- show tracked people, zone-entry events, current alert status and recent events;
- raise a visible in-app alert as soon as integration reports an unknown, uncertain or face-unclear zone entry;
- provide a stop/start control and a clear camera-disconnected state.

Use Python and Streamlit. There is no Telegram bot or external notification service. Keep evidence access private and bind the student demonstration to localhost until access control is configured. This folder is an implementation assignment; the dashboard is not yet fully implemented.
