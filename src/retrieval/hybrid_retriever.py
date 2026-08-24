from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.config.paths import INDEXED_EXAMPLES_PATH, RAG_DIR
from src.retrieval.bm25_index import BM25Index
from src.retrieval.chroma_store import ChromaStore
from src.retrieval.retrieval_scorer import (
    RetrievedExample,
    RetrievalQuery,
    RetrievalScorer,
    normalize_scores,
)
from src.utils.jsonl import read_jsonl


@dataclass
class HybridRetriever:
    indexed_examples_path: Path = INDEXED_EXAMPLES_PATH
    bm25_index_path: Path = field(default_factory=lambda: RAG_DIR / "bm25" / "bm25_index.json")
    use_vector_store: bool = True
    retrieval_mode: str | None = None
    scorer: RetrievalScorer = field(default_factory=RetrievalScorer)

    def __post_init__(self) -> None:
        self.indexed_examples_path = Path(self.indexed_examples_path)
        self.records = read_jsonl(self.indexed_examples_path)
        if self.retrieval_mode is None:
            self.retrieval_mode = "hybrid" if self.use_vector_store else "bm25"
        if self.retrieval_mode not in {"bm25", "vector", "hybrid"}:
            raise ValueError(f"Unsupported retrieval_mode: {self.retrieval_mode}")
        self.use_vector_store = self.retrieval_mode in {"vector", "hybrid"}
        self._bm25: BM25Index | None = None
        self._vector_store: ChromaStore | None = None

    @property
    def bm25(self) -> BM25Index:
        if self._bm25 is None:
            if self.bm25_index_path.exists():
                self._bm25 = BM25Index.load(self.bm25_index_path)
            else:
                self._bm25 = BM25Index.from_records(self.records)
        return self._bm25

    @property
    def vector_store(self) -> ChromaStore:
        if self._vector_store is None:
            self._vector_store = ChromaStore()
            if not self._vector_store.fallback_path.exists() and self.records:
                self._vector_store.build(self.records)
        return self._vector_store

    def retrieve(
        self,
        query: str | RetrievalQuery,
        *,
        top_k: int = 5,
        candidate_pool_size: int = 25,
    ) -> list[RetrievedExample]:
        retrieval_query = query if isinstance(query, RetrievalQuery) else RetrievalQuery(text=query)

        lexical_scores: dict[str, float] = {}
        if self.retrieval_mode in {"bm25", "hybrid"}:
            lexical_raw = self.bm25.score(retrieval_query.text)
            lexical_scores = normalize_scores(lexical_raw)

        semantic_raw: dict[str, float] = {}
        if self.retrieval_mode in {"vector", "hybrid"}:
            for item in self.vector_store.search(retrieval_query.text, top_k=candidate_pool_size):
                record_id = str(item.record.get("id"))
                semantic_raw[record_id] = item.score
        semantic_scores = normalize_scores(semantic_raw)

        candidate_ids = set(lexical_scores) | set(semantic_scores)
        if not candidate_ids:
            candidate_ids = {str(record.get("id", idx)) for idx, record in enumerate(self.records)}

        records_by_id = {
            str(record.get("id", idx)): record for idx, record in enumerate(self.records)
        }
        scored: list[RetrievedExample] = []
        for record_id in candidate_ids:
            record = records_by_id.get(record_id)
            if not record:
                continue
            scored.append(
                self.scorer.score(
                    retrieval_query,
                    record,
                    lexical_score=lexical_scores.get(record_id, 0.0),
                    semantic_score=semantic_scores.get(record_id, 0.0),
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        selected = self._diversify(scored, top_k=top_k)
        return self._ensure_schema_evidence(selected, scored, retrieval_query)

    def _ensure_schema_evidence(
        self,
        selected: list[RetrievedExample],
        candidates: list[RetrievedExample],
        query: RetrievalQuery,
    ) -> list[RetrievedExample]:
        if not selected or not (query.tables or query.columns):
            return selected
        if any(item.schema_overlap_score > 0 for item in selected):
            return selected
        schema_candidates = [item for item in candidates if item.schema_overlap_score > 0]
        if not schema_candidates:
            return selected
        best_schema = max(
            schema_candidates, key=lambda item: (item.schema_overlap_score, item.score)
        )
        if best_schema.id in {item.id for item in selected}:
            return selected
        adjusted = list(selected)
        adjusted[-1] = best_schema
        adjusted.sort(key=lambda item: item.score, reverse=True)
        return adjusted

    def _diversify(self, examples: list[RetrievedExample], top_k: int) -> list[RetrievedExample]:
        selected: list[RetrievedExample] = []
        skeleton_counts: dict[str, int] = {}
        table_set_counts: dict[str, int] = {}

        for example in examples:
            record = example.record
            skeleton = str(record.get("skeleton") or record.get("sql_skeleton") or "")
            tables = "|".join(sorted(str(t) for t in record.get("tables", [])))
            if skeleton and skeleton_counts.get(skeleton, 0) >= 2:
                continue
            if tables and table_set_counts.get(tables, 0) >= 2:
                continue
            selected.append(example)
            if skeleton:
                skeleton_counts[skeleton] = skeleton_counts.get(skeleton, 0) + 1
            if tables:
                table_set_counts[tables] = table_set_counts.get(tables, 0) + 1
            if len(selected) >= top_k:
                break

        if len(selected) < top_k:
            seen = {item.id for item in selected}
            for example in examples:
                if example.id not in seen:
                    selected.append(example)
                    if len(selected) >= top_k:
                        break
        return selected
