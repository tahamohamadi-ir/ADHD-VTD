from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from src.core.enums import IntentLabel
from src.graph.state import VTDState

logger = logging.getLogger(__name__)


def format_answer_updates(
    state: VTDState,
    *,
    answer_formatter: Callable[[dict[str, Any]], dict[str, Any]],
    chart_recommender: Callable[[list[dict[str, Any]] | None], dict[str, Any]],
    explanation_builder: Callable[[dict[str, Any]], str | None],
    narrative_generator: Callable[..., str | None] | None = None,
) -> dict[str, Any]:
    """Build final answer updates without owning output implementation details."""

    state_dict = state.model_dump()
    state_dict["actual_action"] = "format_answer"

    answer = answer_formatter(state_dict)
    chart = chart_recommender(state_dict.get("execution_result", []))
    explanation = explanation_builder(state_dict)

    narrative: str | None = None
    if narrative_generator is not None and state_dict.get("execution_result"):
        try:
            narrative = narrative_generator(
                question=state_dict.get("raw_question"),
                execution_result=state_dict.get("execution_result"),
                chart_recommendation=chart,
                category=getattr(state.intent, "value", state.intent),
            )
        except Exception as exc:
            narrative = None
            logger.warning(
                "Narrative generation failed: %s: %s",
                type(exc).__name__,
                exc,
            )

    final_answer = answer.get("final_answer")
    if narrative and final_answer:
        final_answer = f"{final_answer}\n\n**روایت:**\n{narrative}"

    return {
        "final_answer": final_answer,
        "recommended_visual": chart.get("recommended_visual"),
        "chart_reason": chart.get("chart_reason"),
        "explanation": explanation or state.explanation,
        "narrative": narrative,
        "actual_action": "format_answer",
    }


def fail_gracefully_updates(
    state: VTDState,
    *,
    answer_formatter: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    return action_answer_updates(
        state,
        action="fail_gracefully",
        answer_formatter=answer_formatter,
    )


def action_answer_updates(
    state: VTDState,
    *,
    action: str,
    answer_formatter: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    state_dict = state.model_dump()
    state_dict["actual_action"] = action
    answer = answer_formatter(state_dict)
    answer["actual_action"] = action
    return answer


def clarification_answer_updates(
    state: VTDState,
    *,
    answer_formatter: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    if state.intent == IntentLabel.DEFINITION_QUERY:
        action = "answer_without_sql"
    elif state.intent == IntentLabel.CHART_QUERY and not state.should_generate_sql:
        action = "answer_chart_recommendation"
    else:
        action = "ask_clarification"
    return action_answer_updates(state, action=action, answer_formatter=answer_formatter)
