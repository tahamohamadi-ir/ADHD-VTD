from collections.abc import Callable
from typing import Any

from src.graph.state import VTDState


def generate_sql_candidates(
    state: VTDState,
    llm: Any,
    candidate_count: int,
    *,
    clock: Callable[[], float],
    max_tokens_fn: Callable[[], int],
    extra_generation_budget_ms_fn: Callable[[dict[str, Any]], int | None],
    prompt_variant_fn: Callable[[int], str],
    candidate_prompt_fn: Callable[[str | None, str], str],
    parse_json_fn: Callable[[str], dict[str, Any] | None],
    inspect_candidate_fn: Callable[..., dict[str, Any]],
    consistency_candidate_factory: Callable[..., Any],
    analyze_consistency_fn: Callable[[list[Any]], Any],
    verify_candidates_fn: Callable[..., Any],
    adoption_id_fn: Callable[..., str | None],
) -> dict[str, Any]:
    """Generate, inspect, and select SQL candidates without owning validators.

    Validation and execution stay behind the injected candidate inspector. This
    function coordinates candidate generation, consistency checks, verifier
    scoring, latency budget accounting, and optional adoption.
    """

    requested = max(1, min(3, candidate_count))
    raw_outputs: dict[str, str] = {}
    parsed_payloads: dict[str, dict[str, Any] | None] = {}
    candidates: list[dict[str, Any]] = []
    started = clock()
    extra_generation_budget_ms = extra_generation_budget_ms_fn(state.ablation_config)
    budget_exhausted = False

    for index in range(requested):
        candidate_id = f"candidate_{index + 1}"
        prompt_variant = prompt_variant_fn(index)
        candidate_prompt = candidate_prompt_fn(state.prompt, prompt_variant)
        response_text = llm.generate_json(
            candidate_prompt,
            enforce_json=True,
            max_tokens=max_tokens_fn(),
        )
        raw_outputs[candidate_id] = response_text
        parsed = parse_json_fn(response_text)
        parsed_payloads[candidate_id] = parsed
        sql = parsed.get("sql") if isinstance(parsed, dict) else None
        candidates.append(
            inspect_candidate_fn(
                candidate_id=candidate_id,
                sql=sql,
                state=state,
                raw_model_response=response_text,
                parsed_payload=parsed,
                prompt_variant=prompt_variant,
            )
        )
        elapsed_ms = int((clock() - started) * 1000)
        if (
            extra_generation_budget_ms is not None
            and index < requested - 1
            and elapsed_ms >= extra_generation_budget_ms
        ):
            budget_exhausted = True
            break

    consistency_report = analyze_consistency_fn(
        [
            consistency_candidate_factory(
                candidate_id=str(candidate["candidate_id"]),
                sql=candidate.get("sql"),
                valid_sql=candidate.get("valid_sql"),
                execution_passed=candidate.get("execution_passed"),
                result_hash=candidate.get("result_hash"),
                metadata=candidate.get("metadata") or {},
            )
            for candidate in candidates
        ]
    )
    verifier_enabled = bool(state.ablation_config.get("multi_candidate_verifier", True))
    verification_report = None
    selected_candidate_id = consistency_report.selected_candidate_id
    if verifier_enabled:
        verification_report = verify_candidates_fn(
            candidates,
            consistency_report=consistency_report.as_dict(),
            schema_context=state.schema_context,
            value_links=state.value_links,
        )
        candidates = verification_report.candidates
        selected_candidate_id = verification_report.selected_candidate_id

    primary = candidates[0] if candidates else {}
    primary_id = str(primary.get("candidate_id") or "candidate_1")
    adoption_enabled = (
        bool(state.ablation_config["multi_candidate_adoption"])
        if "multi_candidate_adoption" in state.ablation_config
        else False
    )
    adopted_candidate_id = adoption_id_fn(
        candidates,
        selected_candidate_id=selected_candidate_id,
        adoption_enabled=adoption_enabled,
        consistency_passed=consistency_report.passed,
        verifier_action=verification_report.action if verification_report else None,
        primary_id=primary_id,
    )
    output_candidate_id = adopted_candidate_id or primary_id
    selected_raw = raw_outputs.get(output_candidate_id) or ""
    selected_payload = parsed_payloads.get(output_candidate_id)
    generation_latency_ms = int((clock() - started) * 1000)

    result = {
        "generated_sql": selected_raw,
        "raw_model_response": selected_raw,
        "generation_source": "llm_multi_candidate",
        "generation_latency_ms": generation_latency_ms,
        "candidate_sqls": candidates,
        "selected_candidate_id": adopted_candidate_id,
        "candidate_consistency": consistency_report.as_dict(),
        "candidate_verification": verification_report.as_dict() if verification_report else None,
        "parsed_payload": selected_payload,
    }
    if extra_generation_budget_ms is not None:
        result["multi_candidate_generation_budget"] = {
            "configured_budget_ms": extra_generation_budget_ms,
            "requested_candidate_count": requested,
            "generated_candidate_count": len(candidates),
            "budget_exhausted": budget_exhausted,
        }
    return result
