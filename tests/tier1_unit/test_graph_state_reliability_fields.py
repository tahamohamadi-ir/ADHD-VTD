from __future__ import annotations

from src.graph.state import ReliabilityState, SQLCandidate, VTDState


def test_graph_state_defaults_keep_multi_candidate_inactive():
    state = VTDState(trace_id="trace", raw_question="count rows")

    assert state.candidate_sqls == []
    assert state.selected_candidate_id is None
    assert state.candidate_consistency is None
    assert state.multi_candidate_policy is None
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
        multi_candidate_policy={"enabled": False, "candidate_count": 1},
        reliability=ReliabilityState(
            gate_action="answer",
            gate_reason="validated_executed_sql",
            confidence=0.9,
        ),
    )

    assert state.candidate_sqls[0].candidate_id == "primary"
    assert state.selected_candidate_id == "primary"
    assert state.candidate_consistency == {"passed": True, "issues": []}
    assert state.multi_candidate_policy["candidate_count"] == 1
    assert state.reliability.gate_action == "answer"
