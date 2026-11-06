import io
import csv
import json
import time
import tempfile

from datetime import datetime
from pathlib import Path

import cv2
import streamlit as st

from PIL import Image, ImageDraw, ImageFont, ImageOps
from streamlit_drawable_canvas import st_canvas

from selective_surveillance.integration.controller import SurveillanceController


# ============================================================
# CONFIGURATION
# ============================================================

APP_TITLE = "Smart Surveillance System"

CANVAS_WIDTH = 960
CANVAS_HEIGHT = 540

PROJECT_ROOT = Path(__file__).resolve().parents[3]

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🛡️",
    layout="wide"
)


# ============================================================
# SESSION STATE
# ============================================================

def initialise_state():

    defaults = {
        "controller": None,
        "camera_connected": False,
        "monitoring": False,
        "camera_source": "Phone camera stream",
        "camera_name": "Main Camera",
        "stream_address": "",
        "active_camera_source": None,
        "camera_frame": None,
        "camera_error": None,
        "events": [],
        "saved_region": None,
        "draft_region_json": None,
        "area_shape": "Polygon",
        "canvas_version": 0,
        "last_area_shape": "Polygon",
        "uploaded_frame_bytes": None,
        "page": "Dashboard",
        "last_event_ids": set(),
    }

    for key, value in defaults.items():

        if key not in st.session_state:
            st.session_state[key] = value


initialise_state()


# ============================================================
# BACKEND INITIALIZATION
# ============================================================

def get_controller():

    if st.session_state.controller is None:

        st.session_state.controller = SurveillanceController(
            project_root=PROJECT_ROOT
        )

    return st.session_state.controller


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background: #0b1220;
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] {
        background: #111827;
    }

    [data-testid="stMetric"] {
        background: #172235;
        border: 1px solid #26364d;
        padding: 14px;
        border-radius: 12px;
    }

    div.stButton > button {
        border-radius: 8px;
        min-height: 2.45rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# PLACEHOLDER FRAME
# ============================================================

def make_placeholder_frame():

    image = Image.new(
        "RGB",
        (CANVAS_WIDTH, CANVAS_HEIGHT),
        (13, 22, 36)
    )

    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 26)
    except OSError:
        font = ImageFont.load_default()

    draw.text(
        (CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2),
        "CAMERA NOT CONNECTED",
        fill=(207, 220, 235),
        font=font,
        anchor="mm"
    )

    return image


# ============================================================
# FRAME CONVERSION
# ============================================================

def frame_to_display(frame):

    if frame is None:
        return make_placeholder_frame()

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    return Image.fromarray(rgb)


# ============================================================
# EVENT CONVERSION
# ============================================================

def convert_database_events():

    controller = get_controller()

    database_events = controller.get_events(100)

    converted = []

    for row in database_events:

        event = dict(row)

        recognition = event.get("recognition", "inconclusive")

        if recognition == "known":
            recognition_text = "Known"

        elif recognition == "unknown":
            recognition_text = "Unknown"

        else:
            recognition_text = "Inconclusive"

        alert_status = event.get("alert_status", "not_applicable")
        alert_text_by_status = {
            "dashboard_alert": "On-screen dashboard alert",
            "notified": "On-screen dashboard alert",
            "cooldown": "Repeated alert suppressed",
            "not_applicable": "No unknown identity match",
        }
        alert_text = alert_text_by_status.get(
            alert_status,
            str(alert_status).replace("_", " ").capitalize(),
        )

        image = None

        image_path = (
            event.get("face_image_path")
            or event.get("full_frame_path")
        )

        if image_path:

            try:
                image = Image.open(image_path).copy()
            except Exception:
                image = None

        converted.append({

            "id": str(event.get("id", "")),

            "event_type": "Restricted Zone Entry",

            "recognition": recognition_text,

            "timestamp": event.get("occurred_at", ""),

            "area": event.get("zone", "Restricted Region"),

            "status": alert_text,

            "similarity": event.get("similarity"),

            "image": image,

            "description": (
                f"Track ID: {event.get('track_id', 'Unknown')} | "
                f"Face capture: {event.get('face_status', 'Unknown')}"
            ),

            "demo": False,

        })

    return converted


