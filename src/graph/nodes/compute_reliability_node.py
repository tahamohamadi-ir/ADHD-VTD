import time
from typing import Any, Dict

from src.graph.state import VTDState
from src.evaluation.reliability_gate import evaluate_reliability_gate, ReliabilityGatePolicy
from src.graph.nodes.base_nodes import _with_retry_increment


def reliability_routing_enabled(ablation_config: Dict[str, Any] | None) -> bool:
    """Routing is the historical default; only an explicit false disables it."""
    if not ablation_config:
        return True
    return bool(ablation_config.get("reliability_gate_routing", True))


def compute_reliability(state: VTDState) -> Dict[str, Any]:
    """
    Computes the reliability decision for the generated SQL and execution result.
    If the reliability is low, this will trigger a fallback (retry, ask_clarification, or fail_gracefully).
    """
    # The state must be converted to dict to be passed to the evaluator
    state_dict = state.model_dump()

    # We enable the use of judge signals if any are present (e.g. from semantic evaluation).
    # But usually this is evaluated purely on runtime signals like execution result emptiness, validation, etc.
    policy = ReliabilityGatePolicy(
        min_intent_confidence=0.4, review_empty_results=True, consistency_failure_action="retry"
    )

    started = time.perf_counter()
    decision = evaluate_reliability_gate(state_dict, policy=policy)
    decision_payload = decision.as_dict()
    decision_payload["latency_ms"] = int((time.perf_counter() - started) * 1000)

    if not reliability_routing_enabled(state_dict.get("ablation_config")):
        decision_payload["effective_action"] = "answer"
        decision_payload["routing_applied"] = False
        return {"reliability_decision": decision_payload}

    updates = {"reliability_decision": decision_payload}

    if decision.action in ("retry", "needs_review"):
        return _with_retry_increment(state, updates)

    return updates
