from __future__ import annotations

from src.retrieval.retrieval_scorer import RetrievedExample
from src.retrieval.schema_evidence import ensure_schema_evidence_after_filter


def _example(record_id: str, *, score: float, schema_overlap: float = 0.0) -> RetrievedExample:
    return RetrievedExample(
        record={"id": record_id, "tables": ["target_table"] if schema_overlap else ["other_table"]},
        score=score,
        schema_overlap_score=schema_overlap,
    )


def test_schema_evidence_is_preserved_after_self_overlap_filtering_before_top_k_slice():
    ranked = [
        _example("wrong_1", score=0.9),
        _example("wrong_2", score=0.8),
        _example("wrong_3", score=0.7),
        _example("right_schema", score=0.2, schema_overlap=1.0),
    ]

    adjusted = ensure_schema_evidence_after_filter(ranked, top_k=3)

    assert [item.id for item in adjusted[:3]] == ["wrong_1", "wrong_2", "right_schema"]
