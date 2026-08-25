from __future__ import annotations

import time
from pathlib import Path

RATE_METRIC_KEYS = ("execution_accuracy", "conservative_execution_accuracy", "valid_sql_rate")
METRIC_ENTRY_KEYS = {"name", "value", "numerator", "denominator", "description"}


def test_gold_minibench_llm_free_computes_valid_metrics(monkeypatch):
    project_root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(project_root / "scripts"))

    import run_benchmark  # type: ignore
    from src.db.read_only_executor import ReadOnlyExecutor
    from src.evaluation.dataset_loader import load_dataset
    from src.evaluation.metrics import add_bootstrap_cis, aggregate_basic_metrics

    dataset = load_dataset(run_benchmark.DATASET_ALIASES["dev"], kind="dev")
    cases = dataset.cases[:3]
    assert 1 <= len(cases) <= 3
    assert all(case.get("gold_sql") or case.get("sql") for case in cases)

    executor = ReadOnlyExecutor()
    records = []
    started_total = time.perf_counter()
    for case in cases:
        started = time.perf_counter()
        prediction = run_benchmark.gold_prediction(case, executor)
        record = dict(case, **prediction)
        record.setdefault("latency_ms", int((time.perf_counter() - started) * 1000))
        records.append(record)

    assert len(records) == len(cases)
    assert all(record["actual_action"] == "generate_sql" for record in records)
    assert all(record["generated_sql"] for record in records)
    assert all(record["ok"] and record["execution_correct"] for record in records)
    assert all(record["valid_sql"] is True for record in records)
    assert all(record["error"] is None for record in records)
    assert all(record["mode"] == "gold" for record in records)
    assert all(record["latency_ms"] >= 0 for record in records)

    metrics = aggregate_basic_metrics(records)
    assert metrics["execution_accuracy"]["numerator"] == len(records)
    assert metrics["execution_accuracy"]["denominator"] == len(records)
    for entry in metrics.values():
        assert METRIC_ENTRY_KEYS <= set(entry)
        assert entry["value"] >= 0
        if entry["name"] in RATE_METRIC_KEYS:
            assert 0.0 <= entry["value"] <= 1.0

    metrics_with_ci = add_bootstrap_cis(metrics, records, iterations=10, seed=42)
    ci = metrics_with_ci["execution_accuracy"]["ci95"]
    assert 0.0 <= ci["lower"] <= ci["upper"] <= 1.0
    assert time.perf_counter() - started_total < 10.0