# ============================================================
# REGION CONVERSION
# ============================================================

def extract_zone_points(region):

    if not region:
        raise ValueError("Save a restricted region first.")

    drawing = region.get("drawing", {})

    objects = drawing.get("objects", [])

    if not objects:
        raise ValueError("No drawing objects were found.")

    obj = objects[0]

    shape = region.get("shape")

    points = []

    if shape == "polygon":

        polygon_points = obj.get("points", [])

        if len(polygon_points) < 3:
            raise ValueError("The polygon requires at least three points.")

        scale_x = float(obj.get("scaleX", 0))
        scale_y = float(obj.get("scaleY", 0))

        for point in polygon_points:

            x = float(point["x"]) * scale_x
            y = float(point["y"]) * scale_y

            points.append((
                int(round(x)),
                int(round(y))
            ))

        
    elif shape == "rectangle":

        left = float(obj.get("left", 0))
        top = float(obj.get("top", 0))

        width = float(obj.get("width", 0))
        height = float(obj.get("height", 0))

        scale_x = float(obj.get("scaleX", 1))
        scale_y = float(obj.get("scaleY", 1))

        right = left + width * scale_x
        bottom = top + height * scale_y

        points = [
            (int(left), int(top)),
            (int(right), int(top)),
            (int(right), int(bottom)),
            (int(left), int(bottom))
        ]

    if len(points) < 3:
        raise ValueError("Invalid restricted region.")

    return points

def draw_saved_region(frame, region):

    if frame is None or not region:
        return frame

    display_frame = frame.copy()

    try:
        points = extract_zone_points(region)

        canvas_width = region.get("canvas_width", CANVAS_WIDTH)
        canvas_height = region.get("canvas_height", CANVAS_HEIGHT)

        frame_height, frame_width = display_frame.shape[:2]

        scale_x = frame_width / canvas_width
        scale_y = frame_height / canvas_height

        scaled_points = [
            (
                int(round(x * scale_x)),
                int(round(y * scale_y))
            )
            for x, y in points
        ]

        polygon = np.array(
            scaled_points,
            dtype=np.int32
        )

        overlay = display_frame.copy()

        cv2.fillPoly(
            overlay,
            [polygon],
            (0, 180, 120)
        )

        display_frame = cv2.addWeighted(
            overlay,
            0.20,
            display_frame,
            0.80,
            0
        )

        cv2.polylines(
            display_frame,
            [polygon],
            True,
            (0, 209, 143),
            3
        )

        cv2.putText(
            display_frame,
            "RESTRICTED ZONE",
            tuple(polygon[0]),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 209, 143),
            2
        )

    except Exception as error:
        print(f"Region display error: {error}")

    return display_frame


# ============================================================
# CAMERA CONTROLS
# ============================================================

def connect_camera():

    controller = get_controller()

    try:

        address = st.session_state.stream_address

        if st.session_state.active_camera_source != address:
            st.session_state.saved_region = None
            st.session_state.draft_region_json = None
            st.session_state.canvas_version += 1

        frame = controller.connect_camera(address)

        st.session_state.camera_connected = True

        st.session_state.active_camera_source = address

        st.session_state.camera_frame = frame

        st.session_state.camera_error = None

        st.success("Camera connected successfully.")

    except Exception as error:

        st.session_state.camera_connected = False

        st.session_state.camera_error = str(error)

        st.error(f"Camera connection failed: {error}")


def disconnect_camera():

    if st.session_state.controller:

        st.session_state.controller.disconnect_camera()

    st.session_state.camera_connected = False

    st.session_state.monitoring = False

    st.session_state.camera_frame = None

    st.session_state.video_source_active = False


# ============================================================
# MONITORING CONTROLS
# ============================================================

