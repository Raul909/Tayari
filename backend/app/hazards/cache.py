"""
The in-memory TTL cache the hazard feeds share.

Tayari runs on a free tier: one small container, no Redis, and a process that is
recycled at least daily. That rules out anything clever and makes two properties
matter — entries must expire on a schedule matched to how fast the underlying
truth moves, and the cache must not grow without bound, because its keys are
geographic and therefore unbounded in principle.
"""

import time
from typing import Any, Optional


class TTLCache:
    """Time-limited cache with a hard entry cap and oldest-first eviction."""

    __slots__ = ("ttl", "max_entries", "_data")

    def __init__(self, ttl_seconds: float, max_entries: int = 512):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._data: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        hit = self._data.get(key)
        if hit is None:
            return None
        stored_at, value = hit
        if time.time() - stored_at > self.ttl:
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if key not in self._data and len(self._data) >= self.max_entries:
            oldest = min(self._data, key=lambda k: self._data[k][0])
            self._data.pop(oldest, None)
        self._data[key] = (time.time(), value)

    def __len__(self) -> int:
        return len(self._data)


def geo_key(latitude: float, longitude: float, precision: int = 2) -> str:
    """
    Cache key for a coordinate, rounded to control the hit rate.

    Precision is a deliberate lever per feed rather than one global constant.
    Two decimals (~1 km) is right for weather; one (~11 km) is right for
    climatology and seismic history, where a finer key would just multiply
    identical upstream calls for answers that do not vary at that scale.
    """
    return f"{round(latitude, precision)},{round(longitude, precision)}"
