from __future__ import annotations

from src.graph.nodes.base_nodes import classify_intent
from src.graph.state import ReliabilityState, SQLCandidate, VTDState


def test_graph_state_defaults_keep_multi_candidate_inactive():
    state = VTDState(trace_id="trace", raw_question="count rows")

    assert state.candidate_sqls == []
    assert state.selected_candidate_id is None
    assert state.candidate_consistency is None
    assert state.candidate_verification is None
    assert state.multi_candidate_policy is None
    assert state.multi_candidate_generation_budget is None
    assert state.reliability is None


def test_graph_state_can_store_candidate_and_reliability_annotations():
    state = VTDState(
        trace_id="trace",
        raw_question="count rows",
        candidate_sqls=[
            SQLCandidate(
                candidate_id="primary",
                sql="SELECT COUNT(*) AS n FROM student_depression",
                valid_sql=True,
                execution_passed=True,
                result_hash="hash",
                source="primary_generation",
            )
        ],
        selected_candidate_id="primary",
        candidate_consistency={"passed": True, "issues": []},
        candidate_verification={"action": "select", "selected_candidate_id": "primary"},
        multi_candidate_policy={"enabled": False, "candidate_count": 1},
        multi_candidate_generation_budget={
            "configured_budget_ms": 60000,
            "requested_candidate_count": 2,
            "generated_candidate_count": 1,
            "budget_exhausted": True,
        },
        reliability=ReliabilityState(
            gate_action="answer",
            gate_reason="validated_executed_sql",
            confidence=0.9,
        ),
    )

    assert state.candidate_sqls[0].candidate_id == "primary"
    assert state.selected_candidate_id == "primary"
    assert state.candidate_consistency == {"passed": True, "issues": []}
    assert state.candidate_verification["selected_candidate_id"] == "primary"
    assert state.multi_candidate_policy["candidate_count"] == 1
    assert state.multi_candidate_generation_budget["budget_exhausted"] is True
    assert state.reliability.gate_action == "answer"


def test_classify_intent_propagates_privacy_safety_fields():
    state = VTDState(
        trace_id="trace",
        raw_question="privacy",
        normalized_question=(
            "\u0628\u0631\u0627\u06cc user\u0647\u0627\u06cc "
            "\u0627\u0641\u0633\u0631\u062f\u0647 \u0627\u0633\u0645 \u0648 "
            "\u0645\u0634\u062e\u0635\u0627\u062a \u0641\u0631\u062f\u06cc \u0628\u062f\u0647."
        ),
    )

    updates = classify_intent(state)

    assert updates["intent"] == "unsafe_query"
    assert updates["should_generate_sql"] is False
    assert updates["safety_label"] == "privacy_risk"
    assert updates["needs_clarification"] is False
