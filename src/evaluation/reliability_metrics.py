from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from src.evaluation.action_normalizer import did_abstain_for_action, should_abstain_for_action
from src.evaluation.metrics import MetricResult, safe_div


@dataclass(slots=True)
class ReliabilityWeights:
    correct_sql: float = 1.0
    correct_abstention: float = 1.0
    wrong_sql: float = -1.0
    wrong_abstention: float = -0.25
    unsafe_sql: float = -2.0


@dataclass(slots=True)
class ReliabilityScoreResult:
    score: float
    normalized_score: float
    total_cases: int
    correct_sql: int
    correct_abstention: int
    wrong_sql: int
    wrong_abstention: int
    unsafe_sql: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "normalized_score": self.normalized_score,
            "total_cases": self.total_cases,
            "correct_sql": self.correct_sql,
            "correct_abstention": self.correct_abstention,
            "wrong_sql": self.wrong_sql,
            "wrong_abstention": self.wrong_abstention,
            "unsafe_sql": self.unsafe_sql,
        }


def should_abstain(record: dict[str, Any]) -> bool:
    if record.get("should_abstain") is True:
        return True
    return should_abstain_for_action(
        record.get("expected_action"),
        should_generate_sql=record.get("should_generate_sql"),
    )


def did_abstain(record: dict[str, Any]) -> bool:
    if record.get("abstained") is True:
        return True
    return did_abstain_for_action(record.get("actual_action"))


def is_sql_correct(record: dict[str, Any]) -> bool:
    return bool(record.get("execution_correct") or record.get("result_match") or record.get("ok"))


def is_unsafe_sql(record: dict[str, Any]) -> bool:
    return bool(
        record.get("unsafe_sql_generated")
        or record.get("unsafe_sql")
        or record.get("safety_violation")
    )


def reliability_score(
    records: Iterable[dict[str, Any]], weights: ReliabilityWeights | None = None
) -> ReliabilityScoreResult:
    w = weights or ReliabilityWeights()
    rows = list(records)
    correct_sql = correct_abstention = wrong_sql = wrong_abstention = unsafe_sql = 0
    score = 0.0

    for r in rows:
        expected_abs = should_abstain(r)
        actual_abs = did_abstain(r)
        if is_unsafe_sql(r):
            unsafe_sql += 1
            score += w.unsafe_sql
            continue
        if expected_abs and actual_abs:
            correct_abstention += 1
            score += w.correct_abstention
        elif expected_abs and not actual_abs:
            wrong_sql += 1
            score += w.wrong_sql
        elif not expected_abs and actual_abs:
            wrong_abstention += 1
            score += w.wrong_abstention
        else:
            if is_sql_correct(r):
                correct_sql += 1
                score += w.correct_sql
            else:
                wrong_sql += 1
                score += w.wrong_sql

    # Map from [-max_penalty, max_reward] to an interpretable 0..1-ish range.
    max_possible = len(rows) * max(w.correct_sql, w.correct_abstention, 1.0)
    normalized = safe_div(score, max_possible)
    return ReliabilityScoreResult(
        score=round(score, 4),
        normalized_score=round(normalized, 4),
        total_cases=len(rows),
        correct_sql=correct_sql,
        correct_abstention=correct_abstention,
        wrong_sql=wrong_sql,
        wrong_abstention=wrong_abstention,
        unsafe_sql=unsafe_sql,
    )


def reliability_metric(records: Iterable[dict[str, Any]]) -> MetricResult:
    rs = reliability_score(records)
    return MetricResult(
        "reliability_score",
        rs.normalized_score,
        None,
        rs.total_cases,
        "EHRSQL-inspired SQL correctness + correct abstention score",
    )
