# Model provenance and local setup

The project keeps model binaries out of Git. They are downloaded or copied into the ignored local `models/` folder.

| File | Purpose | Source and checksum | What is known |
|---|---|---|---|
| `face_detection_yunet_2023mar.onnx` | Detect and align faces | OpenCV Zoo YuNet; SHA-256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` | The Zoo describes YuNet as a lightweight face detector and provides its model notes and evaluation references in its [model README](https://github.com/opencv/opencv_zoo/blob/main/models/face_detection_yunet/README.md). The directory declares MIT licensing. |
| `face_recognition_sface_2021dec.onnx` | Produce face embeddings | OpenCV Zoo SFace; SHA-256 `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` | The Zoo describes the file as a MobileFaceNet instance trained with SFace loss and declares Apache 2.0 for the model directory in its [model README](https://github.com/opencv/opencv_zoo/blob/main/models/face_recognition_sface/README.md). |
| `best.pt` | Detect people in camera/video frames | Copied from the supplied `Selective Smart Surveillance System (2).zip`; SHA-256 `95ce01041799e2f21dcb99d1ef42a90497cca98d64cc594d7b442237ae720dec` | The ZIP did not include a model card, training dataset, training configuration, class map or redistribution terms. The team must add those details from the original trainer before claiming detector training provenance or redistributing these weights. |

Run `python scripts/download_face_models.py` to retrieve the two OpenCV Zoo face models. The script checks each file's SHA-256 before placing it in `models/`. Copy `best.pt` from the supplied ZIP into that folder separately.

The benchmark numbers reported in upstream model documentation are not results from this project's camera, laptop, lighting or participants. Use the scenario notebook to record our own measured trials. The repository currently has no liveness or presentation-attack detector; photo, screen and replay tests are observations of the current face-matching pipeline only.
