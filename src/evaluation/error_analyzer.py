from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(slots=True)
class ErrorAnalysis:
    total_errors: int
    by_error: dict[str, int]
    by_difficulty: dict[str, int]
    by_category: dict[str, int]
    examples: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_errors": self.total_errors,
            "by_error": self.by_error,
            "by_difficulty": self.by_difficulty,
            "by_category": self.by_category,
            "examples": self.examples,
        }


def analyze_errors(records: Iterable[dict[str, Any]], *, max_examples: int = 20) -> ErrorAnalysis:
    rows = list(records)
    error_rows = [r for r in rows if not (r.get("ok") or r.get("execution_correct") or r.get("result_match"))]
    by_error: Counter[str] = Counter()
    by_difficulty: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    for r in error_rows:
        error = str(r.get("error") or r.get("error_type") or "UNKNOWN_ERROR")
        by_error[error] += 1
        by_difficulty[str(r.get("difficulty", "unknown"))] += 1
        by_category[str(r.get("category", "unknown"))] += 1
        if len(examples) < max_examples:
            examples.append({
                "id": r.get("audit_id") or r.get("id") or r.get("source_id"),
                "question": r.get("question_fa") or r.get("question"),
                "error": error,
                "sql": r.get("sql") or r.get("gold_sql") or r.get("generated_sql"),
            })
    return ErrorAnalysis(
        total_errors=len(error_rows),
        by_error=dict(by_error.most_common()),
        by_difficulty=dict(by_difficulty.most_common()),
        by_category=dict(by_category.most_common()),
        examples=examples,
    )
