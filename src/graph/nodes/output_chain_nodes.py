from __future__ import annotations

from typing import Any, Dict

from src.graph.state import VTDState
from src.output.chart_recommender import recommend_chart as recommend_visual


def _payload_latency_ms(payload: dict[str, Any] | None) -> int | None:
    raw = (payload or {}).get("latency_ms")
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    return raw


def recommend_chart(state: VTDState) -> Dict[str, Any]:
    """Recommend a visualization for the execution result, when present."""
    recommendation = recommend_visual(state.execution_result)
    return {
        "recommended_visual": recommendation.get("recommended_visual"),
        "chart_reason": recommendation.get("chart_reason"),
    }


def log_benchmark_record(state: VTDState) -> Dict[str, Any]:
    """Build a compact, redaction-friendly benchmark record for the trace.

    Contains identifiers and actions only: no SQL text, no result rows.
    """
    record: Dict[str, Any] = {
        "trace_id": state.trace_id,
        "benchmark_case_id": state.benchmark_case_id,
        "actual_action": state.actual_action,
        "intent": state.intent,
    }
    if state.generation_latency_ms is not None:
        record["generation_latency_ms"] = state.generation_latency_ms
    gate_latency_ms = _payload_latency_ms(state.reliability_decision)
    if gate_latency_ms is not None:
        record["reliability_gate_latency_ms"] = gate_latency_ms
    return {"benchmark_record": record}
