from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import load_phase0_50q_cases, write_jsonl

try:
    from src.db.read_only_executor import ReadOnlyExecutor
except Exception as exc:  # pragma: no cover
    ReadOnlyExecutor = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

try:
    from src.config.paths import PHASE0_50Q_RESULTS_PATH
except Exception:  # pragma: no cover
    PHASE0_50Q_RESULTS_PATH = Path("data/questions/audit/phase0_50q_audit_results.jsonl")


@dataclass(slots=True)
class GoldSQLRunRecord:
    audit_id: str
    source_id: str | None
    question_fa: str
    difficulty: str
    category: str
    gold_sql: str | None
    ok: bool
    row_count: int = 0
    result_hash: str | None = None
    latency_ms: int | None = None
    error: str | None = None


def run_gold_case(case: dict[str, Any], executor: Any | None = None) -> GoldSQLRunRecord:
    if ReadOnlyExecutor is None and executor is None:
        raise RuntimeError(f"Could not import ReadOnlyExecutor: {_IMPORT_ERROR}")
    sql = case.get("gold_sql") or case.get("sql")
    audit_id = str(case.get("audit_id") or case.get("id") or case.get("source_id") or "unknown")
    if not sql:
        return GoldSQLRunRecord(
            audit_id=audit_id,
            source_id=case.get("source_id"),
            question_fa=case.get("question_fa") or case.get("question") or "",
            difficulty=str(case.get("difficulty", "unknown")),
            category=str(case.get("category", "unknown")),
            gold_sql=None,
            ok=False,
            error="No gold SQL present.",
        )

    ex = executor or ReadOnlyExecutor()
    result = ex.execute_readonly(sql)
    return GoldSQLRunRecord(
        audit_id=audit_id,
        source_id=case.get("source_id"),
        question_fa=case.get("question_fa") or case.get("question") or "",
        difficulty=str(case.get("difficulty", "unknown")),
        category=str(case.get("category", "unknown")),
        gold_sql=sql,
        ok=bool(getattr(result, "ok", False)),
        row_count=int(getattr(result, "row_count", 0) or 0),
        result_hash=getattr(result, "result_hash", None),
        latency_ms=getattr(result, "latency_ms", None),
        error=getattr(result, "error", None),
    )


def run_gold_cases(
    cases: list[dict[str, Any]] | None = None, *, output_path: str | Path | None = None
) -> list[dict[str, Any]]:
    ds_cases = cases if cases is not None else load_phase0_50q_cases().cases
    executor = ReadOnlyExecutor()
    rows = [asdict(run_gold_case(case, executor)) for case in ds_cases]
    write_jsonl(output_path or PHASE0_50Q_RESULTS_PATH, rows)
    return rows


if __name__ == "__main__":
    rows = run_gold_cases()
    ok = sum(1 for r in rows if r.get("ok"))
    print(f"Gold SQL executed successfully: {ok}/{len(rows)}")
    print(f"Results written to: {PHASE0_50Q_RESULTS_PATH}")
