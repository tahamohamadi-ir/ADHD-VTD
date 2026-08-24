from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.graph.state import VTDState


def route_sql_generation(
    state: VTDState,
    *,
    llm_factory: Callable[[], Any],
    template_generator: Callable[[str], str | None],
    multi_candidate_generator: Callable[[VTDState, Any, int], dict[str, Any]],
    can_generate_extra_candidates_fn: Callable[[VTDState], bool],
    clock: Callable[[], float],
    max_tokens_fn: Callable[[], int],
) -> dict[str, Any]:
    """Route SQL generation without owning prompt, validation, or execution logic."""

    if not state.prompt:
        return {"generated_sql": ""}

    if bool(state.ablation_config.get("deterministic_templates", False)):
        template_response = template_generator(state.raw_question)
        if template_response is not None:
            return {
                "generated_sql": template_response,
                "raw_model_response": template_response,
                "generation_source": "deterministic_template",
                "generation_latency_ms": 0,
            }

    llm = llm_factory()

    policy = state.multi_candidate_policy if isinstance(state.multi_candidate_policy, dict) else {}
    multi_candidate_generation_flag = bool(
        state.ablation_config.get("multi_candidate_generation", False)
    )
    candidate_count = int(policy.get("candidate_count") or 1)
    multi_candidate_enabled = (
        multi_candidate_generation_flag
        and bool(policy.get("enabled"))
        and candidate_count > 1
        and can_generate_extra_candidates_fn(state)
    )

    if multi_candidate_enabled:
        return multi_candidate_generator(state, llm, candidate_count)

    started = clock()
    response_text = llm.generate_json(
        state.prompt,
        enforce_json=True,
        max_tokens=max_tokens_fn(),
    )
    generation_latency_ms = int((clock() - started) * 1000)
    return {
        "generated_sql": response_text,
        "raw_model_response": response_text,
        "generation_source": "llm",
        "generation_latency_ms": generation_latency_ms,
    }
