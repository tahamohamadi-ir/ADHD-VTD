from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class SerializedResult:
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    result_hash: str

class ResultSerializer:
    @staticmethod
    def normalize_value(value: Any) -> Any:
        if isinstance(value, float):
            return round(value, 8)
        return value

    @classmethod
    def serialize_rows(cls, rows: list[dict[str, Any]]) -> SerializedResult:
        normalized_rows = [
            {str(k): cls.normalize_value(v) for k, v in sorted(row.items(), key=lambda x: x[0])}
            for row in rows
        ]
        columns = sorted(normalized_rows[0].keys()) if normalized_rows else []
        payload = json.dumps(normalized_rows, ensure_ascii=False, sort_keys=True, default=str)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return SerializedResult(columns, normalized_rows, len(normalized_rows), digest)

    @classmethod
    def result_hash(cls, rows: list[dict[str, Any]]) -> str:
        return cls.serialize_rows(rows).result_hash
