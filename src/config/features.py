from __future__ import annotations

# Execution-ready defaults for Phase 0 / Phase 1.
# Keep advanced research features disabled until the deterministic foundation passes.

ENABLE_VALUE_LINKING: bool = True
ENABLE_CAG: bool = True
ENABLE_LANGGRAPH: bool = False
ENABLE_REFLEXION: bool = False
ENABLE_CONSISTENCY_ABSTENTION: bool = True
ENABLE_EDGE_RUNTIME: bool = False

# Additional gates
ENABLE_SCHEMA_FREEZE_CHECK: bool = True
ENABLE_READ_ONLY_EXECUTION_ONLY: bool = True
ENABLE_ERROR_DISCLOSURE: bool = True
ENABLE_HUMAN_AGREEMENT_TRACKING: bool = True

# Research features to enable later through benchmark configs, not by default.
ENABLE_MULTI_CANDIDATE_GENERATION: bool = True
ENABLE_SQL_SURGEON: bool = True
ENABLE_SEMANTIC_CRITIC: bool = True
ENABLE_RERANKER: bool = True
ENABLE_VECTOR_RETRIEVAL: bool = True
ENABLE_BM25_RETRIEVAL: bool = True

# Etude-mining additions (docs/IMPROVEMENT_IDEAS_FROM_VTD_COLLECTION.md).
# Default-off until each passes its own ablation gate.
SIMPLICITY_FIRST_PROMPT: bool = True
REPAIR_CORRECTION_KB: bool = True


def preset_minimal() -> dict[str, bool]:
    """Deterministic-only baseline for A/B ablations."""
    return {
        "ENABLE_VALUE_LINKING": False,
        "ENABLE_CAG": False,
        "ENABLE_LANGGRAPH": False,
        "ENABLE_REFLEXION": False,
        "ENABLE_CONSISTENCY_ABSTENTION": True,
        "ENABLE_MULTI_CANDIDATE_GENERATION": False,
        "ENABLE_SQL_SURGEON": False,
        "ENABLE_SEMANTIC_CRITIC": False,
        "ENABLE_RERANKER": False,
        "ENABLE_VECTOR_RETRIEVAL": False,
        "ENABLE_BM25_RETRIEVAL": False,
        "SIMPLICITY_FIRST_PROMPT": False,
        "REPAIR_CORRECTION_KB": False,
    }


def preset_default() -> dict[str, bool]:
    """Current shipped defaults."""
    return {
        name: value
        for name, value in globals().items()
        if name.startswith(("ENABLE_", "SIMPLICITY_", "REPAIR_")) and isinstance(value, bool)
    }


def preset_full() -> dict[str, bool]:
    """Everything on, for upper-bound diagnostics."""
    config = dict(preset_default())
    config.update(
        {
            "ENABLE_LANGGRAPH": True,
            "ENABLE_REFLEXION": True,
            "ENABLE_VALUE_LINKING": True,
            "ENABLE_CAG": True,
            "ENABLE_MULTI_CANDIDATE_GENERATION": True,
            "ENABLE_SQL_SURGEON": True,
            "ENABLE_SEMANTIC_CRITIC": True,
            "ENABLE_RERANKER": True,
            "ENABLE_VECTOR_RETRIEVAL": True,
            "ENABLE_BM25_RETRIEVAL": True,
            "SIMPLICITY_FIRST_PROMPT": True,
            "REPAIR_CORRECTION_KB": True,
        }
    )
    return config
