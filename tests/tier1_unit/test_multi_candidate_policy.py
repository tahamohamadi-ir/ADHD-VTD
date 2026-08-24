from __future__ import annotations

from src.evaluation.multi_candidate_policy import (
    MultiCandidatePolicy,
    decide_multi_candidate,
    multi_candidate_policy_from_config,
)


def test_multi_candidate_policy_keeps_simple_confident_query_single_candidate():
    decision = decide_multi_candidate(
        {
            "question": "How many students are depressed?",
            "intent": "count_query",
            "intent_confidence": 0.95,
            "valid_sql": True,
            "retry_count": 0,
        }
    )

    assert decision.enabled is False
    assert decision.candidate_count == 1
    assert decision.reason == "simple_or_confident_query"


def test_multi_candidate_policy_triggers_after_validation_failure():
    decision = decide_multi_candidate(
        {
            "question": "Show depression rate by sleep category.",
            "intent": "rate_query",
            "intent_confidence": 0.9,
            "valid_sql": False,
            "retry_count": 1,
        }
    )

    assert decision.enabled is True
    assert decision.candidate_count == 2
    assert "validation_failed" in decision.triggers
    assert "retry_in_progress" in decision.triggers


def test_multi_candidate_policy_filters_triggers_without_gold_labels():
    decision = decide_multi_candidate(
        {
            "question": "Show depression rate by gender.",
            "intent": "rate_query",
            "intent_confidence": 0.9,
            "qir": {
                "expected_result_shape": "table",
                "dimensions": ["gender"],
                "metrics": ["depression_flag"],
            },
            "valid_sql": False,
            "case_id": "VTD-hidden",
            "gold_sql": "SELECT hidden FROM gold",
            "execution_correct": True,
        },
        policy=MultiCandidatePolicy(
            allowed_triggers=("validation_failed",),
            blocked_triggers=("complex_intent",),
        ),
    )

    assert decision.enabled is True
    assert decision.triggers == ["validation_failed"]
    assert decision.suppressed_triggers == ["complex_intent"]
    assert decision.as_dict()["suppressed_triggers"] == ["complex_intent"]


def test_multi_candidate_policy_disables_when_all_triggers_are_filtered():
    decision = decide_multi_candidate(
        {
            "question": "Show depression rate by gender.",
            "intent": "rate_query",
            "intent_confidence": 0.9,
            "qir": {
                "expected_result_shape": "table",
                "dimensions": ["gender"],
                "metrics": ["depression_flag"],
            },
        },
        policy=MultiCandidatePolicy(allowed_triggers=("validation_failed",)),
    )

    assert decision.enabled is False
    assert decision.candidate_count == 1
    assert decision.reason == "triggers_filtered_by_policy"
    assert decision.triggers == []
    assert decision.suppressed_triggers == ["complex_intent"]


def test_multi_candidate_policy_from_config_parses_trigger_filters():
    policy = multi_candidate_policy_from_config(
        {
            "multi_candidate_allowed_triggers": "validation_failed, complex_intent",
            "multi_candidate_blocked_triggers": ["difficulty_hint", "low_intent_confidence"],
        }
    )

    assert policy.allowed_triggers == ("complex_intent", "validation_failed")
    assert policy.blocked_triggers == ("difficulty_hint", "low_intent_confidence")


def test_multi_candidate_policy_triggers_for_complex_dashboard_hint():
    decision = decide_multi_candidate(
        {
            "question": "Build a dashboard of quartile change in prevalence.",
            "intent": "grouping_query",
            "intent_confidence": 0.8,
            "category": "global_change_dashboard",
        }
    )

    assert decision.enabled is True
    assert "complex_category" in decision.triggers
    assert "complex_intent" in decision.triggers


def test_multi_candidate_policy_triggers_for_qir_table_shape():
    decision = decide_multi_candidate(
        {
            "question": "Show depression rate by gender.",
            "intent": "rate_query",
            "intent_confidence": 0.9,
            "qir": {
                "expected_result_shape": "table",
                "dimensions": ["gender"],
                "metrics": ["depression_flag"],
            },
            "retry_count": 0,
        }
    )

    assert decision.enabled is True
    assert "complex_intent" in decision.triggers


def test_multi_candidate_policy_can_be_disabled():
    decision = decide_multi_candidate(
        {"valid_sql": False, "retry_count": 1},
        policy=MultiCandidatePolicy(mode="disabled"),
    )

    assert decision.enabled is False
    assert decision.candidate_count == 1
    assert decision.reason == "disabled"


def test_multi_candidate_policy_always_mode_respects_max_candidates():
    decision = decide_multi_candidate(
        {},
        policy=MultiCandidatePolicy(mode="always", adaptive_candidates=5, max_candidates=3),
    )

    assert decision.enabled is True
    assert decision.candidate_count == 3
    assert decision.reason == "always"


def test_multi_candidate_policy_does_not_need_gold_or_case_labels():
    decision = decide_multi_candidate(
        {
            "case_id": "VTD-hidden",
            "gold_sql": "SELECT hidden FROM gold",
            "execution_correct": False,
            "result_match": False,
            "intent": "count_query",
            "intent_confidence": 0.9,
            "valid_sql": True,
            "retry_count": 0,
        }
    )

    assert decision.enabled is False
    assert decision.triggers == []
