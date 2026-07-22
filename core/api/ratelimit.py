"""Simple in-memory sliding-window rate limiter, keyed by client (e.g. IP).

Per-process and best-effort: fine for a single-worker demo, but back it with a
shared store (Redis) before running multiple workers, since each process would
otherwise keep its own independent window.
"""

import time


class SlidingWindowLimiter:
    def __init__(self, max_events: int, window_seconds: float):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}

    def check_and_record(self, key: str, now: float | None = None) -> bool:
        """Return True if the event is allowed (and record it), False if over the
        limit. A `max_events` of 0 (or less) disables the limit entirely."""
        if self.max_events <= 0:
            return True
        now = time.time() if now is None else now
        cutoff = now - self.window_seconds
        hits = [t for t in self._hits.get(key, []) if t > cutoff]
        if len(hits) >= self.max_events:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True

    def remaining(self, key: str, now: float | None = None) -> int:
        """How many more events `key` may record in the current window."""
        if self.max_events <= 0:
            return -1  # unlimited
        now = time.time() if now is None else now
        cutoff = now - self.window_seconds
        used = len([t for t in self._hits.get(key, []) if t > cutoff])
        return max(0, self.max_events - used)
