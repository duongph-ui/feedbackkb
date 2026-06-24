"""Rate limit + quota (§7.1, Step 10).

In-memory fixed-window limiter keyed by (ip, system, app_key). Production swaps
the backend for slowapi+Redis (env REDIS_URL) without changing call sites; the
window semantics are identical. `clock` is injectable for deterministic tests.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable


class RateLimiter:
    def __init__(self, limit: int, window_s: int, clock: Callable[[], float] | None = None):
        self.limit = limit
        self.window_s = window_s
        import time

        self._clock = clock or time.monotonic
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = self._clock()
        cutoff = now - self.window_s
        hits = [t for t in self._hits[key] if t >= cutoff]
        if len(hits) >= self.limit:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True

    @staticmethod
    def key(ip: str, system: str | None, app_key_prefix: str | None) -> str:
        return f"{ip}|{system or '-'}|{app_key_prefix or '-'}"
