"""Hashing utilities for VTD pipeline.

Provides deterministic hashing for SQL normalization and result
comparison in benchmarks.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def sql_hash(sql: str) -> str:
    """Deterministic hash of a SQL string after whitespace normalization.

    Used to detect duplicate/identical SQL across retries.
    """
    normalized = re.sub(r"\s+", " ", (sql or "").strip().rstrip(";").strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def result_hash(rows: list[dict[str, Any]]) -> str:
    """Deterministic hash of query result rows.

    Rows are sorted by key, values are normalized (floats rounded),
    and the JSON representation is hashed.
    """
    normalized = [{str(k): _normalize_value(v) for k, v in sorted(row.items())} for row in rows]
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def text_hash(text: str) -> str:
    """Simple hash for arbitrary text content."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _normalize_value(value: Any) -> Any:
    """Normalize a single value for deterministic hashing."""
    if isinstance(value, float):
        return round(value, 8)
    return value
