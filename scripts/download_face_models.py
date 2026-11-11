"""Download the two OpenCV Zoo face models required by this project."""

from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIRECTORY = PROJECT_ROOT / "models"

FACE_MODELS = {
    "face_detection_yunet_2023mar.onnx": {
        "url": (
            "https://media.githubusercontent.com/media/opencv/opencv_zoo/"
            "main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
        ),
        "sha256": "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    },
    "face_recognition_sface_2021dec.onnx": {
        "url": (
            "https://media.githubusercontent.com/media/opencv/opencv_zoo/"
            "main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
        ),
        "sha256": "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    },
}


def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest for a file without loading it all at once."""
    digest = sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(filename: str, source: dict[str, str]) -> Path:
    """Download one model and verify it before replacing the destination."""
    MODEL_DIRECTORY.mkdir(parents=True, exist_ok=True)
    destination = MODEL_DIRECTORY / filename

    if destination.is_file():
        if file_sha256(destination) == source["sha256"]:
            print(f"Already verified: {destination.name}")
            return destination
        raise ValueError(
            f"{destination} exists but does not match the expected SHA-256. "
            "Move the incorrect file away, then run this script again."
        )

    temporary_path = destination.with_suffix(destination.suffix + ".download")
    digest = sha256()

    try:
        with urlopen(source["url"], timeout=120) as response:
            with temporary_path.open("wb") as output_file:
                while chunk := response.read(1024 * 1024):
                    digest.update(chunk)
                    output_file.write(chunk)

        actual_sha256 = digest.hexdigest()
        if actual_sha256 != source["sha256"]:
            raise ValueError(
                f"Checksum mismatch for {filename}: {actual_sha256}"
            )

        temporary_path.replace(destination)
        print(f"Downloaded and verified: {destination.name}")
        return destination
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    """Download both face models and remind the team about the custom detector."""
    for filename, source in FACE_MODELS.items():
        download_model(filename, source)

    detector_path = MODEL_DIRECTORY / "best.pt"
    if detector_path.is_file():
        print("Found the local YOLO detector: best.pt")
    else:
        print(
            "Next, copy best.pt from the supplied project ZIP into the models "
            "folder. Its training data and distribution terms were not included "
            "in that ZIP, so this script does not download or redistribute it."
        )


if __name__ == "__main__":
    main()
