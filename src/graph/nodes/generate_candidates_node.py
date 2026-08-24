from typing import Any, Dict
from src.graph.state import VTDState
from src.evaluation.multi_candidate_policy import (
    decide_multi_candidate,
    multi_candidate_policy_from_config,
)


def generate_candidates(state: VTDState) -> Dict[str, Any]:
    """Plan multi-candidate generation without performing an LLM call.

    Actual SQL candidate generation is owned by `base_nodes.generate_sql` and
    `candidate_orchestrator.py`, where validation, inspection, and adoption
    gates are available. This node remains a deterministic compatibility entry
    point for workflows that want to materialize `multi_candidate_policy`.
    """

    state_dict = state.model_dump()
    decision = decide_multi_candidate(
        state_dict,
        policy=multi_candidate_policy_from_config(state_dict.get("ablation_config")),
    )

    if not decision.enabled or decision.candidate_count <= 1:
        return {}

    return {"multi_candidate_policy": decision.as_dict()}
