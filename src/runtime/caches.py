from __future__ import annotations

import hashlib
import re
import threading
import time
from collections import OrderedDict
from typing import Any


def normalize_key(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip()).lower()


class _TTLLRU:
    def __init__(self, max_size: int = 256, ttl_seconds: float = 600.0) -> None:
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _now() -> float:
        return time.monotonic()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            stored_at, value = entry
            if self._now() - stored_at > self._ttl:
                del self._store[key]
                self._misses += 1
                return None
            self._store.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (self._now(), value)
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"hits": self._hits, "misses": self._misses, "size": len(self._store)}


class QuestionCache(_TTLLRU):
    pass


class SQLResultCache(_TTLLRU):
    @staticmethod
    def sql_key(sql_text: str) -> str:
        normalized = re.sub(r"\s+", " ", sql_text.strip()).lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get_by_sql(self, sql_text: str) -> Any | None:
        return self.get(self.sql_key(sql_text))

    def set_by_sql(self, sql_text: str, value: Any) -> None:
        self.set(self.sql_key(sql_text), value)
