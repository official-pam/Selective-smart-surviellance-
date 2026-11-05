# Facial recognition

**Owner: Emmanuel John.** The Python files in this package are the contribution supplied in `Emmanuel_John_Facial_Recognition.zip`, kept as a separate module. `face_processing.py` uses pretrained YuNet and SFace; `gallery.py` enrolls names and stores normalised references; `recognition.py` returns Known, Unknown or Uncertain.

Read the bundled package `README.md` before downloading the two model files. For the full project, install dependencies from the root `pyproject.toml`; the original `requirements.txt` is retained as the standalone requirements from the supplied ZIP. Store consenting reference photos and gallery JSON outside Git under `private_data/`.

## Integration tasks still required

- Add an adapter from `TrackedPerson.face_crop` and `track_id` to the recognition service and shared `RecognitionResult` contract.
- `adapter.py` is the first integration adapter; review its crop source and error policy with the detection/integration owners.
- Preserve `Face unclear` for missing, blurry, turned-away or multiple-face crops; do not reinterpret processing errors as Unknown.
- Use `evaluation/face_threshold.py` to choose a threshold on a separate known/unknown validation set, then freeze it before final testing. Review the permitted false-accept rate with the team.
- `integration/recognition_cache.py` caches Known/Unknown by track ID for a short interval. Integration must clear it when a track ends or resets and must recheck uncertain/unclear faces.
- Report correct rate, false rejection, wrong identity, false acceptance, unclear-face rate, and lighting/angle effects. Report counts and similarity scores; cosine similarity is not a probability.
