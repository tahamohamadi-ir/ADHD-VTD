from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievalWeights:
    semantic: float = 0.30
    lexical: float = 0.25
    schema_overlap: float = 0.20
    intent_match: float = 0.15
    skeleton_match: float = 0.10


@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    intent: str | None = None
    tables: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    skeleton: str | None = None


@dataclass
class RetrievedExample:
    record: dict[str, Any]
    score: float
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    schema_overlap_score: float = 0.0
    intent_match_score: float = 0.0
    skeleton_match_score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return str(self.record.get("id", ""))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "score": round(self.score, 6),
            "lexical_score": round(self.lexical_score, 6),
            "semantic_score": round(self.semantic_score, 6),
            "schema_overlap_score": round(self.schema_overlap_score, 6),
            "intent_match_score": round(self.intent_match_score, 6),
            "skeleton_match_score": round(self.skeleton_match_score, 6),
            "reasons": self.reasons,
            "record": self.record,
        }


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    max_score = max(scores.values())
    if max_score <= 0:
        return {key: 0.0 for key in scores}
    return {key: clamp01(value / max_score) for key, value in scores.items()}


def overlap_score(query_values: list[str], candidate_values: list[str]) -> float:
    query_set = {str(v).lower() for v in query_values if str(v).strip()}
    candidate_set = {str(v).lower() for v in candidate_values if str(v).strip()}
    if not query_set:
        return 0.0
    return len(query_set & candidate_set) / len(query_set)


def skeleton_match_score(query_skeleton: str | None, candidate_skeleton: str | None) -> float:
    if not query_skeleton or not candidate_skeleton:
        return 0.0
    q = " ".join(query_skeleton.lower().split())
    c = " ".join(candidate_skeleton.lower().split())
    if q == c:
        return 1.0
    q_tokens = set(q.replace("...", " ").split())
    c_tokens = set(c.replace("...", " ").split())
    if not q_tokens:
        return 0.0
    return len(q_tokens & c_tokens) / len(q_tokens)


class RetrievalScorer:
    def __init__(self, weights: RetrievalWeights | None = None) -> None:
        self.weights = weights or RetrievalWeights()

    def score(
        self,
        query: RetrievalQuery,
        record: dict[str, Any],
        *,
        lexical_score: float = 0.0,
        semantic_score: float = 0.0,
    ) -> RetrievedExample:
        candidate_tables = [str(v) for v in record.get("tables", [])]
        candidate_columns = [str(v) for v in record.get("columns", [])]
        candidate_intent = record.get("intent")
        candidate_skeleton = record.get("skeleton") or record.get("sql_skeleton")

        schema_overlap = max(
            overlap_score(query.tables, candidate_tables),
            overlap_score(query.columns, candidate_columns),
        )
        intent_match = 1.0 if query.intent and candidate_intent == query.intent else 0.0
        skeleton_match = skeleton_match_score(query.skeleton, candidate_skeleton)

        total = (
            self.weights.semantic * clamp01(semantic_score)
            + self.weights.lexical * clamp01(lexical_score)
            + self.weights.schema_overlap * clamp01(schema_overlap)
            + self.weights.intent_match * intent_match
            + self.weights.skeleton_match * skeleton_match
        )

        reasons: list[str] = []
        if lexical_score > 0:
            reasons.append("lexical")
        if semantic_score > 0:
            reasons.append("semantic")
        if schema_overlap > 0:
            reasons.append("schema_overlap")
        if intent_match:
            reasons.append("intent")
        if skeleton_match:
            reasons.append("skeleton")

        return RetrievedExample(
            record=record,
            score=total,
            lexical_score=lexical_score,
            semantic_score=semantic_score,
            schema_overlap_score=schema_overlap,
            intent_match_score=intent_match,
            skeleton_match_score=skeleton_match,
            reasons=reasons,
        )
