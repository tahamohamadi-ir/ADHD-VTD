from __future__ import annotations

from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import (
    load_phase0_50q_cases,
    load_phase0_results,
    summarize_cases,
    write_json,
)
from src.evaluation.metrics import aggregate_basic_metrics
from src.evaluation.reliability_metrics import reliability_score

try:
    from src.config.paths import QUESTION_AUDIT_DIR
except Exception:  # pragma: no cover
    QUESTION_AUDIT_DIR = Path("data/questions/audit")


def build_phase0_summary(
    *, cases_path: str | Path | None = None, results_path: str | Path | None = None
) -> dict[str, Any]:
    cases_ds = load_phase0_50q_cases(cases_path)
    results = load_phase0_results(results_path)
    summary = {
        "cases": summarize_cases(cases_ds.cases),
        "execution_results_count": len(results),
        "gold_sql_executed_successfully": sum(1 for r in results if r.get("ok")),
        "gold_sql_failed": sum(1 for r in results if not r.get("ok")),
        "metrics": aggregate_basic_metrics(results),
        "reliability": reliability_score(results).as_dict(),
    }
    return summary


def write_phase0_summary_json(path: str | Path | None = None) -> Path:
    out = Path(path) if path else QUESTION_AUDIT_DIR / "phase0_evaluation_summary.json"
    return write_json(out, build_phase0_summary())


if __name__ == "__main__":
    out = write_phase0_summary_json()
    print(f"Phase 0 evaluation summary written to: {out}")
