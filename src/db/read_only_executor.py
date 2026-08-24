from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from src.db.sqlite_connection import get_readonly_connection
    from src.db.result_serializer import ResultSerializer
    from src.sql_validation.safety_validator import SQLSafetyValidator
except Exception:  # pragma: no cover
    from sqlite_connection import get_readonly_connection
    from result_serializer import ResultSerializer
    from safety_validator import SQLSafetyValidator


@dataclass(frozen=True)
class QueryExecutionResult:
    ok: bool
    sql: str
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    result_hash: str | None = None
    latency_ms: int = 0
    error: str | None = None


class ReadOnlyExecutor:
    def __init__(
        self, db_path: str | Path | None = None, timeout: float = 10.0, max_rows: int = 1000
    ) -> None:
        self.db_path = db_path
        self.timeout = timeout
        self.max_rows = max_rows
        self.safety = SQLSafetyValidator(require_limit_for_raw=False)

    def execute_readonly(
        self, sql: str, params: dict | tuple | None = None, max_rows: int | None = None
    ) -> QueryExecutionResult:
        started = time.perf_counter()
        validation = self.safety.validate(sql)
        if not validation.ok:
            return QueryExecutionResult(
                False, sql, error="; ".join(i.message for i in validation.issues)
            )

        limit = max_rows or self.max_rows
        try:
            with get_readonly_connection(self.db_path, timeout=self.timeout) as conn:
                cur = conn.execute(sql, params or {})
                rows_raw = cur.fetchmany(limit + 1)
                rows = [dict(row) for row in rows_raw[:limit]]
                serialized = ResultSerializer.serialize_rows(rows)
                latency = int((time.perf_counter() - started) * 1000)
                return QueryExecutionResult(
                    ok=True,
                    sql=sql,
                    columns=serialized.columns,
                    rows=serialized.rows,
                    row_count=serialized.row_count,
                    result_hash=serialized.result_hash,
                    latency_ms=latency,
                    error="row_limit_exceeded" if len(rows_raw) > limit else None,
                )
        except Exception as exc:
            latency = int((time.perf_counter() - started) * 1000)
            return QueryExecutionResult(False, sql, latency_ms=latency, error=str(exc))

    def execute_gold_sql(self, case: dict) -> QueryExecutionResult:
        sql = case.get("gold_sql") or case.get("sql") or case.get("expected_sql")
        if not sql:
            return QueryExecutionResult(
                False, "", error="Case does not contain gold_sql/sql/expected_sql."
            )
        return self.execute_readonly(sql)

    def compare_results(self, generated_sql: str, gold_sql: str) -> dict[str, Any]:
        gen = self.execute_readonly(generated_sql)
        gold = self.execute_readonly(gold_sql)
        return {
            "generated_ok": gen.ok,
            "gold_ok": gold.ok,
            "generated_hash": gen.result_hash,
            "gold_hash": gold.result_hash,
            "match": gen.ok and gold.ok and gen.result_hash == gold.result_hash,
            "generated_error": gen.error,
            "gold_error": gold.error,
        }

    def serialize_result_hash(self, rows: list[dict[str, Any]]) -> str:
        return ResultSerializer.result_hash(rows)
