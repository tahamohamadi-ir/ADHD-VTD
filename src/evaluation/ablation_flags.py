from __future__ import annotations

from typing import Any

RUNTIME_ENFORCED_FLAGS = {
    "nlu",
    "schema_linking",
    "value_linking",
    "cag",
    "reflexion",
    "repair",
    "llm_judge",
    "reliability_gate",
    "reliability_gate_review_consistency_failures",
    "multi_candidate_generation",
    "multi_candidate_adoption",
    "multi_candidate_verifier",
    "deterministic_templates",
}

RUNTIME_LOCKED_FLAGS = {
    "abstention": "Abstention/clarification behavior is part of the reliability policy and cannot be disabled by this runner.",
    "safety": "Safety cannot be disabled in benchmark execution.",
    "validation": "Read-only SQL validation cannot be disabled in benchmark execution.",
}

RUNTIME_PARAMETER_FLAGS = {
    "max_retries",
    "multi_candidate_extra_generation_budget_ms",
    "multi_candidate_allowed_triggers",
    "multi_candidate_blocked_triggers",
    "retrieval_backend",
    "reranker",
    "reliability_gate_routing",
}

METADATA_ONLY_FLAGS: dict[str, str] = {}


def normalize_feature_flags(flags: dict[str, Any] | None) -> dict[str, Any]:
    if not flags:
        return {}
    normalized: dict[str, Any] = {}
    for raw_key, value in flags.items():
        key = str(raw_key)
        if isinstance(value, bool):
            normalized[key] = value
        elif key in RUNTIME_PARAMETER_FLAGS:
            normalized[key] = value
    return normalized


def ablation_runtime_contract(flags: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    enforced: dict[str, bool] = {}
    locked: dict[str, bool] = {}
    runtime_parameters: dict[str, Any] = {}
    metadata_only: dict[str, bool] = {}
    unknown: dict[str, Any] = {}

    for key, value in sorted(flags.items()):
        if key in RUNTIME_ENFORCED_FLAGS:
            enforced[key] = value
        elif key in RUNTIME_LOCKED_FLAGS:
            locked[key] = True
            if value is False:
                warnings.append(f"{key}=false requested but ignored: {RUNTIME_LOCKED_FLAGS[key]}")
        elif key in RUNTIME_PARAMETER_FLAGS:
            runtime_parameters[key] = value
        elif key in METADATA_ONLY_FLAGS:
            metadata_only[key] = value
            warnings.append(f"{key} is metadata-only: {METADATA_ONLY_FLAGS[key]}")
        else:
            unknown[key] = value
            warnings.append(f"{key} is not a recognized ablation flag and has no runtime effect.")

    return {
        "runtime_enforced": enforced,
        "runtime_locked": locked,
        "runtime_parameters": runtime_parameters,
        "metadata_only": metadata_only,
        "unknown": unknown,
        "warnings": warnings,
    }
