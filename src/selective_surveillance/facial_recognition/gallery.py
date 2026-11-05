"""Enrollment and local storage for SFace reference embeddings."""

import json
from pathlib import Path
import numpy as np

from .config import PIPELINE_ID, DETECTOR_MODEL, RECOGNITION_MODEL


def validate_embedding(value):
    """Return a copy of a valid, normalized SFace embedding."""
    vector = np.asarray(value, dtype=np.float32)

    if (
        vector.shape != (128,)
        or not np.isfinite(vector).all()
        or not np.isclose(np.linalg.norm(vector), 1.0, atol=1e-4)
    ):
        raise ValueError("Expected a normalized 128-value embedding.")

    return vector.copy()


class FaceGallery:
    def __init__(self):
        # Each entry stores name fields and one reference embedding.
        self._people = {}

    def enroll(self, first_name, surname, embedding):
        """Add a person without overwriting an existing entry."""
        first_name = " ".join(first_name.split())
        surname = " ".join(surname.split())

        if not first_name or not surname:
            raise ValueError("Provide both first name and surname.")

        full_name = f"{first_name} {surname}"
        key = full_name.casefold()

        if key in self._people:
            raise ValueError(f"{full_name} is already enrolled.")

        self._people[key] = {
            "first_name": first_name,
            "surname": surname,
            "embedding": validate_embedding(embedding)
        }

        return full_name

    def references(self):
        """Return names and embedding copies for the matching module."""
        return {
            f"{person['first_name']} {person['surname']}":
                person["embedding"].copy()
            for person in self._people.values()
        }

    def save(self, filepath):
        """Save references with their model and pipeline identifiers."""
        records = []

        for person in self._people.values():
            records.append({
                "first_name": person["first_name"],
                "surname": person["surname"],
                "embedding": person["embedding"].tolist()
            })

        payload = {
            "schema_version": 2,
            "pipeline": PIPELINE_ID,
            "detector_model": DETECTOR_MODEL,
            "recognition_model": RECOGNITION_MODEL,
            "people": records
        }

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Replace the destination only after writing the complete file.
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def load(cls, filepath):
        """Validate the entire file before returning a restored gallery."""
        payload = json.loads(
            Path(filepath).read_text(encoding="utf-8")
        )

        expected = {
            "schema_version": 2,
            "pipeline": PIPELINE_ID,
            "detector_model": DETECTOR_MODEL,
            "recognition_model": RECOGNITION_MODEL
        }

        if not isinstance(payload, dict):
            raise ValueError("Invalid gallery file.")

        for field, value in expected.items():
            if payload.get(field) != value:
                raise ValueError(f"Incompatible gallery setting: {field}")

        records = payload.get("people")

        if not isinstance(records, list):
            raise ValueError("Expected a list of enrolled people.")

        restored = cls()

        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Invalid person record.")

            first_name = record.get("first_name")
            surname = record.get("surname")

            if not isinstance(first_name, str) or not isinstance(surname, str):
                raise ValueError("Invalid name fields.")

            # Reuse enrollment checks for names, duplicates and embeddings.
            restored.enroll(
                first_name,
                surname,
                record.get("embedding")
            )

        return restored
