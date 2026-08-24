from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from scripts.run_benchmark import apply_agent_retrieval_overrides  # noqa: E402
from src.graph.nodes import base_nodes  # noqa: E402
from src.retrieval.reranker import IdentityReranker  # noqa: E402


class _RecordingRetriever:
    last_kwargs: dict | None = None

    def __init__(self, **kwargs) -> None:
        type(self).last_kwargs = kwargs

    def retrieve(self, query, *, top_k=5, candidate_pool_size=25):
        return []


def test_apply_agent_retrieval_overrides_noop_without_flags():
    config = {"cag": True}

    result = apply_agent_retrieval_overrides(config, retrieval_backend=None, reranker_name=None)

    assert result is config
    assert result == {"cag": True}


def test_apply_agent_retrieval_overrides_injects_backend_and_reranker():
    result = apply_agent_retrieval_overrides(
        {"deterministic_templates": False},
        retrieval_backend="hybrid_rerank",
        reranker_name="bge-reranker-v2-m3",
    )
    none_reranker = apply_agent_retrieval_overrides(
        {}, retrieval_backend="vector", reranker_name="none"
    )

    assert result["retrieval_backend"] == "hybrid_rerank"
    assert result["reranker"] == "bge-reranker-v2-m3"
    assert none_reranker == {"retrieval_backend": "vector"}


def test_build_agent_retriever_default_path_is_unchanged(monkeypatch):
    monkeypatch.setattr(base_nodes, "HybridRetriever", _RecordingRetriever)

    retriever, active = base_nodes.build_agent_retriever(backend=None, reranker_name=None)

    assert isinstance(retriever, _RecordingRetriever)
    assert _RecordingRetriever.last_kwargs == {"use_vector_store": False}
    assert active is None


def test_build_agent_retriever_honors_vector_backend(monkeypatch):
    _RecordingRetriever.last_kwargs = None
    monkeypatch.setattr(base_nodes, "HybridRetriever", _RecordingRetriever)

    retriever, active = base_nodes.build_agent_retriever(backend="vector", reranker_name=None)

    assert isinstance(retriever, _RecordingRetriever)
    assert _RecordingRetriever.last_kwargs == {"retrieval_mode": "vector"}
    assert active is None


def test_build_agent_retriever_maps_hybrid_rerank_and_attaches_model_reranker(monkeypatch):
    _RecordingRetriever.last_kwargs = None
    monkeypatch.setattr(base_nodes, "HybridRetriever", _RecordingRetriever)
    stub_reranker = object()
    monkeypatch.setattr(
        base_nodes,
        "create_reranker",
        lambda name: stub_reranker if name == "bge-reranker-v2-m3" else IdentityReranker(),
    )
    monkeypatch.setattr(
        base_nodes,
        "is_model_backed_reranker",
        lambda obj: obj is stub_reranker,
        raising=True,
    )

    retriever, active = base_nodes.build_agent_retriever(
        backend="hybrid_rerank", reranker_name="bge-reranker-v2-m3"
    )

    assert _RecordingRetriever.last_kwargs == {"retrieval_mode": "hybrid"}
    assert active is stub_reranker


def test_build_agent_retriever_ignores_identity_placeholder(monkeypatch):
    monkeypatch.setattr(base_nodes, "HybridRetriever", _RecordingRetriever)
    monkeypatch.setattr(
        base_nodes, "create_reranker", lambda name: IdentityReranker(), raising=True
    )

    _, active = base_nodes.build_agent_retriever(backend="bm25", reranker_name="identity")

    assert active is None