def start_monitoring():

    controller = get_controller()

    try:

        zone_points = extract_zone_points(
            st.session_state.saved_region
        )

        controller.set_zone(zone_points)

        controller.start_monitoring()

        st.session_state.monitoring = True

        st.success("Surveillance monitoring started.")

    except Exception as error:

        st.error(f"Unable to start monitoring: {error}")


def stop_monitoring():

    if st.session_state.controller:

        st.session_state.controller.stop_monitoring()

    st.session_state.monitoring = False


# ============================================================
# LIVE CAMERA PROCESSING
# ============================================================

def monitoring_loop():

    if not st.session_state.camera_connected:

        st.warning("Connect a camera first.")
        return

    if not st.session_state.monitoring:

        st.info("Monitoring is currently stopped.")
        return

    controller = get_controller()

    frame = controller.read_camera_frame()

    if frame is None:

        is_video = st.session_state.get(
            "video_source_active",
            False
        )

        if is_video:

            st.success("CCTV video playback completed.")

        else:

            st.error(
                "Camera stream stopped or no frame was received."
            )

        disconnect_camera()

        st.rerun()

        return

    # The detector and region coordinates use the same
    # 960 x 540 coordinate system.

    frame = cv2.resize(
        frame,
        (CANVAS_WIDTH, CANVAS_HEIGHT)
    )

    annotated_frame, new_events = controller.process_frame(frame)

    st.session_state.camera_frame = annotated_frame

    st.image(
        frame_to_display(annotated_frame),
        caption="Live surveillance feed",
        use_container_width=True
    )

    if new_events:
        for event in new_events:
            if event["event"] != "zone_entry":
                continue

            identity = event.get("identity", {})
            status = identity.get("status", "Uncertain")
            message = (
                f"Track ID: {event['track_id']} | "
                f"Recognition: {status}"
            )

            if status == "Unknown":
                alert_status = event.get("storage", {}).get("alert_status")
                if alert_status == "dashboard_alert":
                    st.error(f"Identity not matched inside the restricted zone. {message}")
                    st.toast("An identity-mismatch alert was added to the dashboard.")
                else:
                    st.warning(f"Repeated identity-mismatch entry; alert cooldown applies. {message}")
            elif status == "Known":
                st.info(f"Known person entered the restricted zone. {message}")
            else:
                st.warning(
                    f"Person entered, but identity could not be confirmed. {message}"
                )

    st.session_state.events = convert_database_events()


# ============================================================
# EVENT DISPLAY
# ============================================================

def show_event_card(event):

    with st.container(border=True):

        left, right = st.columns([1, 2])

        with left:

            if event.get("image") is not None:

                st.image(
                    event["image"],
                    use_container_width=True
                )

            else:

                st.info("No evidence image available.")

        with right:

            st.markdown(
                f"### {event.get('event_type', 'Security Event')}"
            )

            st.write("*Event ID:*", event.get("id"))

            st.write(
                "*Date and time:*",
                event.get("timestamp")
            )

            st.write(
                "*Recognition:*",
                event.get("recognition")
            )

            if event.get("similarity") is not None:
                st.write("*Face similarity:*", f"{event['similarity']:.3f}")

            st.write(
                "*Restricted area:*",
                event.get("area")
            )

            st.write(
                "*Alert status:*",
                event.get("status")
            )

            st.caption(event.get("description", ""))


# ============================================================
# CSV EXPORT
# ============================================================

def get_event_csv(events):

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Event ID",
        "Event Type",
        "Timestamp",
        "Recognition",
        "Face Similarity",
        "Restricted Area",
        "Alert Status",
        "Description"
    ])

    for event in events:

        writer.writerow([
            event.get("id"),
            event.get("event_type"),
            event.get("timestamp"),
            event.get("recognition"),
            event.get("similarity"),
            event.get("area"),
            event.get("status"),
            event.get("description")
        ])

    return output.getvalue()


# ============================================================
# ALERT POPUP
# ============================================================

