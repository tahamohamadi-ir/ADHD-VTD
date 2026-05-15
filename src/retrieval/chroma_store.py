from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config.paths import RAG_DIR
from src.retrieval.embedding_model import EmbeddingModel, cosine_similarity


@dataclass
class VectorSearchResult:
    record: dict[str, Any]
    score: float


@dataclass
class ChromaStore:
    """Chroma-compatible example store with a JSON fallback.

    The class intentionally exposes a small API used by HybridRetriever. It can
    persist embeddings to a JSON file when ChromaDB is not available.
    """

    persist_dir: Path = field(default_factory=lambda: RAG_DIR / "chroma")
    collection_name: str = "vtd_golden_examples"
    embedding_model: EmbeddingModel = field(default_factory=EmbeddingModel)

    def __post_init__(self) -> None:
        self.persist_dir = Path(self.persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.fallback_path = self.persist_dir / "examples_vectors.jsonl"

    def build(self, records: list[dict[str, Any]]) -> Path:
        rows: list[dict[str, Any]] = []
        for record in records:
            text = str(record.get("text_for_embedding") or record.get("question_fa") or "")
            vector = self.embedding_model.encode(text).tolist()
            rows.append({"record": record, "embedding": vector})
        with self.fallback_path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return self.fallback_path

    def _load_rows(self) -> list[dict[str, Any]]:
        if not self.fallback_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.fallback_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    rows.append(json.loads(stripped))
        return rows

    def search(self, query: str, top_k: int = 5) -> list[VectorSearchResult]:
        query_vector = self.embedding_model.encode(query)
        results: list[VectorSearchResult] = []
        for row in self._load_rows():
            vector = [float(value) for value in row.get("embedding", [])]
            score = cosine_similarity(query_vector, vector)
            results.append(VectorSearchResult(record=row["record"], score=score))
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]
