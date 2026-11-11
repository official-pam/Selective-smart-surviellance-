# Face enrolment and recognition

**Owner: Emmanuel John.** This folder contains the supplied Python face-recognition module: YuNet detects and aligns faces, SFace creates normalized embeddings, the gallery stores enrolled references, and the matcher returns Known, Unknown or Uncertain.

The live controller in `integration/controller.py` calls this module for tracked people inside the restricted zone. It retries on later frames when a face is unclear, uses the cached track crop, and stops after a known match, zone exit, or the configured attempt limit. Face detection receives shadow-enhanced pixels in low light; SFace still uses the original pixels so enrollment and recognition share the same embedding pipeline. This does not provide liveness or anti-spoofing.

## Model files

Place these local model files in the ignored project-level `models/` directory:

- `face_detection_yunet_2023mar.onnx`
- `face_recognition_sface_2021dec.onnx`

The controller loads both files from `models/`. Do not commit model files or enrolled face images.

## Enrollment and matching

`FaceGallery` currently stores one normalized 128-value reference embedding for each full name. It prevents duplicate names, saves the gallery as JSON, and checks model/pipeline identifiers when loading. The gallery is saved as `face_gallery.json` in the local application-data directory returned by `storage/paths.py`.

The current gallery is not yet a multi-image profile and does not perform a documented augmentation sequence. Before extending enrollment, compare multiple consenting captures under normal and difficult conditions. If synthetic augmentation is tried, keep those samples grouped with the original person and do not count them as independent test participants.

The similarity threshold and ambiguity margin in `config.py` are provisional. Joseph's independent validation set should be used to choose them, then freeze them before final scenario tests. A similarity score is not a calibrated probability.

## Current limitations to measure

- One gallery embedding per enrolled person.
- No liveness or anti-spoof model; a photograph or screen replay may match a face.
- Face quality changes with distance, image resolution, lighting, pose, motion blur, caps and occlusion.
- Twins and lookalikes require separate, well-sampled enrollment and should be measured with wrong-identity rate as well as correct-match rate.
- Do not identify an unknown match as a threat. Show an identity-not-matched notice for review.

Keep recognition experiments in Python notebooks and report trial counts, thresholds, similarity distributions, false acceptance, false rejection, uncertain/unclear outcomes and presentation-attack acceptance.