def show_alert_popup():

    events = st.session_state.events

    with st.popover(
        f"🔔 Alerts ({len(events)})",
        use_container_width=True
    ):

        st.markdown("### Recent Security Alerts")

        if not events:

            st.success("No recorded events.")

        else:

            for event in events[:5]:

                st.warning(event.get("event_type"))

                st.write("Recognition:", event.get("recognition"))

                st.write("Time:", event.get("timestamp"))

                st.write("Area:", event.get("area"))

                st.write("Status:", event.get("status"))


# ============================================================
# PAGE HEADER
# ============================================================

def page_header(title, subtitle):

    left, right = st.columns([5, 1])

    with left:

        st.title(title)

        st.caption(subtitle)

    with right:

        show_alert_popup()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## 🛡️ Sentinel")

    st.caption("Smart Surveillance System")

    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Dashboard",
            "Live Monitoring",
            "Event History",
            "Camera Settings"
        ],
        key="page"
    )

    st.divider()

    st.caption("SYSTEM STATUS")

    st.write(
        "📷 Camera:",
        "Connected" if st.session_state.camera_connected else "Disconnected"
    )

    st.write(
        "🛡️ Monitoring:",
        "Running" if st.session_state.monitoring else "Stopped"
    )

    st.write(
        "📐 Restricted area:",
        "Saved" if st.session_state.saved_region else "Not configured"
    )


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    page_header(
        "Smart Surveillance Dashboard",
        "System overview, camera status and security events."
    )

    events = st.session_state.events

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Camera",
        "Connected" if st.session_state.camera_connected else "Disconnected"
    )

    m2.metric(
        "Monitoring",
        "Running" if st.session_state.monitoring else "Stopped"
    )

    m3.metric(
        "Restricted Region",
        "Saved" if st.session_state.saved_region else "Not configured"
    )

    m4.metric(
        "Event Records",
        len(events)
    )

    st.markdown("### Camera Overview")

    if st.session_state.camera_frame is not None:

        preview_frame = draw_saved_region(
            st.session_state.camera_frame,
            st.session_state.saved_region
        )
        
        st.image(
            frame_to_display(preview_frame),
            use_container_width=True
        )

    else:

        st.image(
            make_placeholder_frame(),
            use_container_width=True
        )

    st.markdown("### Quick Controls")

    c1, c2 = st.columns(2)

    with c1:

        if st.button(
            "Connect Camera",
            type="primary",
            use_container_width=True
        ):

            connect_camera()

    with c2:

        if st.button(
            "Disconnect Camera",
            use_container_width=True
        ):

            disconnect_camera()

            st.rerun()

    st.markdown("### Recent Events")

    for event in events[:3]:

        show_event_card(event)


# ============================================================
# LIVE MONITORING
# ============================================================

