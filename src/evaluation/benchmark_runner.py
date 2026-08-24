from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.evaluation.dataset_loader import load_phase0_50q_cases, write_json
from src.evaluation.metrics import aggregate_basic_metrics
from src.evaluation.reliability_metrics import reliability_score


PredictionFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(slots=True)
class BenchmarkRun:
    name: str
    total_cases: int
    records: list[dict[str, Any]]
    metrics: dict[str, Any]
    reliability: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "total_cases": self.total_cases,
            "records": self.records,
            "metrics": self.metrics,
            "reliability": self.reliability,
        }


def run_benchmark(
    cases: list[dict[str, Any]], predict: PredictionFn, *, name: str = "benchmark"
) -> BenchmarkRun:
    records: list[dict[str, Any]] = []
    for case in cases:
        pred = predict(case)
        records.append({**case, **pred})
    return BenchmarkRun(
        name=name,
        total_cases=len(cases),
        records=records,
        metrics=aggregate_basic_metrics(records),
        reliability=reliability_score(records).as_dict(),
    )


def run_phase0_identity_benchmark() -> BenchmarkRun:
    """A non-LLM sanity benchmark: treats gold SQL execution records as predictions.

    This is not a model benchmark. It verifies evaluation plumbing.
    """
    from src.evaluation.gold_sql_runner import run_gold_cases

    rows = run_gold_cases()

    def pred(case: dict[str, Any]) -> dict[str, Any]:
        match = next((r for r in rows if r.get("audit_id") == case.get("audit_id")), None)
        return {
            "actual_action": "generate_sql",
            "generated_sql": case.get("gold_sql"),
            "ok": bool(match and match.get("ok")),
            "execution_correct": bool(match and match.get("ok")),
            "result_hash": match.get("result_hash") if match else None,
            "error": match.get("error") if match else "missing_run_record",
        }

    return run_benchmark(load_phase0_50q_cases().cases, pred, name="phase0_identity_gold_sql")


def write_benchmark_run(run: BenchmarkRun, path: str | Path) -> Path:
    return write_json(path, run.as_dict())
