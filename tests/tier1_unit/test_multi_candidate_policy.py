from __future__ import annotations

from src.evaluation.multi_candidate_policy import (
    MultiCandidatePolicy,
    decide_multi_candidate,
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
