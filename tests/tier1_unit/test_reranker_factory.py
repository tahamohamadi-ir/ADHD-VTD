from __future__ import annotations

import logging
import sys

from src.retrieval import reranker as reranker_module
from src.retrieval.reranker import (
    CrossEncoderReranker,
    IdentityReranker,
    create_reranker,
    resolve_reranker_backend,
)
from src.retrieval.retrieval_scorer import RetrievedExample


def _example(example_id: str, score: float, question: str) -> RetrievedExample:
    return RetrievedExample(
        record={"id": example_id, "question": question, "tables": [], "columns": []},
        score=score,
    )


class _StubCrossEncoder:
    def __init__(self, scores: list[float]) -> None:
        self._scores = scores

    def predict(self, pairs, batch_size: int = 16):
        return self._scores[: len(pairs)]


def test_factory_maps_none_and_identity_to_identity():
    assert isinstance(create_reranker(None), IdentityReranker)
    assert isinstance(create_reranker("none"), IdentityReranker)
    assert isinstance(create_reranker("identity"), IdentityReranker)


def test_cross_encoder_construction_is_lazy_and_uses_local_dir(tmp_path):
    model_dir = tmp_path / "bge-reranker-base"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}", encoding="utf-8")

    reranker = CrossEncoderReranker("bge-reranker-base", model_dir=model_dir)

    assert reranker.uses_local_dir is True
    assert "sentence_transformers" not in sys.modules


def test_cross_encoder_rerank_orders_by_model_scores(tmp_path, monkeypatch):
    reranker = CrossEncoderReranker("bge-reranker-base", model_dir=tmp_path)
    monkeypatch.setattr(
        reranker,
        "_create_cross_encoder",
        lambda model_path: _StubCrossEncoder([0.1, 0.9, 0.5]),
        raising=True,
    )
    examples = [
        _example("a", 0.9, "q1"),
        _example("b", 0.8, "q2"),
        _example("c", 0.7, "q3"),
    ]

    ranked = reranker.rerank(examples, top_k=2, query="تعداد دانشجوها")

    assert [item.id for item in ranked] == ["b", "c"]


def test_cross_encoder_falls_back_to_hybrid_score_without_query(tmp_path, monkeypatch):
    reranker = CrossEncoderReranker("bge-reranker-base", model_dir=tmp_path)
    monkeypatch.setattr(
        reranker,
        "_create_cross_encoder",
        lambda model_path: _StubCrossEncoder([]),
        raising=True,
    )
    examples = [_example("low", 0.2, "x"), _example("high", 0.8, "y")]

    ranked = reranker.rerank(examples, top_k=None)

    assert [item.id for item in ranked] == ["high", "low"]


def test_factory_falls_back_to_identity_when_local_model_missing(tmp_path, caplog, monkeypatch):
    monkey_missing = tmp_path / "models"
    monkey_missing.mkdir()
    monkeypatch.setattr(reranker_module, "MODELS_DIR", monkey_missing)
    with caplog.at_level(logging.WARNING, logger="src.retrieval.reranker"):
        resolved = create_reranker("bge-reranker-v2-m3")

    assert isinstance(resolved, IdentityReranker)
    assert any("local_reranker_model_missing" in record.message for record in caplog.records)


def test_resolve_reranker_backend_reports_availability(tmp_path, monkeypatch):
    assert resolve_reranker_backend(None) is None
    assert resolve_reranker_backend("none") is None
    assert resolve_reranker_backend("identity") == "identity"

    local_dir = tmp_path / "reranker" / "bge-reranker-base"
    local_dir.mkdir(parents=True)
    monkeypatch.setattr(reranker_module, "MODELS_DIR", tmp_path)
    assert resolve_reranker_backend("bge-reranker-base") == "cross_encoder"
    missing_dir = tmp_path / "empty"
    missing_dir.mkdir()
    monkeypatch.setattr(reranker_module, "MODELS_DIR", missing_dir)
    assert resolve_reranker_backend("bge-reranker-base") == "identity"


def test_identity_reranker_accepts_query_keyword_for_signature_compat():
    reranker = IdentityReranker()
    examples = [_example("a", 0.3, "q"), _example("b", 0.6, "q")]

    ranked = reranker.rerank(examples, top_k=1, query="anything")

    assert [item.id for item in ranked] == ["b"]
