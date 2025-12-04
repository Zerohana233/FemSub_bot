from __future__ import annotations

import time
from typing import Dict, Generic, Optional, TypeVar

T = TypeVar("T")


class TimedStateStore(Generic[T]):
    """简单的 TTL 状态存储，避免内存状态无限增长。"""

    def __init__(self, ttl_seconds: int = 600):
        self.ttl = ttl_seconds
        self._store: Dict[int, tuple[float, T]] = {}

    def set(self, key: int, value: T):
        self._store[key] = (time.time(), value)
        self._cleanup_expired()

    def get(self, key: int) -> Optional[T]:
        entry = self._store.get(key)
        if not entry:
            return None
        created_at, value = entry
        if time.time() - created_at > self.ttl:
            self._store.pop(key, None)
            return None
        return value

    def pop(self, key: int) -> Optional[T]:
        entry = self._store.pop(key, None)
        if not entry:
            return None
        created_at, value = entry
        if time.time() - created_at > self.ttl:
            return None
        return value

    def delete(self, key: int):
        self._store.pop(key, None)

    def __contains__(self, key: int) -> bool:
        return self.get(key) is not None

    def _cleanup_expired(self):
        now = time.time()
        expired_keys = [key for key, (created_at, _) in self._store.items() if now - created_at > self.ttl]
        for key in expired_keys:
            self._store.pop(key, None)