elif page == "Live Monitoring":

    page_header(
        "Live Monitoring",
        "Camera feed, person detection and restricted-zone monitoring."
    )

    # ========================================================
    # VIDEO UPLOAD
    # ========================================================

    st.markdown("### Upload CCTV Video")

    uploaded_video = st.file_uploader(
        "Select a CCTV video",
        type=["mp4", "avi", "mov", "mkv"],
        key="cctv_video_uploader"
    )

    if uploaded_video is not None:

        st.caption(
            f"Selected video: {uploaded_video.name}"
        )

        if st.button(
            "Load Uploaded Video",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.monitoring
        ):

            try:

                # Disconnect any previously connected source.
                if st.session_state.camera_connected:
                    disconnect_camera()

                # Save the uploaded video temporarily.
                video_extension = Path(
                    uploaded_video.name
                ).suffix.lower()

                video_path = (
                    Path(tempfile.gettempdir())
                    / f"selective_surveillance_video{video_extension}"
                )

                video_path.write_bytes(
                    uploaded_video.getvalue()
                )

                # Mark this source as an uploaded video.
                st.session_state.video_source_active = True

                # Pass the video path to the existing controller.
                st.session_state.stream_address = str(video_path)

                connect_camera()

                if st.session_state.camera_connected:

                    st.success(
                        "CCTV video loaded successfully. "
                        "You can now start monitoring."
                    )

            except Exception as error:

                st.error(
                    f"Unable to load video: {error}"
                )

    st.divider()

    st.markdown("### Camera Preview")

    if st.session_state.camera_connected:

        if st.session_state.monitoring:

            # Streamlit fragments periodically execute without
            # blocking the rest of the application.

            @st.fragment(run_every="0.2s")
            def live_feed():

                monitoring_loop()

            live_feed()

        elif st.session_state.camera_frame is not None:

            preview_frame = draw_saved_region(
                st.session_state.camera_frame,
                st.session_state.saved_region
            )

            st.image(
                frame_to_display(preview_frame),
                use_container_width=True
            )

        else:

            st.info("Camera connected. Start monitoring to process frames.")

    else:

        st.image(
            make_placeholder_frame(),
            use_container_width=True
        )

        st.warning("Camera is not connected.")

    st.markdown("### Monitoring Controls")

    start_col, stop_col = st.columns(2)

    with start_col:

        if st.button(
            "Start Monitoring",
            type="primary",
            use_container_width=True,
            disabled=not st.session_state.camera_connected
        ):

            start_monitoring()

            st.rerun()

    with stop_col:

        if st.button(
            "Stop Monitoring",
            use_container_width=True
        ):

            stop_monitoring()

            st.rerun()

    st.divider()

    st.markdown("### Restricted Region Setup")

    st.write(
        "Draw the restricted area on the camera frame. "
        "The detector uses these coordinates to identify entry."
    )

    uploaded_frame = st.file_uploader(
        "Upload a still frame for region setup (optional)",
        type=["png", "jpg", "jpeg"]
    )

    if uploaded_frame is not None:

        st.session_state.uploaded_frame_bytes = uploaded_frame.getvalue()

    if st.session_state.camera_frame is not None:

        frame = frame_to_display(
            cv2.resize(
                st.session_state.camera_frame,
                (CANVAS_WIDTH, CANVAS_HEIGHT)
            )
        )

    elif st.session_state.uploaded_frame_bytes:

        frame = Image.open(
            io.BytesIO(st.session_state.uploaded_frame_bytes)
        ).convert("RGB")

        frame = ImageOps.fit(
            frame,
            (CANVAS_WIDTH, CANVAS_HEIGHT)
        )

    else:

        frame = make_placeholder_frame()

    selected_shape = st.selectbox(
        "Drawing shape",
        ["Polygon", "Rectangle"],
        key="area_shape"
    )

    if selected_shape != st.session_state.last_area_shape:

        st.session_state.draft_region_json = None

        st.session_state.saved_region = None

        st.session_state.canvas_version += 1

        st.session_state.last_area_shape = selected_shape

    drawing_mode = (
        "polygon" if selected_shape == "Polygon" else "rect"
    )

    canvas_result = st_canvas(
        fill_color="rgba(0,180,120,0.18)",
        stroke_width=3,
        stroke_color="#00D18F",
        background_image=frame,
        update_streamlit=True,
        height=CANVAS_HEIGHT,
        width=CANVAS_WIDTH,
        drawing_mode=drawing_mode,
        initial_drawing=st.session_state.draft_region_json,
        key=f"region_canvas_{st.session_state.canvas_version}"
    )

    if canvas_result.json_data:

        if canvas_result.json_data.get("objects"):

            st.session_state.draft_region_json = canvas_result.json_data

    save_col, clear_col = st.columns(2)

    with save_col:

        if st.button(
            "Save Restricted Region",
            type="primary",
            use_container_width=True
        ):

            if not st.session_state.draft_region_json:
                st.error("Draw a restricted region first.")

            else:

                st.session_state.saved_region = {

                    "shape": selected_shape.lower(),

                    "canvas_width": CANVAS_WIDTH,

                    "canvas_height": CANVAS_HEIGHT,

                    "drawing": st.session_state.draft_region_json,

                    "saved_at": datetime.now().isoformat()
                }

                try:

                    points = extract_zone_points(
                        st.session_state.saved_region
                    )

                    if len(points) < 3:
                        raise ValueError("Invalid region.")

                    st.success("Restricted region saved successfully.")

                except Exception as error:

                    st.session_state.saved_region = None

                    st.error(str(error))

    with clear_col:

        if st.button(
            "Clear Region",
            use_container_width=True
        ):

            st.session_state.saved_region = None

            st.session_state.draft_region_json = None

            st.session_state.canvas_version += 1

            st.rerun()

    if st.session_state.saved_region:

        st.success("Restricted region is configured.")

        st.download_button(
            "Download Region Configuration",
            data=json.dumps(
                st.session_state.saved_region,
                indent=4
            ),
            file_name="restricted_region.json",
            mime="application/json"
        )


