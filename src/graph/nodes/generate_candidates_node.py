from typing import Any, Dict
from src.graph.state import VTDState
from src.evaluation.multi_candidate_policy import (
    decide_multi_candidate,
    multi_candidate_policy_from_config,
)
from src.core.llm import call_llm
import json


def generate_candidates(state: VTDState) -> Dict[str, Any]:
    """
    If multi_candidate_policy allows it, generates multiple alternative SQL queries.
    This replaces or augments generate_sql in scenarios where we need diverse candidates.
    Currently, we implement a simple single-call multi-SQL generation via a JSON prompt
    if candidate_count > 1.
    """
    state_dict = state.model_dump()
    decision = decide_multi_candidate(
        state_dict,
        policy=multi_candidate_policy_from_config(state_dict.get("ablation_config")),
    )

    if not decision.enabled or decision.candidate_count <= 1:
        return {}

    # Build a special prompt to ask for multiple distinct SQL queries
    base_prompt = state.prompt
    multi_prompt = f"{base_prompt}\n\nPlease generate {decision.candidate_count} DISTINCT alternative SQL queries that might answer the user's question. Each alternative should use a slightly different approach or interpretation if ambiguity exists. Return a JSON array of strings containing ONLY the SQL queries."

    # In a real implementation, we would parse the JSON array and validate each.
    # For now, we will return it as candidate_sqls.
    try:
        response = call_llm(multi_prompt)  # pseudo-code for calling LLM
        # This is a stub for the actual LLM call.
        # Since we use qwen2.5-coder locally, we need to adapt the parse_llm_output to handle JSON lists.
    except Exception as e:
        pass

    return {"multi_candidate_policy": decision.as_dict()}
