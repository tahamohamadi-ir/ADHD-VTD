from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RetrievalMetricSummary:
    total: int
    schema_recall_at_k: float
    intent_match_at_k: float
    skeleton_match_at_k: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "schema_recall_at_k": self.schema_recall_at_k,
            "intent_match_at_k": self.intent_match_at_k,
            "skeleton_match_at_k": self.skeleton_match_at_k,
        }


def _overlap(expected: list[str], retrieved: list[str]) -> bool:
    expected_set = {str(item).lower() for item in expected if str(item).strip()}
    retrieved_set = {str(item).lower() for item in retrieved if str(item).strip()}
    if not expected_set:
        return False
    return bool(expected_set & retrieved_set)


def summarize_retrieval(records: list[dict[str, Any]]) -> RetrievalMetricSummary:
    if not records:
        return RetrievalMetricSummary(0, 0.0, 0.0, 0.0)

    schema_hits = 0
    intent_hits = 0
    skeleton_hits = 0

    for row in records:
        expected_tables = row.get("expected_tables", [])
        expected_columns = row.get("expected_columns", [])
        expected_intent = row.get("expected_intent")
        expected_skeleton = row.get("expected_skeleton")
        retrieved = row.get("retrieved", [])

        retrieved_tables: list[str] = []
        retrieved_columns: list[str] = []
        retrieved_intents: list[str] = []
        retrieved_skeletons: list[str] = []

        for item in retrieved:
            record = item.get("record", item)
            retrieved_tables.extend(record.get("tables", []))
            retrieved_columns.extend(record.get("columns", []))
            if record.get("intent"):
                retrieved_intents.append(record["intent"])
            if record.get("skeleton") or record.get("sql_skeleton"):
                retrieved_skeletons.append(record.get("skeleton") or record.get("sql_skeleton"))

        if _overlap(expected_tables, retrieved_tables) or _overlap(
            expected_columns, retrieved_columns
        ):
            schema_hits += 1
        if expected_intent and expected_intent in retrieved_intents:
            intent_hits += 1
        if expected_skeleton and expected_skeleton in retrieved_skeletons:
            skeleton_hits += 1

    total = len(records)
    return RetrievalMetricSummary(
        total=total,
        schema_recall_at_k=schema_hits / total,
        intent_match_at_k=intent_hits / total,
        skeleton_match_at_k=skeleton_hits / total,
    )
