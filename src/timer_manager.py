import time
from datetime import datetime
from loguru import logger


class TimerManager:
    def __init__(self, threshold_seconds: float = 30.0):
        self.threshold     = threshold_seconds
        self._start_times: dict[int, float] = {}
        self._entry_times: dict[int, str]   = {}
        self._alerted:     set[int]         = set()
        self._last_seen:   dict[int, float] = {}
        self._active:      set[int]         = set()
        self.GRACE_PERIOD  = 1.5
        self.on_exit       = None

    def update(self, active_track_ids: list[int], current_time=None) -> list[tuple]:
        current_time    = time.time() if current_time is None else current_time
        newly_triggered = []

        # ── Register new + update last seen ─────────────
        for tid in active_track_ids:
            if tid not in self._start_times:
                self._start_times[tid] = current_time
                self._entry_times[tid] = datetime.fromtimestamp(current_time).strftime("%H:%M:%S")
                logger.info(f"🟢 ID:{tid} fresh timer started at {self._entry_times[tid]}")
            self._last_seen[tid] = current_time

        # ── Check threshold ──────────────────────────────
        for tid in active_track_ids:
            elapsed = current_time - self._start_times[tid]
            if elapsed >= self.threshold and tid not in self._alerted:
                self._alerted.add(tid)
                newly_triggered.append((tid, round(elapsed, 1)))
                logger.success(f"🚨 ID:{tid} — {elapsed:.1f}s — ALERT!")

        # ── Check ALL known IDs for vanishing ───────────
        # Check every known ID — not just active ones
        for tid in list(self._start_times.keys()):
            if tid not in active_track_ids:
                gone_for = current_time - self._last_seen.get(tid, current_time)
                if gone_for > self.GRACE_PERIOD:
                    entry_ts  = self._start_times[tid]
                    exit_ts   = self._last_seen.get(tid, current_time)
                    duration  = round(exit_ts - entry_ts, 1)
                    entry_str = self._entry_times.get(tid, "Unknown")
                    exit_str  = datetime.fromtimestamp(exit_ts).strftime("%H:%M:%S")
                    alerted   = tid in self._alerted

                    logger.info(
                        f"🔴 ID:{tid} left | "
                        f"In:{entry_str} Out:{exit_str} "
                        f"Duration:{duration}s"
                    )

                    # Fire exit callback
                    if self.on_exit:
                        try:
                            self.on_exit(
                                track_id   = tid,
                                entry_time = entry_str,
                                exit_time  = exit_str,
                                duration   = duration,
                                alerted    = alerted
                            )
                        except Exception as e:
                            logger.error(f"on_exit error: {e}")

                    # Clean up
                    self._start_times.pop(tid, None)
                    self._entry_times.pop(tid, None)
                    self._last_seen.pop(tid, None)
                    self._alerted.discard(tid)

        # Update active set
        self._active = set(active_track_ids)
        return newly_triggered

    def get_elapsed(self, current_time=None) -> dict[int, float]:
        now = time.time() if current_time is None else current_time
        return {
            tid: now - self._start_times[tid]
            for tid in self._active
            if tid in self._start_times
        }

    def get_entry_time(self, tid: int) -> str:
        return self._entry_times.get(tid, "Unknown")