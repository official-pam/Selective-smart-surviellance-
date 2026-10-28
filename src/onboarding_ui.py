"""Enrollment and a transparent matching check inside the existing dashboard."""
import hashlib
import cv2
import numpy as np
import streamlit as st
from src.face_gallery import FaceGallery, ROOT, extract_embedding, load_policy


def decode(upload):
    raw = upload.getvalue()
    if len(raw) > 15 * 1024 * 1024:
        raise ValueError("Use an image smaller than 15 MB.")
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Image could not be read.")
    return raw, image


def show_result(result):
    st.write(f"**Result: {result['name']}**")
    score = result.get("similarity")
    st.write(f"Best similarity: {score:.4f}" if score is not None else "Best similarity: unavailable")
    st.write(f"Threshold: {result['threshold']:.4f}")
    st.write(result["reason"])
    if result.get("scores"):
        st.dataframe(result["scores"], hide_index=True)
    st.caption("Cosine similarity is a match score, not a probability of identity.")


def render_onboarding():
    with st.expander("Face onboarding and matching check"):
        try:
            gallery = FaceGallery()
            policy = load_policy()
        except (ValueError, OSError) as exc:
            st.error(str(exc))
            return
        st.caption("Original Facenet model · local storage · no retraining when a person is enrolled.")
        st.write(f"Threshold: {policy['threshold']:.4f} ({policy['status']}); ambiguity margin: {policy['margin']:.4f} (provisional).")
        people = gallery.people()
        if people:
            st.dataframe([{"Person": n, "Samples": count} for n, count in people], hide_index=True)
        else:
            st.info("No faces enrolled in this application's Facenet gallery yet.")
        st.caption("Enroll only people who have agreed to take part. Use several clear images from different angles. Keep separate photos for validation.")
        name = st.text_input("Person's name", key="enroll_name")
        uploads = st.file_uploader("Reference photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="enroll_photos")
        use_camera = st.checkbox("Use a webcam snapshot for enrollment", key="enroll_camera_toggle")
        snapshot = None
        if use_camera:
            st.caption("Stop the live camera first if the browser cannot access the webcam.")
            snapshot = st.camera_input("Enrollment snapshot", key="enroll_snapshot")
        if st.button("Enroll face", key="enroll_submit"):
            samples = list(uploads or []) + ([snapshot] if snapshot else [])
            if not samples:
                st.warning("Upload reference photos or take a snapshot.")
            else:
                try:
                    vectors, hashes = [], []
                    with st.spinner("Checking face quality and creating local reference embeddings..."):
                        for sample in samples:
                            raw, image = decode(sample)
                            vectors.append(extract_embedding(image))
                            hashes.append(hashlib.sha256(raw).hexdigest())
                        count = gallery.enroll(name, vectors, hashes)
                    st.success(f"Added {count} reference sample(s). Live recognition reads the updated gallery automatically.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Enrollment was not completed: {exc}")
        if st.button("Import existing known_faces photos", key="import_legacy"):
            with st.spinner("Checking existing photos..."):
                count, errors = gallery.import_legacy(ROOT / "known_faces")
            st.success(f"Imported {count} samples. Original photos were preserved.")
            for error in errors:
                st.warning(error)
        st.divider()
        st.write("**Check a separate image**")
        probe = st.file_uploader("Test photo (different from the reference photos)", type=["jpg", "jpeg", "png"], key="probe_photo")
        if st.button("Check face match", key="probe_submit"):
            if probe is None:
                st.warning("Choose a test photo first.")
            else:
                try:
                    _, image = decode(probe)
                    with st.spinner("Comparing with enrolled people..."):
                        result = gallery.match(extract_embedding(image))
                    show_result(result)
                except Exception as exc:
                    st.error(f"Matching check failed: {exc}")