# ============================================================
# EVENT HISTORY
# ============================================================

elif page == "Event History":

    page_header(
        "Event History",
        "Review recorded security events and evidence."
    )

    events = st.session_state.events

    filter_a, filter_b = st.columns([2, 1])

    with filter_a:

        search_term = st.text_input(
            "Search by ID, event type, recognition or area"
        )

    with filter_b:

        statuses = ["All"] + sorted({
            event.get("status", "Pending")
            for event in events
        })

        status_filter = st.selectbox(
            "Alert status",
            statuses
        )

    filtered = events

    if status_filter != "All":

        filtered = [
            event for event in filtered
            if event.get("status") == status_filter
        ]

    if search_term.strip():

        needle = search_term.lower().strip()

        filtered = [
            event for event in filtered
            if needle in " ".join(
                str(event.get(key, ""))
                for key in [
                    "id",
                    "event_type",
                    "recognition",
                    "area",
                    "status",
                    "description"
                ]
            ).lower()
        ]

    st.caption(
        f"{len(filtered)} event record(s) shown."
    )

    for event in filtered:

        show_event_card(event)

    if filtered:

        st.download_button(
            "Download Events CSV",
            data=get_event_csv(filtered),
            file_name="event_history.csv",
            mime="text/csv"
        )

    else:

        st.info("No event records match your search.")


# ============================================================
# CAMERA SETTINGS
# ============================================================

elif page == "Camera Settings":

    page_header(
        "Camera Settings",
        "Configure your surveillance camera."
    )

    st.markdown("### Camera Connection Details")

    with st.form("camera_settings_form"):

        source_options = [
            "Phone camera stream",
            "IP camera / RTSP stream",
            "Video source supplied by backend"
        ]

        source = st.selectbox(
            "Camera source",
            source_options
        )

        address = st.text_input(
            "Stream address or camera index",
            value=st.session_state.stream_address,
            placeholder="Example: rtsp://... or 0 for local webcam"
        )

        camera_name = st.text_input(
            "Camera name",
            value=st.session_state.camera_name
        )

        submitted = st.form_submit_button(
            "Save Camera Settings"
        )

        if submitted:

            st.session_state.camera_source = source

            st.session_state.stream_address = address.strip()

            st.session_state.camera_name = camera_name.strip()

            st.success("Camera settings saved.")

    st.markdown("### Connection Status")

    st.write(
        "Camera:",
        "Connected" if st.session_state.camera_connected else "Disconnected"
    )

    st.write(
        "Camera name:",
        st.session_state.camera_name
    )

    st.write(
        "Stream address:",
        "Configured" if st.session_state.stream_address else "Not configured"
    )

    if st.button(
        "Connect Camera",
        type="primary",
        use_container_width=True
    ):

        connect_camera()

        st.rerun()

    if st.button(
        "Disconnect Camera",
        use_container_width=True
    ):

        disconnect_camera()

        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Smart Surveillance System | "
    "YOLO Detection | ByteTrack | Face Recognition | "
    "SQLite Event Storage"
)
