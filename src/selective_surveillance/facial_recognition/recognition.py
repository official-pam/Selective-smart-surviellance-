"""Face matching using normalized SFace embeddings."""

import math
import numpy as np

from .config import SIMILARITY_THRESHOLD, AMBIGUITY_MARGIN


class FaceRecognitionService:
    def __init__(
        self,
        processor,
        gallery,
        threshold=SIMILARITY_THRESHOLD,
        margin=AMBIGUITY_MARGIN
    ):
        # Validate the decision settings before processing images.
        if not math.isfinite(threshold) or not -1 <= threshold <= 1:
            raise ValueError("Threshold must be between -1 and 1.")

        if not math.isfinite(margin) or not 0 <= margin <= 2:
            raise ValueError("Margin must be between 0 and 2.")

        self.processor = processor
        self.gallery = gallery
        self.threshold = threshold
        self.margin = margin

    def recognize(self, image_bgr):
        """Return a structured identity decision for one face."""

        references = self.gallery.references()

        if not references:
            raise ValueError("Enroll at least one person first.")

        # Use the same preprocessing as enrollment.
        # Invalid or multiple-face inputs raise ValueError.
        query, _ = self.processor.extract(image_bgr)

        # Calculate cosine similarity against every reference.
        scores = {
            name: float(np.clip(np.dot(query, reference), -1.0, 1.0))
            for name, reference in references.items()
        }

        # Rank by similarity; use names to make tied ordering consistent.
        ranked = sorted(
            scores.items(),
            key=lambda item: (-item[1], item[0])
        )

        candidate, best_score = ranked[0]

        # A second-best score exists only with multiple enrolled people.
        second_score = ranked[1][1] if len(ranked) > 1 else None
        gap = (
            best_score - second_score
            if second_score is not None
            else None
        )

        if best_score < self.threshold:
            status = "Unknown"
            name = None
            reason = "No reference passed the similarity threshold."

        elif gap is not None and gap < self.margin:
            status = "Uncertain"
            name = None
            reason = "The two best identity scores are too close."

        else:
            status = "Known"
            name = candidate
            reason = "Match passed the current decision rules."

        # A candidate is only the closest reference, not an accepted identity.
        return {
            "status": status,
            "name": name,
            "candidate": candidate,
            "similarity": best_score,
            "threshold": self.threshold,
            "score_gap": gap,
            "required_margin": self.margin,
            "reason": reason,
            "scores": scores
        }
