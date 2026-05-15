from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from pathlib import Path

from src.config.paths import MODELS_DIR
from src.retrieval.bm25_index import tokenize


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    denom = norm_a * norm_b
    if denom == 0:
        return 0.0
    return float(dot / denom)


@dataclass(frozen=True)
class EmbeddingConfig:
    model_path: str | Path | None = None
    fallback_dimensions: int = 384
    normalize_embeddings: bool = True


class EmbeddingModel:
    """Lazy embedding wrapper with a deterministic local fallback.

    The fallback keeps retrieval tests and index building usable even when
    SentenceTransformers or a local model path is unavailable.
    """

    def __init__(self, config: EmbeddingConfig | None = None) -> None:
        self.config = config or EmbeddingConfig(
            model_path=os.getenv(
                "VTD_EMBEDDING_MODEL_PATH",
                str(MODELS_DIR / "embeddings" / "intfloat__multilingual-e5-small"),
            )
        )
        self._model = None
        self.backend = "hash"

    def _load_model(self) -> None:
        if self._model is not None:
            return
        model_path = self.config.model_path
        if not model_path:
            return
        try:
            from sentence_transformers import SentenceTransformer

            path = Path(model_path)
            if path.exists():
                self._model = SentenceTransformer(str(path))
                self.backend = "sentence_transformers"
        except Exception:
            self._model = None
            self.backend = "hash"

    def _hash_embedding(self, text: str) -> list[float]:
        vec = [0.0 for _ in range(self.config.fallback_dimensions)]
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.config.fallback_dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(value * value for value in vec))
        if norm > 0:
            vec = [value / norm for value in vec]
        return vec

    def encode(self, texts: list[str] | str) -> list[float] | list[list[float]]:
        single = isinstance(texts, str)
        items = [texts] if single else list(texts)
        self._load_model()
        if self._model is not None:
            vectors = self._model.encode(
                items,
                normalize_embeddings=self.config.normalize_embeddings,
                show_progress_bar=False,
            )
            arr = [list(map(float, vector)) for vector in vectors]
        else:
            arr = [self._hash_embedding(item) for item in items]
        return arr[0] if single else arr
