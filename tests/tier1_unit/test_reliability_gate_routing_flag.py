from __future__ import annotations

import copy

from src.evaluation.ablation_flags import (
    RUNTIME_ENFORCED_FLAGS,
    RUNTIME_PARAMETER_FLAGS,
    ablation_runtime_contract,
    normalize_feature_flags,
)
from src.graph.nodes.compute_reliability_node import compute_reliability
from src.graph.routes import route_after_reliability
from src.graph.state import VTDState

LEGACY_DECISION_KEYS = {"action", "reason", "confidence", "warnings", "signals", "latency_ms"}


def _retry_state(ablation_config: dict | None = None) -> VTDState:
    return VTDState(
        trace_id="trace-retry",
        raw_question="test",
        intent="count_query",
        intent_confidence=0.9,
        generated_sql="SELECT bad_column FROM table_name",
        validation_errors=[{"message": "unknown column"}],
        retry_count=0,
        max_retries=3,
        ablation_config=ablation_config if ablation_config is not None else {},
    )


def _exhausted_state(ablation_config: dict | None = None) -> VTDState:
    return VTDState(
        trace_id="trace-review",
        raw_question="test",
        intent="count_query",
        intent_confidence=0.9,
        generated_sql="SELECT bad_column FROM table_name",
        validation_errors=[{"message": "unknown column"}],
        retry_count=3,
        max_retries=3,
        ablation_config=ablation_config if ablation_config is not None else {},
    )


def _routed_state(decision: dict, **kwargs) -> VTDState:
    defaults: dict = {
        "trace_id": "trace-route",
        "raw_question": "test",
        "retry_count": 0,
        "max_retries": 3,
    }
    defaults.update(kwargs)
    return VTDState(reliability_decision=decision, **defaults)


def test_reliability_gate_routing_flag_is_registered_runtime_parameter():
    assert "reliability_gate_routing" in RUNTIME_PARAMETER_FLAGS
    assert "reliability_gate_routing" not in RUNTIME_ENFORCED_FLAGS

    contract = ablation_runtime_contract({"reliability_gate_routing": False})

    assert contract["runtime_parameters"]["reliability_gate_routing"] is False
    assert contract["unknown"] == {}
    assert contract["warnings"] == []


def test_normalize_feature_flags_keeps_routing_boolean():
    normalized = normalize_feature_flags(
        {"reliability_gate": True, "reliability_gate_routing": False}
    )

    assert normalized == {"reliability_gate": True, "reliability_gate_routing": False}


def test_compute_reliability_annotation_only_forces_answer_and_preserves_original_decision():
    state = _exhausted_state({"reliability_gate": True, "reliability_gate_routing": False})

    updates = compute_reliability(state)

    decision = updates["reliability_decision"]
    assert decision["action"] == "needs_review"
    assert decision["reason"] == "validation_failed_exhausted"
    assert decision["effective_action"] == "answer"
    assert decision["routing_applied"] is False
    assert "retry_count" not in updates

    routed = _routed_state(
        dict(decision), retry_count=state.retry_count, max_retries=state.max_retries
    )
    assert route_after_reliability(routed) == "format_answer"


def test_compute_reliability_annotation_only_forces_retry_to_format_answer_path():
    state = _retry_state({"reliability_gate_routing": False})

    updates = compute_reliability(state)

    decision = updates["reliability_decision"]
    assert decision["action"] == "retry"
    assert decision["effective_action"] == "answer"
    assert "retry_count" not in updates

    routed = _routed_state(
        dict(decision), retry_count=state.retry_count, max_retries=state.max_retries
    )
    assert route_after_reliability(routed) == "format_answer"


def test_compute_reliability_routed_passes_action_through():
    state = _retry_state({"reliability_gate": True, "reliability_gate_routing": True})

    updates = compute_reliability(state)

    decision = updates["reliability_decision"]
    assert decision["action"] == "retry"
    assert decision["reason"] == "validation_failed_retryable"
    assert "effective_action" not in decision
    assert "routing_applied" not in decision
    assert updates["retry_count"] == 1

    routed = _routed_state(
        dict(decision), retry_count=updates["retry_count"], max_retries=state.max_retries
    )
    assert route_after_reliability(routed) == "reflect_on_error"


def test_compute_reliability_absent_key_matches_prechange_behavior():
    absent_updates = compute_reliability(_retry_state())
    explicit_updates = compute_reliability(
        _retry_state({"reliability_gate": True, "reliability_gate_routing": True})
    )

    absent_decision = dict(absent_updates["reliability_decision"])
    explicit_decision = dict(explicit_updates["reliability_decision"])
    absent_decision["latency_ms"] = 0
    explicit_decision["latency_ms"] = 0

    assert absent_updates.keys() == explicit_updates.keys()
    assert absent_decision == explicit_decision
    assert set(absent_decision) == LEGACY_DECISION_KEYS
    assert absent_updates["retry_count"] == explicit_updates["retry_count"] == 1

    routed = _routed_state(absent_decision, retry_count=1, max_retries=3)
    assert route_after_reliability(routed) == "reflect_on_error"


def test_route_after_reliability_maps_every_gate_action():
    base = {"reason": "r", "confidence": 0.9}

    assert route_after_reliability(_routed_state({**base, "action": "answer"})) == "format_answer"
    assert route_after_reliability(_routed_state({**base, "action": "retry"})) == "reflect_on_error"
    assert (
        route_after_reliability(_routed_state({**base, "action": "needs_review"}))
        == "reflect_on_error"
    )
    assert (
        route_after_reliability(_routed_state({**base, "action": "ask_clarification"}))
        == "ask_clarification"
    )
    assert (
        route_after_reliability(_routed_state({**base, "action": "refuse_unsafe"}))
        == "refuse_unsafe_sql"
    )
    assert route_after_reliability(_routed_state(None)) == "format_answer"


def test_route_after_reliability_fails_gracefully_when_retries_or_reflexion_exhausted():
    decision = {"action": "retry", "reason": "r", "confidence": 0.8}

    exhausted = _routed_state(copy.deepcopy(decision), retry_count=3, max_retries=3)
    assert route_after_reliability(exhausted) == "fail_gracefully"

    no_reflexion = _routed_state(
        copy.deepcopy(decision),
        retry_count=0,
        max_retries=3,
        ablation_config={"reflexion": False},
    )
    assert route_after_reliability(no_reflexion) == "fail_gracefully"

    no_repair = _routed_state(
        copy.deepcopy(decision),
        retry_count=0,
        max_retries=3,
        ablation_config={"repair": False},
    )
    assert route_after_reliability(no_repair) == "fail_gracefully"


def test_route_after_reliability_prefers_effective_action_over_original():
    decision = {
        "action": "needs_review",
        "effective_action": "answer",
        "routing_applied": False,
        "reason": "empty_execution_result",
        "confidence": 0.75,
    }

    assert route_after_reliability(_routed_state(decision)) == "format_answer"
