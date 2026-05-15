from __future__ import annotations

from src.evaluation.metrics import add_bootstrap_cis, aggregate_basic_metrics, bootstrap_ci, latency_summary


def test_bootstrap_ci_is_bounded_and_deterministic():
    records = [
        {"ok": True, "execution_correct": True},
        {"ok": False, "execution_correct": False},
        {"ok": True, "execution_correct": True},
    ]

    metric = lambda rows: sum(1 for row in rows if row.get("ok")) / len(rows)
    ci1 = bootstrap_ci(records, metric, iterations=50, seed=7)
    ci2 = bootstrap_ci(records, metric, iterations=50, seed=7)

    assert ci1 == ci2
    assert 0.0 <= ci1["lower"] <= ci1["upper"] <= 1.0
    assert ci1["confidence"] == 0.95


def test_add_bootstrap_cis_adds_ci_to_core_metrics():
    records = [
        {"ok": True, "execution_correct": True, "valid_sql": True},
        {"ok": False, "execution_correct": False, "valid_sql": False},
    ]

    metrics = add_bootstrap_cis(aggregate_basic_metrics(records), records, iterations=20, seed=1)

    assert "ci95" in metrics["execution_accuracy"]
    assert "ci95" in metrics["valid_sql_rate"]


def test_latency_summary_reports_distribution():
    summary = latency_summary([
        {"latency_ms": 10},
        {"latency_ms": 20},
        {"latency_ms": 30},
    ])

    assert summary["count"] == 3
    assert summary["median_ms"] == 20
    assert summary["p95_ms"] == 30
