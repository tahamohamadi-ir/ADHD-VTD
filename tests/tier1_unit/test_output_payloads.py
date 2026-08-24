from __future__ import annotations

from typing import Any

from src.core.enums import IntentLabel
from src.graph.nodes.output_payloads import (
    action_answer_updates,
    clarification_answer_updates,
    fail_gracefully_updates,
    format_answer_updates,
)
from src.graph.state import VTDState


def test_format_answer_updates_wires_formatter_chart_and_explanation_builder() -> None:
    calls: dict[str, Any] = {}
    state = VTDState(
        trace_id="trace",
        raw_question="question",
        execution_result=[{"category": "A", "n": 2}],
        explanation="fallback explanation",
    )

    def answer_formatter(payload: dict[str, Any]) -> dict[str, Any]:
        calls["answer_action"] = payload["actual_action"]
        return {"final_answer": "done"}

    def chart_recommender(rows: list[dict[str, Any]] | None) -> dict[str, Any]:
        calls["chart_rows"] = rows
        return {"recommended_visual": "bar_chart", "chart_reason": "two columns"}

    def explanation_builder(payload: dict[str, Any]) -> str | None:
        calls["explanation_action"] = payload["actual_action"]
        return "built explanation"

    updates = format_answer_updates(
        state,
        answer_formatter=answer_formatter,
        chart_recommender=chart_recommender,
        explanation_builder=explanation_builder,
    )

    assert updates == {
        "final_answer": "done",
        "recommended_visual": "bar_chart",
        "chart_reason": "two columns",
        "explanation": "built explanation",
        "narrative": None,
        "actual_action": "format_answer",
    }
    assert calls == {
        "answer_action": "format_answer",
        "chart_rows": [{"category": "A", "n": 2}],
        "explanation_action": "format_answer",
    }


def test_format_answer_updates_uses_existing_explanation_when_builder_returns_none() -> None:
    state = VTDState(
        trace_id="trace",
        raw_question="question",
        execution_result=[],
        explanation="existing explanation",
    )

    updates = format_answer_updates(
        state,
        answer_formatter=lambda _payload: {"final_answer": "empty"},
        chart_recommender=lambda _rows: {"recommended_visual": None, "chart_reason": None},
        explanation_builder=lambda _payload: None,
    )

    assert updates["final_answer"] == "empty"
    assert updates["explanation"] == "existing explanation"
    assert updates["actual_action"] == "format_answer"


def test_fail_gracefully_updates_sets_action_after_formatting() -> None:
    captured: dict[str, Any] = {}
    state = VTDState(trace_id="trace", raw_question="question", retry_count=3)

    def answer_formatter(payload: dict[str, Any]) -> dict[str, Any]:
        captured["action"] = payload["actual_action"]
        return {"final_answer": "failed"}

    updates = fail_gracefully_updates(state, answer_formatter=answer_formatter)

    assert captured == {"action": "fail_gracefully"}
    assert updates == {"final_answer": "failed", "actual_action": "fail_gracefully"}


def test_action_answer_updates_sets_requested_action() -> None:
    state = VTDState(trace_id="trace", raw_question="question")

    updates = action_answer_updates(
        state,
        action="refuse_unsafe_sql",
        answer_formatter=lambda payload: {"final_answer": payload["actual_action"]},
    )

    assert updates == {
        "final_answer": "refuse_unsafe_sql",
        "actual_action": "refuse_unsafe_sql",
    }


def test_clarification_answer_updates_routes_definition_and_chart_actions() -> None:
    seen_actions: list[str] = []

    def formatter(payload: dict[str, Any]) -> dict[str, Any]:
        seen_actions.append(payload["actual_action"])
        return {"final_answer": payload["actual_action"]}

    definition = clarification_answer_updates(
        VTDState(trace_id="d", raw_question="تعریف", intent=IntentLabel.DEFINITION_QUERY),
        answer_formatter=formatter,
    )
    chart = clarification_answer_updates(
        VTDState(
            trace_id="c",
            raw_question="نمودار",
            intent=IntentLabel.CHART_QUERY,
            should_generate_sql=False,
        ),
        answer_formatter=formatter,
    )
    clarification = clarification_answer_updates(
        VTDState(trace_id="a", raw_question="مبهم"),
        answer_formatter=formatter,
    )

    assert definition["actual_action"] == "answer_without_sql"
    assert chart["actual_action"] == "answer_chart_recommendation"
    assert clarification["actual_action"] == "ask_clarification"
    assert seen_actions == [
        "answer_without_sql",
        "answer_chart_recommendation",
        "ask_clarification",
    ]
