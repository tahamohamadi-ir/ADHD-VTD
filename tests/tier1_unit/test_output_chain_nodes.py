from __future__ import annotations

from src.graph.nodes.output_chain_nodes import log_benchmark_record, recommend_chart
from src.graph.state import VTDState


def _state(**overrides) -> VTDState:
    defaults: dict = {
        "trace_id": "trace-1",
        "raw_question": "تعداد دانشجوها",
        "benchmark_case_id": "VTD-001",
        "actual_action": "format_answer",
        "intent": "count_query",
    }
    defaults.update(overrides)
    return VTDState(**defaults)


def test_recommend_chart_kpi_for_single_scalar():
    updates = recommend_chart(_state(execution_result=[{"n": 5}]))

    assert updates["recommended_visual"] == "kpi"
    assert updates["chart_reason"] == "Single scalar value"


def test_recommend_chart_bar_chart_for_two_column_rows():
    updates = recommend_chart(
        _state(execution_result=[{"gender": "Female", "n": 5}, {"gender": "Male", "n": 3}])
    )

    assert updates["recommended_visual"] == "bar_chart"
    assert updates["chart_reason"]


def test_recommend_chart_none_safe_without_execution_result():
    updates = recommend_chart(_state())

    assert updates["recommended_visual"] is None
    assert updates["chart_reason"] is None


def test_log_benchmark_record_builds_redacted_record():
    state = _state(
        generated_sql="SELECT secret_column FROM private_table",
        attempts=[{"iteration": 0, "sql": "SELECT secret_column FROM private_table"}],
        execution_result=[{"secret_column": 1}],
        reliability_decision={"latency_ms": 12},
    )

    record = log_benchmark_record(state)["benchmark_record"]

    assert record["trace_id"] == "trace-1"
    assert record["benchmark_case_id"] == "VTD-001"
    assert record["actual_action"] == "format_answer"
    assert record["intent"] == "count_query"
    assert record["reliability_gate_latency_ms"] == 12
    assert "sql" not in record
    assert "generated_sql" not in record
    assert all("secret" not in str(value) for value in record.values())


def test_log_benchmark_record_omits_absent_latency_hints():
    record = log_benchmark_record(_state())["benchmark_record"]

    assert "generation_latency_ms" not in record
    assert "reliability_gate_latency_ms" not in record


def test_log_benchmark_record_is_none_safe_on_empty_state():
    state = VTDState(trace_id="trace-empty", raw_question="")

    record = log_benchmark_record(state)["benchmark_record"]

    assert record == {
        "trace_id": "trace-empty",
        "benchmark_case_id": None,
        "actual_action": None,
        "intent": None,
    }
