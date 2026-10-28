"""
Smart Security Camera — Live Dashboard
Run with: streamlit run dashboard.py
Reads from security.db — refreshes every 5 seconds automatically
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import time

from src.database import init_database, get_recent_events, get_stats, get_hourly_activity

# ─── PAGE CONFIG ───────────────────────────────────────────
st.set_page_config(
    page_title  = "Group Selective Surveillance System for Security",
    page_icon   = "🔒",
    layout      = "wide",
    initial_sidebar_state = "expanded"
)

init_database()

# ─── CUSTOM CSS ────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark theme */
    .stApp { background-color: #0d1117; color: #c9d1d9; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
    }

    /* Alert table */
    .alert-known   { color: #3fb950; font-weight: bold; }
    .alert-unknown { color: #f85149; font-weight: bold; }

    /* Header */
    .dashboard-header {
        background: linear-gradient(90deg, #161b22, #0d1117);
        border: 1px solid #30363d;
        border-left: 4px solid #3fb950;
        padding: 16px 24px;
        border-radius: 8px;
        margin-bottom: 24px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }

    /* Status dot */
    .status-live {
        display: inline-block;
        width: 10px; height: 10px;
        background: #3fb950;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 1.5s infinite;
    }
</style>
""", unsafe_allow_html=True)


# ─── SIDEBAR ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔒 Security Cam")
    st.markdown("---")

    auto_refresh = st.toggle("Auto Refresh", value=False)
    refresh_rate = st.slider("Refresh every (seconds)", 3, 30, 5)
    st.markdown("---")

    show_known   = st.checkbox("Show Known Persons", value=True)
    show_unknown = st.checkbox("Show Unknown Persons", value=True)
    max_events   = st.slider("Max events to show", 10, 100, 25)

    st.markdown("---")
    st.markdown(f"**Last refresh:**")
    st.markdown(f"`{datetime.now().strftime('%H:%M:%S')}`")

    if st.button("🔄 Refresh Now"):
        st.rerun()


# ─── HEADER ────────────────────────────────────────────────
st.markdown("""
<div class="dashboard-header">
    <h2 style="margin:0; color:#fff;">
        🔒 Smart Group Selective Surveillance System for Security
    </h2>
    <p style="margin:4px 0 0; color:#8b949e; font-size:14px;">
        Real-time monitoring · YOLOv8 · DeepFace · ByteTrack
    </p>
</div>
""", unsafe_allow_html=True)


from src.local_runtime import ROOT, RUNTIME, STATE, FRAME, STOP, read_status
import subprocess
import sys
import os

from src.onboarding_ui import render_onboarding
render_onboarding()

st.subheader("Live camera")
import importlib.util
models_ready = all(importlib.util.find_spec(module) is not None for module in ("ultralytics", "deepface", "tensorflow", "lap"))
if not models_ready:
    st.caption("Install requirements-local-engine.txt before starting the camera.")
source_kind = st.radio("Video source", ["Laptop webcam / phone stream", "Upload a video"], horizontal=True)
video_upload = None
if source_kind == "Upload a video":
    video_upload = st.file_uploader("Test video", type=["mp4", "avi", "mov", "mkv"], key="test_video")
    camera_source = ""
    st.caption("Select a clip, then click Start camera. Clip timestamps drive the alert timer; processing may be slower than real time.")
else:
    camera_source = st.text_input("Camera source (0 for the laptop webcam, or your phone stream URL)", "0")
start_col, stop_col = st.columns(2)
with start_col:
    if st.button("Start camera", type="primary", disabled=not models_ready or (source_kind == "Upload a video" and video_upload is None)):
        current = read_status()
        alive = current.get("status") in {"running", "loading"} and time.time()-current.get("updated", 0) < 60
        if alive:
            st.warning("Camera engine is already running.")
        else:
            STOP.unlink(missing_ok=True)
            if source_kind == "Upload a video":
                import hashlib
                raw = video_upload.getvalue()
                input_dir = RUNTIME / "inputs"
                input_dir.mkdir(exist_ok=True)
                destination = input_dir / (hashlib.sha256(raw).hexdigest() + Path(video_upload.name).suffix.lower())
                destination.write_bytes(raw)
                camera_source = str(destination)
            environment = os.environ.copy()
            environment.update({"CAMERA_SOURCE": camera_source, "ALERT_METHOD": "local", "DEEPFACE_HOME": str(RUNTIME), "PYTHONIOENCODING": "utf-8", "OMP_NUM_THREADS": "2", "TF_NUM_INTRAOP_THREADS": "2", "TF_NUM_INTEROP_THREADS": "1", "YOLO_CONFIG_DIR": str(RUNTIME / "ultralytics")})
            with open(RUNTIME / "engine.log", "a", encoding="utf-8") as log:
                subprocess.Popen([sys.executable, "-u", str(ROOT / "main.py")], cwd=ROOT, env=environment, stdout=log, stderr=log, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            st.success("Camera engine is starting. The preview appears below once frames arrive.")
with stop_col:
    if st.button("Stop camera"):
        STOP.touch()
        st.info("Stop requested. Camera will release after the current frame.")

@st.fragment(run_every=1)
def live_preview():
    state = read_status()
    state_name = state.get("status", "stopped")
    age = time.time()-state.get("updated", 0)
    if state_name == "running" and age < 30:
        st.caption(f"Camera running | {state.get('frames', 0)} frames | {state.get('tracks', 0)} tracks | {state.get('fps', 0)} FPS")
        matches = state.get("identities", [])
        if matches:
            st.dataframe(matches, hide_index=True)
        try:
            st.image(FRAME.read_bytes(), width="stretch")
        except OSError:
            st.info("Waiting for the next video frame...")
    elif state_name == "loading" and age < 120:
        st.info(state.get("message", "Loading models..."))
    elif state_name == "error":
        st.error(state.get("message", "Camera engine stopped."))
    else:
        st.info(state.get("message", "Camera is stopped. Select a source and click Start camera. Close any other app using the webcam first."))

live_preview()
st.divider()

# ─── LOAD DATA ─────────────────────────────────────────────
stats  = get_stats()
events = get_recent_events(limit=max_events)
hourly = get_hourly_activity()


# ─── METRIC CARDS ──────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label = "🔔 Total Alerts",
        value = stats.get("total_alerts", 0)
    )
