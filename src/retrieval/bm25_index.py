from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.nlu.persian_normalizer import PersianNormalizer


TOKEN_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    normalized = PersianNormalizer(enable_colloquial_mapping=True).normalize_text(text or "")
    return [token.lower() for token in TOKEN_RE.findall(normalized) if token.strip()]


@dataclass
class BM25SearchResult:
    record: dict[str, Any]
    score: float


@dataclass
class BM25Index:
    records: list[dict[str, Any]] = field(default_factory=list)
    tokenized_docs: list[list[str]] = field(default_factory=list)
    text_field: str = "text_for_embedding"

    def __post_init__(self) -> None:
        if self.records and not self.tokenized_docs:
            self.tokenized_docs = [tokenize(self._record_text(record)) for record in self.records]
        self._bm25 = self._build_rank_bm25()
        self._idf = self._build_idf()

    @classmethod
    def from_records(cls, records: list[dict[str, Any]], text_field: str = "text_for_embedding") -> "BM25Index":
        return cls(records=records, text_field=text_field)

    def _record_text(self, record: dict[str, Any]) -> str:
        return str(record.get(self.text_field) or record.get("question_fa") or "")

    def _build_rank_bm25(self) -> Any | None:
        try:
            from rank_bm25 import BM25Okapi

            if self.tokenized_docs:
                return BM25Okapi(self.tokenized_docs)
        except Exception:
            return None
        return None

    def _build_idf(self) -> dict[str, float]:
        doc_count = len(self.tokenized_docs)
        if doc_count == 0:
            return {}
        df: dict[str, int] = {}
        for doc in self.tokenized_docs:
            for token in set(doc):
                df[token] = df.get(token, 0) + 1
        return {
            token: math.log((doc_count - freq + 0.5) / (freq + 0.5) + 1.0)
            for token, freq in df.items()
        }

    def _fallback_scores(self, query_tokens: list[str]) -> list[float]:
        if not query_tokens:
            return [0.0 for _ in self.records]
        query_set = set(query_tokens)
        scores: list[float] = []
        for doc in self.tokenized_docs:
            doc_counts: dict[str, int] = {}
            for token in doc:
                doc_counts[token] = doc_counts.get(token, 0) + 1
            score = 0.0
            for token in query_set:
                if token in doc_counts:
                    score += self._idf.get(token, 1.0) * doc_counts[token]
            scores.append(score)
        return scores

    def score(self, query: str) -> dict[str, float]:
        query_tokens = tokenize(query)
        if self._bm25 is not None:
            raw_scores = list(self._bm25.get_scores(query_tokens))
        else:
            raw_scores = self._fallback_scores(query_tokens)
        return {
            str(record.get("id", idx)): float(score)
            for idx, (record, score) in enumerate(zip(self.records, raw_scores))
        }

    def search(self, query: str, top_k: int = 5) -> list[BM25SearchResult]:
        scores = self.score(query)
        by_id = {str(record.get("id", idx)): record for idx, record in enumerate(self.records)}
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [BM25SearchResult(record=by_id[record_id], score=score) for record_id, score in ranked]

    def save(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "text_field": self.text_field,
            "records": self.records,
            "tokenized_docs": self.tokenized_docs,
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path

    @classmethod
    def load(cls, path: str | Path) -> "BM25Index":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            records=list(payload.get("records", [])),
            tokenized_docs=list(payload.get("tokenized_docs", [])),
            text_field=str(payload.get("text_field", "text_for_embedding")),
        )
