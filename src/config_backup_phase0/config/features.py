from __future__ import annotations

# Execution-ready defaults for Phase 0 / Phase 1.
# Keep advanced research features disabled until the deterministic foundation passes.

ENABLE_VALUE_LINKING: bool = True
ENABLE_CAG: bool = False
ENABLE_LANGGRAPH: bool = False
ENABLE_REFLEXION: bool = False
ENABLE_CONSISTENCY_ABSTENTION: bool = False
ENABLE_EDGE_RUNTIME: bool = False

# Additional gates
ENABLE_SCHEMA_FREEZE_CHECK: bool = True
ENABLE_READ_ONLY_EXECUTION_ONLY: bool = True
ENABLE_ERROR_DISCLOSURE: bool = True
ENABLE_HUMAN_AGREEMENT_TRACKING: bool = True

# Research features to enable later through benchmark configs, not by default.
ENABLE_MULTI_CANDIDATE_GENERATION: bool = False
ENABLE_SQL_SURGEON: bool = False
ENABLE_SEMANTIC_CRITIC: bool = False
ENABLE_RERANKER: bool = False
ENABLE_VECTOR_RETRIEVAL: bool = False
ENABLE_BM25_RETRIEVAL: bool = False
