"""Local enrollment UI and single-image recognition preview."""
import json
from pathlib import Path
import cv2
import numpy as np
import streamlit as st
from face_recognition_service import FaceGallery, PIPELINE, extract_embedding

st.set_page_config(page_title="Face enrollment", layout="centered")
st.title("Face enrollment and recognition")
st.caption("Local prototype. First use may download pretrained face weights.")
gallery = FaceGallery()


def decode(upload):
    image = cv2.imdecode(np.frombuffer(upload.getvalue(), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode this image.")
    return image


default_threshold = 0.70
settings_path = Path("embeddings/threshold.json")
if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        if settings["pipeline"] != PIPELINE:
            raise ValueError("Threshold belongs to another embedding pipeline.")
        default_threshold = float(settings["threshold"])
        if not np.isfinite(default_threshold) or not -1 <= default_threshold <= 1:
            raise ValueError("Invalid threshold value.")
        st.caption("Loaded validation threshold; assess separately on held-out queries.")
    except (ValueError, KeyError) as exc:
        st.error(str(exc))
        st.stop()
else:
    st.warning("The 0.70 starting threshold has not been validated on your faces.")
threshold = st.slider("Minimum cosine similarity (higher is stricter)", -1.0, 1.0, default_threshold, 0.01)
margin = st.slider("Required lead over the next identity", 0.0, 0.5, 0.05, 0.01)
enroll_tab, recognize_tab, manage_tab = st.tabs(["Enroll faces", "Test recognition", "Manage people"])

with enroll_tab:
    name = st.text_input("Person name")
    uploads = st.file_uploader("Face photos (different angles and lighting)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    camera = st.camera_input("Or take one photo")
    consent = st.checkbox("I have permission to enroll this person.")
    if st.button("Enroll samples"):
        samples = list(uploads or []) + ([camera] if camera is not None else [])
        if not consent or not samples or not name.strip():
            st.error("Enter a name, select photos, and confirm permission.")
        else:
            try:
                with st.spinner("Checking faces and extracting embeddings..."):
                    vectors = [extract_embedding(decode(sample)) for sample in samples]
                    gallery.enroll(name, vectors)
                st.success(f"Enrolled {len(vectors)} sample(s) for {name.strip()}.")
            except Exception as exc:
                st.error(f"Enrollment failed: {exc}")

with recognize_tab:
    query = st.file_uploader("Held-out photo to recognize", type=["jpg", "jpeg", "png"], key="query")
    if st.button("Recognize") and query is not None:
        try:
            result = gallery.match(extract_embedding(decode(query)), threshold, margin)
            st.write(result)
            st.caption("Similarity is a score, not a probability or percentage.")
        except Exception as exc:
            st.error(f"Recognition failed: {exc}")

with manage_tab:
    people = gallery.people()
    st.dataframe([{"Name": name, "Samples": count} for name, count in people])
    if people:
        selected = st.selectbox("Person to remove", [name for name, _ in people])
        confirm = st.checkbox("Confirm removal of all enrolled samples for this person")
        if st.button("Remove person", disabled=not confirm):
            gallery.delete(selected)
            st.rerun()
