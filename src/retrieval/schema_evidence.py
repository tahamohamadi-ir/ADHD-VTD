from __future__ import annotations

from src.retrieval.retrieval_scorer import RetrievedExample


def ensure_schema_evidence_after_filter(
    retrieved: list[RetrievedExample],
    *,
    top_k: int,
) -> list[RetrievedExample]:
    top = retrieved[:top_k]
    if not top or any(item.schema_overlap_score > 0 for item in top):
        return retrieved
    schema_candidates = [item for item in retrieved[top_k:] if item.schema_overlap_score > 0]
    if not schema_candidates:
        return retrieved
    best_schema = max(schema_candidates, key=lambda item: (item.schema_overlap_score, item.score))
    adjusted = [item for item in retrieved if item.id != best_schema.id]
    insert_at = min(max(top_k - 1, 0), len(adjusted))
    adjusted.insert(insert_at, best_schema)
    return adjusted
