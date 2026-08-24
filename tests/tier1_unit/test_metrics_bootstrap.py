from __future__ import annotations

from src.evaluation.metrics import (
    add_bootstrap_cis,
    aggregate_basic_metrics,
    bootstrap_ci,
    latency_summary,
)


def test_bootstrap_ci_is_bounded_and_deterministic():
    records = [
        {"ok": True, "execution_correct": True},
        {"ok": False, "execution_correct": False},
        {"ok": True, "execution_correct": True},
    ]

    def metric(rows):
        return sum(1 for row in rows if row.get("ok")) / len(rows)

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
    assert "ci95" in metrics["expected_action_accuracy"]


def test_sql_metrics_exclude_behavior_only_records():
    records = [
        {
            "expected_action": "ask_clarification",
            "should_generate_sql": False,
            "ok": True,
            "execution_correct": False,
            "valid_sql": True,
        },
        {
            "expected_action": "generate_sql",
            "should_generate_sql": True,
            "ok": False,
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "execution_correct": True,
            "valid_sql": True,
        },
    ]

    metrics = aggregate_basic_metrics(records)

    assert metrics["execution_accuracy"]["numerator"] == 1
    assert metrics["execution_accuracy"]["denominator"] == 1
    assert metrics["valid_sql_rate"]["numerator"] == 1
    assert metrics["valid_sql_rate"]["denominator"] == 1


def test_sql_metrics_report_strict_and_conservative_denominators_separately():
    records = [
        {
            "expected_action": "generate_sql",
            "should_generate_sql": True,
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "valid_sql": True,
            "execution_correct": True,
        },
        {
            "expected_action": "generate_sql",
            "should_generate_sql": True,
            "generated_sql": "SELECT gender, COUNT(*) AS n FROM student_depression GROUP BY gender",
            "valid_sql": True,
            "execution_correct": False,
            "error": "RESULT_MISMATCH",
        },
        {
            "expected_action": "generate_sql",
            "should_generate_sql": True,
            "generated_sql": None,
            "valid_sql": False,
            "execution_correct": False,
            "error": "MISSING_GENERATED_SQL",
        },
        {
            "expected_action": "ask_clarification",
            "should_generate_sql": False,
            "actual_action": "ask_clarification",
            "generated_sql": None,
        },
    ]

    metrics = aggregate_basic_metrics(records)

    assert metrics["execution_accuracy"]["numerator"] == 1
    assert metrics["execution_accuracy"]["denominator"] == 2
    assert metrics["conservative_execution_accuracy"]["numerator"] == 1
    assert metrics["conservative_execution_accuracy"]["denominator"] == 3
    assert metrics["valid_sql_rate"]["numerator"] == 2
    assert metrics["valid_sql_rate"]["denominator"] == 2
    assert metrics["attempted_sql_count"]["numerator"] == 2
    assert metrics["attempted_sql_count"]["denominator"] == 3
    assert metrics["missing_sql_count"]["numerator"] == 1
    assert metrics["missing_sql_count"]["denominator"] == 3
    assert metrics["result_mismatch_count"]["numerator"] == 1
    assert metrics["result_mismatch_count"]["denominator"] == 2


def test_unsafe_sql_and_semantic_judge_metrics_are_separate():
    metrics = aggregate_basic_metrics(
        [
            {
                "expected_action": "generate_sql",
                "should_generate_sql": True,
                "generated_sql": "DROP TABLE student_depression",
                "valid_sql": False,
                "semantic_business_correct": False,
                "validation_errors": [{"code": "FORBIDDEN_KEYWORD"}],
            },
            {
                "expected_action": "generate_sql",
                "should_generate_sql": True,
                "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
                "valid_sql": True,
                "execution_correct": True,
                "semantic_business_correct": True,
            },
            {
                "expected_action": "ask_clarification",
                "should_generate_sql": False,
                "actual_action": "ask_clarification",
                "generated_sql": None,
            },
        ]
    )

    assert metrics["unsafe_sql_count"]["numerator"] == 1
    assert metrics["unsafe_sql_count"]["denominator"] == 3
    assert metrics["semantic_business_accuracy"]["numerator"] == 1
    assert metrics["semantic_business_accuracy"]["denominator"] == 2
    assert metrics["execution_accuracy"]["denominator"] == 2


def test_expected_action_accuracy_is_separate_from_execution_correctness():
    records = [
        {
            "expected_action": "generate_sql",
            "should_generate_sql": True,
            "actual_action": "format_answer",
            "generated_sql": "SELECT 1",
            "execution_correct": False,
        },
        {
            "expected_action": "ask_clarification",
            "should_generate_sql": False,
            "actual_action": "fail_gracefully",
            "generated_sql": None,
            "execution_correct": False,
        },
    ]

    metrics = aggregate_basic_metrics(records)

    assert metrics["expected_action_accuracy"]["numerator"] == 1
    assert metrics["expected_action_accuracy"]["denominator"] == 2
    assert metrics["execution_accuracy"]["numerator"] == 0


def test_behavioral_privacy_refusal_alias_counts_as_safety_rejection():
    metrics = aggregate_basic_metrics(
        [
            {
                "expected_action": "refuse_privacy",
                "should_generate_sql": False,
                "actual_action": "refuse_unsafe_sql",
                "safety_label": "privacy_risk",
            }
        ]
    )

    assert metrics["execution_accuracy"]["denominator"] == 0
    assert metrics["safety_rejection_accuracy"]["numerator"] == 1
    assert metrics["safety_rejection_accuracy"]["denominator"] == 1


def test_latency_summary_reports_distribution():
    summary = latency_summary(
        [
            {"latency_ms": 10},
            {"latency_ms": 20},
            {"latency_ms": 30},
        ]
    )

    assert summary["count"] == 3
    assert summary["median_ms"] == 20
    assert summary["p95_ms"] == 30
