# Face enrolment and recognition

**Owner: Emmanuel John.** This folder contains the supplied Python face-recognition module: YuNet detects and aligns faces, SFace creates normalized embeddings, the gallery stores enrolled references, and the matcher returns Known, Unknown or Uncertain.

The live controller in `integration/controller.py` calls this module when a tracked person enters the restricted zone. The controller currently checks the entry frame once; later-frame retries for unclear faces and the existing track cache are still to be integrated.

## Model files

Place these local model files in the ignored project-level `models/` directory:

- `face_detection_yunet_2023mar.onnx`
- `face_recognition_sface_2021dec.onnx`

The controller loads both files from `models/`. Do not commit model files or enrolled face images.

## Enrollment and matching

`FaceGallery` currently stores one normalized 128-value reference embedding for each full name. It prevents duplicate names, saves the gallery as JSON, and checks model/pipeline identifiers when loading. The gallery belongs under `private_data/face_gallery.json`.

The current gallery is not yet a multi-image profile and does not perform a documented augmentation sequence. Before extending enrollment, compare multiple consenting captures under normal and difficult conditions. If synthetic augmentation is tried, keep those samples grouped with the original person and do not count them as independent test participants.

The similarity threshold and ambiguity margin in `config.py` are provisional. Joseph's independent validation set should be used to choose them, then freeze them before final scenario tests. A similarity score is not a calibrated probability.

## Current limitations to measure

- One gallery embedding per enrolled person.
- No liveness or anti-spoof model; a photograph or screen replay may match a face.
- Face quality changes with distance, image resolution, lighting, pose, motion blur, caps and occlusion.
- Twins and lookalikes require separate, well-sampled enrollment and should be measured with wrong-identity rate as well as correct-match rate.
- Do not identify an unknown match as a threat. Show an identity-not-matched notice for review.

Keep recognition experiments in Python notebooks and report trial counts, thresholds, similarity distributions, false acceptance, false rejection, uncertain/unclear outcomes and presentation-attack acceptance.
