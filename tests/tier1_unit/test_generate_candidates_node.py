from __future__ import annotations

from src.graph.nodes.generate_candidates_node import generate_candidates
from src.graph.state import VTDState


def test_generate_candidates_returns_empty_when_policy_does_not_enable_candidates() -> None:
    state = VTDState(
        trace_id="trace",
        raw_question="count students",
        intent="count_query",
        intent_confidence=0.95,
    )

    assert generate_candidates(state) == {}


def test_generate_candidates_materializes_policy_without_llm_call() -> None:
    state = VTDState(
        trace_id="trace",
        raw_question="Show depression rate by sleep category.",
        normalized_question="Show depression rate by sleep category.",
        intent="rate_query",
        intent_confidence=0.9,
        retry_count=1,
        validation_errors=[{"message": "missing rate"}],
        generated_sql=(
            "SELECT sleep_duration_category, COUNT(*) AS n "
            "FROM student_depression GROUP BY sleep_duration_category"
        ),
    )

    updates = generate_candidates(state)

    assert updates["multi_candidate_policy"]["enabled"] is True
    assert updates["multi_candidate_policy"]["candidate_count"] == 2
    assert "validation_failed" in updates["multi_candidate_policy"]["triggers"]
