from __future__ import annotations

from src.evaluation.statistical_tests import bootstrap_ci, mcnemar_test


def test_bootstrap_ci_is_deterministic_with_seed():
    rows = [{"ok": True}, {"ok": False}, {"ok": True}, {"ok": False}]

    def metric(sample):
        return sum(1 for row in sample if row["ok"]) / len(sample)

    first = bootstrap_ci(rows, metric, iterations=100, seed=123)
    second = bootstrap_ci(rows, metric, iterations=100, seed=123)

    assert first == second
    assert first.confidence == 0.95
    assert first.iterations == 100
    assert 0.0 <= first.lower <= first.upper <= 1.0


def test_mcnemar_test_counts_paired_disagreements_by_case_id():
    baseline = [
        {"id": "a", "execution_correct": True},
        {"id": "b", "execution_correct": False},
        {"id": "c", "execution_correct": False},
        {"id": "d", "execution_correct": True},
    ]
    system = [
        {"id": "a", "execution_correct": True},
        {"id": "b", "execution_correct": True},
        {"id": "c", "execution_correct": False},
        {"id": "d", "execution_correct": False},
    ]

    result = mcnemar_test(baseline, system)

    assert result.compared_cases == 4
    assert result.both_correct == 1
    assert result.both_wrong == 1
    assert result.baseline_wrong_system_correct == 1
    assert result.baseline_correct_system_wrong == 1
    assert result.exact_p_value == 1.0


def test_mcnemar_test_warns_without_overlap():
    result = mcnemar_test(
        [{"id": "a", "execution_correct": True}],
        [{"id": "b", "execution_correct": True}],
    )

    assert result.compared_cases == 0
    assert result.warning