with col2:
    st.metric(
        label = "✅ Known Persons",
        value = stats.get("known_alerts", 0),
        delta = f"Today: {stats.get('today_alerts', 0)}"
    )
with col3:
    st.metric(
        label = "🚨 Unknown Intruders",
        value = stats.get("unknown_alerts", 0)
    )
with col4:
    st.metric(
        label = "👁 Total Detections",
        value = stats.get("total_detections", 0)
    )
with col5:
    most_seen = stats.get("most_seen", {})
    st.metric(
        label = "👤 Most Seen",
        value = most_seen.get("name", "N/A"),
        delta = f"{most_seen.get('count', 0)} times"
    )

st.markdown("---")


# ─── CHARTS ROW ────────────────────────────────────────────
chart_col1, chart_col2 = st.columns([2, 1])

with chart_col1:
    st.markdown("### 📊 Hourly Activity")
    if hourly:
        df_hourly = pd.DataFrame(hourly)
        fig = px.bar(
            df_hourly,
            x="hour", y="count",
            color_discrete_sequence=["#3fb950"],
            labels={"hour": "Hour", "count": "Alerts"},
        )
        fig.update_layout(
            paper_bgcolor = "#161b22",
            plot_bgcolor  = "#161b22",
            font_color    = "#c9d1d9",
            showlegend    = False,
            margin        = dict(l=0, r=0, t=10, b=0),
            height        = 280
        )
        fig.update_xaxes(gridcolor="#30363d")
        fig.update_yaxes(gridcolor="#30363d")
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No activity data yet. Run main.py and trigger some alerts.")

with chart_col2:
    st.markdown("### 🥧 Known vs Unknown")
    known   = stats.get("known_alerts", 0)
    unknown = stats.get("unknown_alerts", 0)

    if known + unknown > 0:
        fig2 = go.Figure(go.Pie(
            labels = ["Known", "Unknown"],
            values = [known, unknown],
            marker_colors = ["#3fb950", "#f85149"],
            hole   = 0.5,
        ))
        fig2.update_layout(
            paper_bgcolor = "#161b22",
            font_color    = "#c9d1d9",
            showlegend    = True,
            margin        = dict(l=0, r=0, t=10, b=0),
            height        = 280
        )
        st.plotly_chart(fig2, width="stretch")
    else:
        st.info("No alert data yet.")

st.markdown("---")


# ─── RECENT ALERTS TABLE ───────────────────────────────────
st.markdown("### 🗃 Recent Alert Events")

if events:
    st.caption("Similarity is not a probability. Older events used the previous matching implementation.")
    df = pd.DataFrame(events)

    # Filter based on sidebar
    if not show_known:
        df = df[df["is_known"] == 0]
    if not show_unknown:
        df = df[df["is_known"] == 1]

    # Format columns
    df["Status"] = df["is_known"].apply(
        lambda x: "✅ Known" if x else "🚨 Unknown"
    )
    df["Similarity score"] = df["confidence"].apply(lambda x: f"{x / 100:.4f}")
    df["Duration"]   = df["duration"].apply(lambda x: f"{x:.1f}s")

    # Select display columns
    display_df = df[[
        "timestamp", "track_id", "name",
        "Status", "Similarity score", "Duration"
    ]].rename(columns={
        "timestamp": "Time",
        "track_id":  "Track ID",
        "name":      "Person",
    })

    st.dataframe(
        display_df,
        width = "stretch",
        hide_index          = True,
        height              = 320
    )
else:
    st.info("No alert events yet. Run main.py and wait 30 seconds in frame.")


# ─── CAPTURED IMAGES ───────────────────────────────────────
st.markdown("---")
st.markdown("### 📸 Recent Captured Images")

captures_dir = Path("captures")
if captures_dir.exists():
    # Get latest 6 images
    images = sorted(
        captures_dir.glob("*.jpg"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )[:6]

    if images:
        img_cols = st.columns(3)
        for i, img_path in enumerate(images):
            with img_cols[i % 3]:
                st.image(
                    str(img_path),
                    caption = img_path.name,
                    width = "stretch"
                )
    else:
        st.info("No images captured yet.")
else:
    st.info("captures/ folder not found.")


# ─── AUTO REFRESH ──────────────────────────────────────────
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
    