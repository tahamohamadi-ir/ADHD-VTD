from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.config.paths import MODELS_DIR
from src.retrieval.retrieval_scorer import RetrievedExample

logger = logging.getLogger(__name__)

RERANKER_LOCAL_DIRS: dict[str, str] = {
    "bge-reranker-base": str(Path("reranker") / "bge-reranker-base"),
    "bge-reranker-v2-m3": str(Path("rerankers") / "BAAI__bge-reranker-v2-m3"),
}

MODEL_BACKED_RERANKER_NAMES = {"bge-reranker-base", "bge-reranker-v2-m3"}


class IdentityReranker:
    """Placeholder reranker that preserves hybrid ranking.

    A model-backed reranker can replace this without changing callers.
    """

    def rerank(
        self,
        examples: list[RetrievedExample],
        top_k: int | None = None,
        *,
        query: str | None = None,
    ) -> list[RetrievedExample]:
        ranked = sorted(examples, key=lambda item: item.score, reverse=True)
        return ranked[:top_k] if top_k is not None else ranked


def _example_text(example: RetrievedExample) -> str:
    record = example.record or {}
    for key in ("question", "question_fa", "text", "sql"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return example.id


class CrossEncoderReranker:
    """Model-backed cross-encoder reranker.

    Weights are loaded lazily on first ``predict``/``rerank`` call so that
    constructing the object (and unit tests) never imports heavy deps.
    """

    def __init__(
        self,
        model_name: str,
        model_dir: Path | None = None,
        batch_size: int = 16,
        max_length: int = 512,
    ) -> None:
        self.model_name = model_name
        resolved = model_dir
        if resolved is None:
            relative = RERANKER_LOCAL_DIRS.get(model_name)
            if relative is not None:
                candidate = MODELS_DIR / relative
                if candidate.is_dir():
                    resolved = candidate
        self.model_dir: Path | None = Path(resolved) if resolved is not None else None
        self.batch_size = batch_size
        self.max_length = max_length
        self._model: Any = None

    @property
    def uses_local_dir(self) -> bool:
        return self.model_dir is not None

    def _create_cross_encoder(self, model_path: str) -> Any:
        from sentence_transformers import CrossEncoder

        return CrossEncoder(model_path, max_length=self.max_length)

    def _ensure_model(self) -> Any:
        if self._model is None:
            model_path = str(self.model_dir) if self.model_dir else self.model_name
            self._model = self._create_cross_encoder(model_path)
        return self._model

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        if not pairs:
            return []
        model = self._ensure_model()
        scores = model.predict(pairs, batch_size=self.batch_size)
        return [float(score) for score in scores]

    def rerank(
        self,
        examples: list[RetrievedExample],
        top_k: int | None = None,
        *,
        query: str | None = None,
    ) -> list[RetrievedExample]:
        if not examples:
            return []
        query_text = (query or "").strip()
        scored_examples: list[tuple[float, RetrievedExample]] = []
        if query_text:
            pairs = [(query_text, _example_text(example)) for example in examples]
            predictions = self.predict(pairs)
            scored_examples = list(zip(predictions, examples))
        else:
            scored_examples = [(example.score, example) for example in examples]
        scored_examples.sort(key=lambda pair: pair[0], reverse=True)
        ranked = [example for _, example in scored_examples]
        return ranked[:top_k] if top_k is not None else ranked


def is_model_backed_reranker(obj: object) -> bool:
    return isinstance(obj, CrossEncoderReranker)


def create_reranker(name: str | None) -> IdentityReranker | CrossEncoderReranker:
    normalized = (name or "none").strip().lower()
    if normalized in {"", "none", "identity"}:
        return IdentityReranker()
    if normalized in MODEL_BACKED_RERANKER_NAMES:
        reranker = CrossEncoderReranker(normalized)
        if reranker.uses_local_dir:
            return reranker
        logger.warning("local_reranker_model_missing_falling_back_to_identity name=%s", normalized)
        return IdentityReranker()
    logger.warning("unknown_reranker_name_falling_back_to_identity name=%s", normalized)
    return IdentityReranker()


def resolve_reranker_backend(name: str | None) -> str | None:
    normalized = (name or "").strip().lower()
    if normalized in {"", "none"}:
        return None
    if normalized == "identity":
        return "identity"
    if normalized in MODEL_BACKED_RERANKER_NAMES:
        reranker = CrossEncoderReranker(normalized)
        return "cross_encoder" if reranker.uses_local_dir else "identity"
    return "identity"
