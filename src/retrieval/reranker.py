from __future__ import annotations

from src.retrieval.retrieval_scorer import RetrievedExample


class IdentityReranker:
    """Placeholder reranker that preserves hybrid ranking.

    A model-backed reranker can replace this without changing callers.
    """

    def rerank(self, examples: list[RetrievedExample], top_k: int | None = None) -> list[RetrievedExample]:
        ranked = sorted(examples, key=lambda item: item.score, reverse=True)
        return ranked[:top_k] if top_k is not None else ranked
