from __future__ import annotations

import sys
from pathlib import Path

from src.evaluation.reliability_gate import (
    ReliabilityGatePolicy,
    evaluate_reliability_gate,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from scripts.run_benchmark import agent_prediction


class _FakeWorkflow:
    def invoke(self, _state):
        return {
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "validation_errors": [],
            "execution_result": [{"n": 10}],
            "execution_error": None,
            "final_answer": "ØªØ­Ù„ÛŒÙ„ Ø§Ù†Ø¬Ø§Ù… Ø´Ø¯.",
            "intent": "count_query",
            "intent_confidence": 0.9,
            "retry_count": 0,
            "max_retries": 3,
            "needs_clarification": False,
            "safety_label": "safe",
            "attempts": [],
            "candidate_sqls": [
                {
                    "candidate_id": "primary",
                    "sql": "SELECT COUNT(*) AS n FROM student_depression",
                    "valid_sql": True,
                    "execution_passed": True,
                    "result_hash": "generated-hash",
                }
            ],
            "selected_candidate_id": "primary",
            "candidate_consistency": {"passed": True, "issues": []},
            "multi_candidate_policy": {"enabled": False, "candidate_count": 1},
        }


class _FakeExecutor:
    def compare_results(self, _generated_sql, _gold_sql):
        return {
            "match": True,
            "generated_hash": "generated-hash",
            "gold_hash": "gold-hash",
            "generated_ok": True,
            "gold_ok": True,
        }


def test_reliability_gate_refuses_unsafe_request():
    decision = evaluate_reliability_gate(
        {
            "intent": "unsafe_query",
            "safety_label": "unsafe_sql",
            "generated_sql": "SELECT 1",
            "execution_result": [{"x": 1}],
        }
    )

    assert decision.action == "refuse_unsafe"
    assert decision.reason == "unsafe_request"


def test_reliability_gate_asks_clarification_on_low_confidence():
    decision = evaluate_reliability_gate(
        {
            "intent": "unknown",
            "intent_confidence": 0.2,
            "should_generate_sql": True,
        },
        policy=ReliabilityGatePolicy(min_intent_confidence=0.4),
    )

    assert decision.action == "ask_clarification"
    assert decision.reason == "low_intent_confidence"


def test_reliability_gate_retries_retryable_validation_failure():
    decision = evaluate_reliability_gate(
        {
            "generated_sql": "SELECT bad_column FROM table_name",
            "validation_issues": [{"message": "unknown column"}],
            "retry_count": 1,
            "max_retries": 3,
        }
    )

    assert decision.action == "retry"
    assert decision.reason == "validation_failed_retryable"


def test_reliability_gate_needs_review_after_validation_retries_exhausted():
    decision = evaluate_reliability_gate(
        {
            "generated_sql": "SELECT bad_column FROM table_name",
            "validation_errors": [{"message": "unknown column"}],
            "retry_count": 3,
            "max_retries": 3,
        }
    )

    assert decision.action == "needs_review"
    assert decision.reason == "validation_failed_exhausted"


def test_reliability_gate_answers_with_warning_for_semantic_correct_strict_mismatch():
    decision = evaluate_reliability_gate(
        {
            "generated_sql": "SELECT group_value, rate_pct FROM rates",
            "valid_sql": True,
            "execution_result": [{"group_value": "7-8", "rate_pct": 12.5}],
            "semantic_policy_label": "correct",
            "strict_policy_label": "incorrect",
            "combined_label": "semantic_correct_strict_incorrect",
        }
    )

    assert decision.action == "answer"
    assert decision.reason == "semantic_correct_with_strict_reference_mismatch"
    assert decision.warnings == ["strict_reference_mismatch"]


def test_reliability_gate_does_not_convert_unjudged_partial_to_answer():
    decision = evaluate_reliability_gate(
        {
            "generated_sql": "SELECT group_value, rate_pct FROM rates",
            "valid_sql": True,
            "execution_result": [{"group_value": "7-8", "rate_pct": 12.5}],
            "semantic_policy_label": "partial_business_match",
            "strict_policy_label": "incorrect",
        }
    )

    assert decision.action == "needs_review"
    assert decision.reason == "semantic_judge_unresolved"


def test_reliability_gate_reviews_empty_execution_result_by_default():
    decision = evaluate_reliability_gate(
        {
            "generated_sql": "SELECT * FROM student_depression WHERE age > 999",
            "valid_sql": True,
            "execution_result": [],
        }
    )

    assert decision.action == "needs_review"
    assert decision.reason == "empty_execution_result"


def test_reliability_gate_answers_valid_nonempty_execution_without_gold_signals():
    decision = evaluate_reliability_gate(
        {
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "valid_sql": True,
            "execution_result": [{"n": 10}],
        }
    )

    assert decision.action == "answer"
    assert decision.reason == "validated_executed_sql"
    assert "execution_correct" not in decision.signals


def test_reliability_gate_ignores_benchmark_only_gold_and_case_labels():
    decision = evaluate_reliability_gate(
        {
            "case_id": "VTD-343",
            "gold_sql": "SELECT different_reference_shape FROM hidden_gold",
            "execution_correct": False,
            "result_match": False,
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "valid_sql": True,
            "execution_result": [{"n": 10}],
        }
    )

    assert decision.action == "answer"
    assert decision.reason == "validated_executed_sql"
    assert "case_id" not in decision.signals
    assert "gold_sql" not in decision.signals
    assert "execution_correct" not in decision.signals
    assert "result_match" not in decision.signals


def test_reliability_gate_reviews_consistency_failure_after_retries_exhausted():
    decision = evaluate_reliability_gate(
        {
            "question": "Show quartiles of change in eating disorder prevalence since 1990.",
            "generated_sql": "SELECT AVG(prevalence_pct) FROM country_prevalence_long",
            "valid_sql": True,
            "execution_result": [{"avg": 2.1}],
            "retry_count": 3,
            "max_retries": 3,
        }
    )

    assert decision.action == "needs_review"
    assert decision.reason == "consistency_failed_exhausted"
    assert decision.signals["consistency_issue_count"] == 2


def test_reliability_gate_retries_consistency_failure_before_retry_limit():
    decision = evaluate_reliability_gate(
        {
            "question": "What is the depression rate by sleep category?",
            "generated_sql": "SELECT sleep_duration_category, COUNT(*) AS n FROM student_depression GROUP BY sleep_duration_category",
            "valid_sql": True,
            "execution_result": [{"sleep_duration_category": "7-8", "n": 10}],
            "retry_count": 0,
            "max_retries": 3,
        }
    )

    assert decision.action == "retry"
    assert decision.reason == "consistency_failed_retryable"


def test_reliability_gate_can_review_consistency_failure_without_retry_loop():
    decision = evaluate_reliability_gate(
        {
            "question": "What is the depression rate by sleep category?",
            "generated_sql": "SELECT sleep_duration_category, COUNT(*) AS n FROM student_depression GROUP BY sleep_duration_category",
            "valid_sql": True,
            "execution_result": [{"sleep_duration_category": "7-8", "n": 10}],
            "retry_count": 0,
            "max_retries": 3,
            "reliability_gate_review_consistency_failures": True,
        }
    )

    assert decision.action == "needs_review"
    assert decision.reason == "consistency_failed_review"
    assert decision.signals["reliability_gate_review_consistency_failures"] is True


def test_reliability_gate_reviews_risk_profile_missing_context_averages_after_retries_exhausted():
    decision = evaluate_reliability_gate(
        {
            "question": "Show risks for people with stress above average and sleep below average.",
            "generated_sql": "SELECT mental_health_risk, COUNT(*) AS n "
            "FROM mental_health_general "
            "WHERE stress_level > (SELECT AVG(stress_level) FROM mental_health_general) "
            "AND sleep_hours < (SELECT AVG(sleep_hours) FROM mental_health_general) "
            "GROUP BY mental_health_risk",
            "valid_sql": True,
            "execution_result": [{"mental_health_risk": "High", "n": 10}],
            "retry_count": 3,
            "max_retries": 3,
        }
    )

    assert decision.action == "needs_review"
    assert decision.reason == "consistency_failed_exhausted"
    assert any(
        issue["code"] == "QUESTION_SQL_MISSING_RISK_CONTEXT_AVERAGES"
        for issue in decision.signals["consistency_issues"]
    )


def test_reliability_gate_reviews_comparative_single_group_filter_after_retries_exhausted():
    decision = evaluate_reliability_gate(
        {
            "question": "Do high risk people seek treatment more?",
            "generated_sql": "SELECT AVG(seeks_treatment) * 100.0 "
            "FROM mental_health_general WHERE mental_health_risk = 'High'",
            "valid_sql": True,
            "execution_result": [{"treatment_rate": 42.0}],
            "retry_count": 3,
            "max_retries": 3,
        }
    )

    assert decision.action == "needs_review"
    assert decision.reason == "consistency_failed_exhausted"
    assert any(
        issue["code"] == "QUESTION_SQL_MISSING_COMPARISON_BASELINE"
        for issue in decision.signals["consistency_issues"]
    )


def test_reliability_gate_reviews_candidate_disagreement_after_retries_exhausted():
    decision = evaluate_reliability_gate(
        {
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "valid_sql": True,
            "execution_result": [{"n": 10}],
            "retry_count": 3,
            "max_retries": 3,
            "candidate_consistency": {
                "passed": False,
                "issues": [
                    {
                        "code": "CANDIDATE_RESULT_HASH_DISAGREEMENT",
                        "message": "candidate result hashes differ",
                        "severity": "error",
                    }
                ],
            },
        }
    )

    assert decision.action == "needs_review"
    assert decision.reason == "candidate_consistency_failed_exhausted"
    assert decision.signals["candidate_consistency_issue_count"] == 1


def test_reliability_gate_ignores_candidate_consistency_warnings_for_answer():
    decision = evaluate_reliability_gate(
        {
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "valid_sql": True,
            "execution_result": [{"n": 10}],
            "candidate_consistency": {
                "passed": True,
                "issues": [
                    {
                        "code": "SINGLE_VIABLE_CANDIDATE",
                        "message": "single candidate",
                        "severity": "warning",
                    }
                ],
            },
        }
    )

    assert decision.action == "answer"
    assert decision.reason == "validated_executed_sql"


def test_reliability_gate_reviews_when_multicandidate_was_triggered_but_no_evidence_available():
    decision = evaluate_reliability_gate(
        {
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "valid_sql": True,
            "execution_result": [{"n": 10}],
            "multi_candidate_policy": {
                "enabled": True,
                "candidate_count": 2,
                "triggers": ["retry_in_progress", "validation_failed"],
            },
            "multi_candidate_generation_enabled": True,
            "candidate_sqls": [],
            "candidate_consistency": None,
        }
    )

    assert decision.action == "needs_review"
    assert decision.reason == "candidate_evidence_missing_after_trigger"
    assert decision.warnings == ["multi_candidate_evidence_unavailable"]
    assert decision.signals["candidate_evidence_missing_after_trigger"] is True


def test_reliability_gate_does_not_require_candidate_evidence_when_policy_is_disabled():
    decision = evaluate_reliability_gate(
        {
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "valid_sql": True,
            "execution_result": [{"n": 10}],
            "multi_candidate_policy": {
                "enabled": False,
                "candidate_count": 1,
                "triggers": [],
            },
        }
    )

    assert decision.action == "answer"
    assert decision.reason == "validated_executed_sql"


def test_reliability_gate_does_not_require_candidate_evidence_for_annotation_only_policy():
    decision = evaluate_reliability_gate(
        {
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "valid_sql": True,
            "execution_result": [{"n": 10}],
            "multi_candidate_generation_enabled": False,
            "multi_candidate_policy": {
                "enabled": True,
                "candidate_count": 2,
                "triggers": ["complex_intent"],
            },
            "candidate_sqls": [],
            "candidate_consistency": None,
        }
    )

    assert decision.action == "answer"
    assert decision.reason == "validated_executed_sql"
    assert decision.signals["candidate_evidence_missing_after_trigger"] is False


def test_agent_prediction_records_reliability_gate_when_feature_enabled():
    prediction = agent_prediction(
        {
            "id": "synthetic-case",
            "question": "count rows",
            "gold_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "expected_action": "generate_sql",
        },
        _FakeWorkflow(),
        _FakeExecutor(),
        ablation_config={
            "reliability_gate": True,
            "reliability_gate_review_consistency_failures": True,
        },
    )

    assert prediction["reliability_gate_action"] == "answer"
    assert prediction["reliability_gate"]["reason"] == "validated_executed_sql"
    assert prediction["reliability_gate_review_consistency_failures"] is True
    assert (
        prediction["reliability_gate"]["signals"]["reliability_gate_review_consistency_failures"]
        is True
    )
    assert prediction["candidate_sqls"][0]["candidate_id"] == "primary"
    assert prediction["selected_candidate_id"] == "primary"
    assert prediction["candidate_consistency"] == {"passed": True, "issues": []}
    assert prediction["multi_candidate_policy"]["candidate_count"] == 1


def test_agent_prediction_omits_reliability_gate_when_feature_disabled():
    prediction = agent_prediction(
        {
            "id": "synthetic-case",
            "question": "count rows",
            "gold_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "expected_action": "generate_sql",
        },
        _FakeWorkflow(),
        _FakeExecutor(),
        ablation_config={"reliability_gate": False},
    )

    assert "reliability_gate_action" not in prediction
