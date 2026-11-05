"""Short-lived face-decision cache keyed by persistent person tracking ID."""

from dataclasses import replace

from selective_surveillance.contracts import RecognitionResult, RecognitionStatus


class RecognitionCache:
    """Reuse only recent Known/Unknown decisions for a still-active track.

    Pass ``time.monotonic()`` as ``now`` from the video loop. Uncertain,
    face-unclear and error results are returned to the caller but never cached.
    Call ``remove_ended_tracks`` when ByteTrack says tracks have disappeared.
    """

    _cacheable_statuses = {RecognitionStatus.KNOWN, RecognitionStatus.UNKNOWN}

    def __init__(self, ttl_seconds: float = 3.0) -> None:
        if ttl_seconds <= 0:
            raise ValueError("Cache lifetime must be greater than zero.")
        self._ttl_seconds = ttl_seconds
        self._entries: dict[int, tuple[float, RecognitionResult]] = {}

    def get(self, track_id: int, now: float) -> RecognitionResult | None:
        """Return a marked cached result, or None when the track needs checking."""
        entry = self._entries.get(track_id)
        if entry is None:
            return None
        saved_at, result = entry
        if now < saved_at or now - saved_at >= self._ttl_seconds:
            self._entries.pop(track_id, None)
            return None
        return replace(result, cached=True)

    def put(self, result: RecognitionResult, now: float) -> None:
        """Cache a final Known/Unknown result; leave uncertain cases uncached."""
        if result.status in self._cacheable_statuses:
            self._entries[result.track_id] = (now, replace(result, cached=False))

    def remove(self, track_id: int) -> None:
        """Forget a track as soon as it ends or ByteTrack resets."""
        self._entries.pop(track_id, None)

    def remove_ended_tracks(self, active_track_ids: set[int]) -> None:
        """Remove cached identities for all tracks absent from the current set."""
        for track_id in set(self._entries) - active_track_ids:
            self._entries.pop(track_id, None)

    def clear(self) -> None:
        """Clear all cached decisions after a camera or tracker reset."""
        self._entries.clear()
