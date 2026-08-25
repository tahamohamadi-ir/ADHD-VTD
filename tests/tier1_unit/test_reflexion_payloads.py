from __future__ import annotations

from src.graph.nodes.reflexion_payloads import (
    latest_reflexion_context,
    repair_attempt_history,
    reflexion_updates,
    repair_critic_feedback,
    repair_validation_error_text,
    seed_transition_memory,
    update_latest_attempt_with_reflexion,
)
from src.graph.state import SQLAttempt, VTDState
from src.reflexion.transition_memory import TransitionMemory


def test_latest_reflexion_context_uses_defaults_for_missing_fields() -> None:
    state = VTDState(
        trace_id="trace",
        raw_question="question",
        attempts=[SQLAttempt(iteration=0)],
    )

    assert latest_reflexion_context(state) == ("Unknown failure", "")


def test_seed_transition_memory_records_prior_attempts() -> None:
    memory = TransitionMemory()
    attempts = [SQLAttempt(iteration=0, sql="SELECT 1", error_message="bad")]

    seed_transition_memory(attempts, memory)

    assert memory.is_looping("SELECT 1", "bad")


def test_update_latest_attempt_with_reflexion_only_changes_latest_attempt() -> None:
    attempts = [
        SQLAttempt(iteration=0, sql="SELECT 1"),
        SQLAttempt(iteration=1, sql="SELECT missing"),
    ]

    updated = update_latest_attempt_with_reflexion(
        attempts,
        critic_feedback="feedback",
        repair_plan="plan",
    )

    assert updated[0] is attempts[0]
    assert updated[-1].critic_feedback == "feedback"
    assert updated[-1].repair_plan == "plan"


def test_repair_validation_error_text_prefers_validation_errors() -> None:
    state = VTDState(
        trace_id="trace",
        raw_question="question",
        validation_errors=[{"message": "unknown column"}, {"message": "raw error"}],
    )

    assert repair_validation_error_text(state, "fallback") == "unknown column\nraw error"


def test_repair_validation_error_text_uses_candidate_consistency_when_unknown() -> None:
    state = VTDState(
        trace_id="trace",
        raw_question="question",
        candidate_consistency_report={
            "passed": False,
            "issues": [{"message": "candidate mismatch"}, "raw candidate issue"],
        },
    )

    assert repair_validation_error_text(state, "Unknown failure") == (
        "candidate mismatch\nraw candidate issue"
    )


def test_repair_critic_feedback_and_updates_contract() -> None:
    attempts = [SQLAttempt(iteration=0)]

    assert repair_critic_feedback("feedback", "plan") == "feedback\n\nRepair Plan: plan"
    assert reflexion_updates(prompt="PROMPT", attempts=attempts) == {
        "prompt": "PROMPT",
        "attempts": attempts,
        "repair_attempt_history": [],
    }


def test_repair_attempt_history_keeps_recent_failed_pairs_only() -> None:
    ok_attempt = SQLAttempt(iteration=0, sql="SELECT 1")
    failed_no_sql = SQLAttempt(iteration=1, error_message="boom")
    failures = [
        SQLAttempt(iteration=i, sql=f"SELECT {i}", error_message=f"err{i}") for i in range(2, 7)
    ]
    history = repair_attempt_history([ok_attempt, failed_no_sql, *failures])
    assert [item["sql"] for item in history] == ["SELECT 4", "SELECT 5", "SELECT 6"]
    assert history[-1]["error"] == "err6"
    assert repair_attempt_history(failures, limit=0) == []
