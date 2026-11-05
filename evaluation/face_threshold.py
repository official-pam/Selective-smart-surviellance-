"""Choose a face-match threshold from separate, labelled validation scores."""

import math


def choose_similarity_threshold(
    known_scores: list[float],
    unknown_scores: list[float],
    max_false_accept_rate: float = 0.01,
) -> dict[str, float | int]:
    """Choose the best known-person acceptance subject to a stranger limit.

    ``known_scores`` are cosine similarities for separate enrolled-person
    validation photos. ``unknown_scores`` are similarities for unenrolled
    people. A score at or above the chosen threshold is accepted as a match.

    Do not use final test scores to choose the threshold. Report the number of
    validation images and independently evaluate the chosen value afterward.
    """
    if not known_scores:
        raise ValueError("Provide at least one known-person validation score.")
    if not unknown_scores:
        raise ValueError("Provide at least one unenrolled-person validation score.")
    if not 0 <= max_false_accept_rate <= 1:
        raise ValueError("The maximum false-accept rate must be between 0 and 1.")
    for score in [*known_scores, *unknown_scores]:
        if not math.isfinite(score) or not -1 <= score <= 1:
            raise ValueError("Every cosine similarity must be finite and between -1 and 1.")

    # Between observed score values, the decisions do not change. Above 1.0
    # represents rejecting every sample, including a tie at a score of 1.0.
    candidates = sorted({*known_scores, *unknown_scores})
    eligible = []
    for threshold in candidates:
        false_accepts = sum(score >= threshold for score in unknown_scores)
        false_rejects = sum(score < threshold for score in known_scores)
        far = false_accepts / len(unknown_scores)
        frr = false_rejects / len(known_scores)
        if far <= max_false_accept_rate:
            eligible.append((frr, -threshold, threshold, far, frr))

    if not eligible:
        raise ValueError(
            "No threshold between -1 and 1 meets the requested false-accept limit. "
            "Add validation data or review the limit with the team."
        )

    _, _, threshold, far, frr = min(eligible)
    return {
        "threshold": threshold,
        "false_accept_rate": far,
        "false_reject_rate": frr,
        "known_validation_count": len(known_scores),
        "unknown_validation_count": len(unknown_scores),
        "maximum_false_accept_rate": max_false_accept_rate,
    }
