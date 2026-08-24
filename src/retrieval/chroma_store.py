from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from src.config.paths import RAG_DIR
from src.retrieval.embedding_model import EmbeddingModel, cosine_similarity


@dataclass
class VectorSearchResult:
    record: dict[str, Any]
    score: float


@dataclass
class ChromaStore:
    """Persistent vector example store with ChromaDB and JSON fallback.

    The class intentionally exposes a small API used by HybridRetriever. It can
    use a real ChromaDB persistent collection when the optional dependency is
    available, and always falls back to a deterministic JSON vector store.
    """

    persist_dir: Path = field(default_factory=lambda: RAG_DIR / "chroma")
    collection_name: str = "vtd_golden_examples"
    embedding_model: EmbeddingModel = field(default_factory=EmbeddingModel)
    backend: Literal["auto", "chroma", "json"] = "auto"

    def __post_init__(self) -> None:
        self.persist_dir = Path(self.persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.fallback_path = self.persist_dir / "examples_vectors.jsonl"
        self._collection = None
        self.active_backend = self._resolve_backend()

    def _resolve_backend(self) -> str:
        if self.backend == "json":
            return "json"
        try:
            import chromadb  # noqa: F401

            return "chroma"
        except Exception:
            if self.backend == "chroma":
                raise
            return "json"

    def _chroma_collection(self):
        if self._collection is not None:
            return self._collection
        import chromadb

        client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._collection = client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def _encode_one(self, text: str) -> list[float]:
        vector = self.embedding_model.encode(text)
        if hasattr(vector, "tolist"):
            vector = vector.tolist()
        return [float(value) for value in vector]

    def _record_id(self, record: dict[str, Any], index: int) -> str:
        return str(record.get("id") or record.get("source_id") or f"record_{index}")

    def build(self, records: list[dict[str, Any]]) -> Path:
        if self.active_backend == "chroma":
            return self._build_chroma(records)
        return self._build_json(records)

    def _build_chroma(self, records: list[dict[str, Any]]) -> Path:
        collection = self._chroma_collection()
        ids: list[str] = []
        documents: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, str]] = []
        for index, record in enumerate(records):
            text = str(
                record.get("text_for_embedding")
                or record.get("question_fa")
                or record.get("question")
                or ""
            )
            ids.append(self._record_id(record, index))
            documents.append(text)
            embeddings.append(self._encode_one(text))
            metadatas.append({"record_json": json.dumps(record, ensure_ascii=False)})

        if ids:
            collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        return self.persist_dir

    def _build_json(self, records: list[dict[str, Any]]) -> Path:
        rows: list[dict[str, Any]] = []
        for record in records:
            text = str(record.get("text_for_embedding") or record.get("question_fa") or "")
            vector = self._encode_one(text)
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
        if self.active_backend == "chroma":
            return self._search_chroma(query, top_k=top_k)
        return self._search_json(query, top_k=top_k)

    def _search_chroma(self, query: str, top_k: int = 5) -> list[VectorSearchResult]:
        collection = self._chroma_collection()
        if collection.count() == 0:
            return []
        query_vector = self._encode_one(query)
        raw = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["metadatas", "distances"],
        )
        results: list[VectorSearchResult] = []
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        for metadata, distance in zip(metadatas, distances):
            record = json.loads(metadata.get("record_json", "{}"))
            score = max(0.0, 1.0 - float(distance))
            results.append(VectorSearchResult(record=record, score=score))
        return results

    def _search_json(self, query: str, top_k: int = 5) -> list[VectorSearchResult]:
        query_vector = self._encode_one(query)
        results: list[VectorSearchResult] = []
        for row in self._load_rows():
            vector = [float(value) for value in row.get("embedding", [])]
            score = cosine_similarity(query_vector, vector)
            results.append(VectorSearchResult(record=row["record"], score=score))
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]
