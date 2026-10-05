import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class _Entry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """Simple in-memory TTL cache. Not thread-safe; suitable for a single process."""

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, _Entry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.monotonic():
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._store[key] = _Entry(value=value, expires_at=time.monotonic() + self._ttl)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


async def get_or_set(
    cache: TTLCache[T],
    key: str,
    factory: Callable[[], Awaitable[T]],
) -> T:
    cached = cache.get(key)
    if cached is not None:
        return cached
    value = await factory()
    cache.set(key, value)
    return value
