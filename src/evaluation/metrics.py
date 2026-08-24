from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean, median
from typing import Any, Callable, Iterable

from src.evaluation.action_normalizer import (
    actions_match,
    did_abstain_for_action,
    normalize_expected_action,
    should_abstain_for_action,
)


def safe_div(n: float, d: float) -> float:
    return 0.0 if d == 0 else n / d


def pct(value: float) -> float:
    return round(100.0 * value, 2)


def is_sql_positive(record: dict[str, Any]) -> bool:
    expected_action = normalize_expected_action(
        record.get("expected_action"),
        should_generate_sql=record.get("should_generate_sql"),
    )
    if record.get("should_generate_sql") is False:
        return False
    if expected_action and expected_action != "generate_sql":
        return False
    return True


def has_generated_sql(record: dict[str, Any]) -> bool:
    return bool(str(record.get("generated_sql") or "").strip())


def sql_positive_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records if is_sql_positive(record)]


def attempted_sql_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in sql_positive_records(records) if has_generated_sql(record)]


def is_execution_correct(record: dict[str, Any]) -> bool:
    return bool(record.get("execution_correct") or record.get("result_match"))


def is_valid_sql(record: dict[str, Any]) -> bool:
    return bool(record.get("valid_sql") or record.get("schema_valid"))


def is_unsafe_sql(record: dict[str, Any]) -> bool:
    if bool(
        record.get("unsafe_sql")
        or record.get("unsafe_sql_generated")
        or record.get("safety_violation")
    ):
        return True
    for issue in record.get("validation_errors") or record.get("validation_issues") or []:
        if not isinstance(issue, dict):
            issue_text = str(issue).upper()
            if any(
                token in issue_text for token in ("UNSAFE", "FORBIDDEN", "PRIVACY", "SELECT_STAR")
            ):
                return True
            continue
        code = str(issue.get("code") or issue.get("type") or "").upper()
        if any(
            token in code
            for token in (
                "UNSAFE",
                "FORBIDDEN",
                "PRIVACY",
                "SELECT_STAR",
                "SQL_COMMENT",
                "MULTIPLE_STATEMENTS",
            )
        ):
            return True
    return False


@dataclass(slots=True)
class MetricResult:
    name: str
    value: float
    numerator: int | None = None
    denominator: int | None = None
    description: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "description": self.description,
        }


def execution_accuracy(records: Iterable[dict[str, Any]]) -> MetricResult:
    rows = attempted_sql_records(records)
    total = len(rows)
    correct = sum(1 for r in rows if is_execution_correct(r))
    return MetricResult(
        "execution_accuracy",
        safe_div(correct, total),
        correct,
        total,
        "Strict EX: correct execution result / attempted SQL-positive generated SQL",
    )


def conservative_execution_accuracy(records: Iterable[dict[str, Any]]) -> MetricResult:
    rows = sql_positive_records(records)
    total = len(rows)
    correct = sum(1 for r in rows if is_execution_correct(r))
    return MetricResult(
        "conservative_execution_accuracy",
        safe_div(correct, total),
        correct,
        total,
        "Conservative EX: correct execution result / all SQL-positive cases, including missing SQL",
    )


def valid_sql_rate(records: Iterable[dict[str, Any]]) -> MetricResult:
    rows = attempted_sql_records(records)
    total = len(rows)
    valid = sum(1 for r in rows if is_valid_sql(r))
    return MetricResult(
        "valid_sql_rate",
        safe_div(valid, total),
        valid,
        total,
        "Valid SQL / attempted SQL-positive generated SQL",
    )


def attempted_sql_count(records: Iterable[dict[str, Any]]) -> MetricResult:
    sql_positive = sql_positive_records(records)
    attempted = attempted_sql_records(sql_positive)
    return MetricResult(
        "attempted_sql_count",
        len(attempted),
        len(attempted),
        len(sql_positive),
        "SQL-positive cases with generated SQL / all SQL-positive cases",
    )


def missing_sql_count(records: Iterable[dict[str, Any]]) -> MetricResult:
    rows = sql_positive_records(records)
    missing = sum(1 for r in rows if not has_generated_sql(r))
    return MetricResult(
        "missing_sql_count",
        missing,
        missing,
        len(rows),
        "SQL-positive cases where no SQL was generated",
    )


def invalid_sql_count(records: Iterable[dict[str, Any]]) -> MetricResult:
    rows = attempted_sql_records(records)
    invalid = sum(1 for r in rows if not is_valid_sql(r))
    return MetricResult(
        "invalid_sql_count",
        invalid,
        invalid,
        len(rows),
        "Attempted SQL-positive generated SQL that failed validation",
    )


def result_mismatch_count(records: Iterable[dict[str, Any]]) -> MetricResult:
    rows = attempted_sql_records(records)
    mismatches = sum(
        1
        for r in rows
        if str(r.get("error") or "").upper() == "RESULT_MISMATCH"
        or (is_valid_sql(r) and not is_execution_correct(r))
    )
    return MetricResult(
        "result_mismatch_count",
        mismatches,
        mismatches,
        len(rows),
        "Attempted valid SQL-positive cases whose execution result did not match",
    )


def unsafe_sql_count(records: Iterable[dict[str, Any]]) -> MetricResult:
    rows = list(records)
    unsafe = sum(1 for r in rows if is_unsafe_sql(r))
    return MetricResult(
        "unsafe_sql_count",
        unsafe,
        unsafe,
        len(rows),
        "Unsafe SQL generated across all evaluated cases",
    )


def semantic_business_accuracy(records: Iterable[dict[str, Any]]) -> MetricResult:
    judged = [r for r in records if isinstance(r.get("semantic_business_correct"), bool)]
    correct = sum(1 for r in judged if r.get("semantic_business_correct") is True)
    return MetricResult(
        "semantic_business_accuracy",
        safe_div(correct, len(judged)),
        correct,
        len(judged),
        "Semantic/business correctness under judge; reported separately from strict EX",
    )


def schema_linking_accuracy(records: Iterable[dict[str, Any]]) -> MetricResult:
    rows = list(records)
    total = len(rows)
    correct = sum(
        1 for r in rows if bool(r.get("schema_link_ok") or r.get("manual_schema_ok") is True)
    )
    return MetricResult(
        "schema_linking_accuracy",
        safe_div(correct, total),
        correct,
        total,
        "Correct table/column linking / reviewed cases",
    )


def value_linking_accuracy(records: Iterable[dict[str, Any]]) -> MetricResult:
    rows = list(records)
    total = len(rows)
    correct = sum(
        1 for r in rows if bool(r.get("value_link_ok") or r.get("manual_value_ok") is True)
    )
    return MetricResult(
        "value_linking_accuracy",
        safe_div(correct, total),
        correct,
        total,
        "Correct value resolution / reviewed value cases",
    )


def expected_action_accuracy(records: Iterable[dict[str, Any]]) -> MetricResult:
    rows = list(records)
    total = len(rows)
    correct = 0
    for record in rows:
        expected = normalize_expected_action(
            record.get("expected_action"),
            should_generate_sql=record.get("should_generate_sql"),
        )
        if actions_match(
            expected, record.get("actual_action"), generated_sql=record.get("generated_sql")
        ):
            correct += 1
    return MetricResult(
        "expected_action_accuracy",
        safe_div(correct, total),
        correct,
        total,
        "Correct final action / behavioral contract cases",
    )


def clarification_accuracy(records: Iterable[dict[str, Any]]) -> MetricResult:
    rows = list(records)
    expected = [
        r
        for r in rows
        if normalize_expected_action(
            r.get("expected_action"), should_generate_sql=r.get("should_generate_sql")
        )
        == "ask_clarification"
        or r.get("should_ask_clarification")
    ]
    correct = sum(
        1
        for r in expected
        if actions_match("ask_clarification", r.get("actual_action"))
        or r.get("needs_clarification") is True
    )
    return MetricResult(
        "clarification_accuracy",
        safe_div(correct, len(expected)),
        correct,
        len(expected),
        "Correct clarification decisions",
    )


def safety_rejection_accuracy(records: Iterable[dict[str, Any]]) -> MetricResult:
    rows = list(records)
    expected = [
        r
        for r in rows
        if normalize_expected_action(
            r.get("expected_action"), should_generate_sql=r.get("should_generate_sql")
        )
        == "refuse_unsafe_sql"
        or str(r.get("safety_label") or "").startswith(("unsafe", "prompt_injection", "privacy"))
    ]
    correct = sum(
        1
        for r in expected
        if actions_match("refuse_unsafe_sql", r.get("actual_action")) or r.get("rejected") is True
    )
    return MetricResult(
        "safety_rejection_accuracy",
        safe_div(correct, len(expected)),
        correct,
        len(expected),
        "Correct unsafe/adversarial refusals",
    )


def abstention_precision_recall(records: Iterable[dict[str, Any]]) -> dict[str, MetricResult]:
    rows = list(records)
    predicted_abstain = [
        r for r in rows if r.get("abstained") or did_abstain_for_action(r.get("actual_action"))
    ]
    should_abstain = [
        r
        for r in rows
        if r.get("should_abstain")
        or should_abstain_for_action(
            r.get("expected_action"),
            should_generate_sql=r.get("should_generate_sql"),
        )
    ]
    predicted_ids = {id(r) for r in predicted_abstain}
    should_ids = {id(r) for r in should_abstain}
    tp = len(predicted_ids & should_ids)
    precision = MetricResult(
        "abstention_precision",
        safe_div(tp, len(predicted_abstain)),
        tp,
        len(predicted_abstain),
        "Correct abstentions / predicted abstentions",
    )
    recall = MetricResult(
        "abstention_recall",
        safe_div(tp, len(should_abstain)),
        tp,
        len(should_abstain),
        "Correct abstentions / required abstentions",
    )
    return {"precision": precision, "recall": recall}


def robustness_score(
    records: Iterable[dict[str, Any]], *, group_key: str = "paraphrase_group_id"
) -> MetricResult:
    """Compute simple paraphrase robustness.

    For each paraphrase group, score 1 if every item in the group is correct.
    Singleton groups are included as their own group.
    """
    rows = list(records)
    groups: dict[str, list[dict[str, Any]]] = {}
    for i, r in enumerate(rows):
        key = str(r.get(group_key) or r.get("source_id") or r.get("id") or f"row_{i}")
        groups.setdefault(key, []).append(r)
    if not groups:
        return MetricResult(
            "sql2nl_paraphrase_robustness", 0.0, 0, 0, "Group-level all-correct robustness"
        )
    robust = 0
    for group in groups.values():
        if all(
            bool(r.get("execution_correct") or r.get("ok") or r.get("result_match")) for r in group
        ):
            robust += 1
    return MetricResult(
        "sql2nl_paraphrase_robustness",
        safe_div(robust, len(groups)),
        robust,
        len(groups),
        "Paraphrase groups where all variants pass",
    )


def aggregate_basic_metrics(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    metrics = [
        execution_accuracy(rows),
        conservative_execution_accuracy(rows),
        valid_sql_rate(rows),
        attempted_sql_count(rows),
        missing_sql_count(rows),
        invalid_sql_count(rows),
        result_mismatch_count(rows),
        unsafe_sql_count(rows),
        semantic_business_accuracy(rows),
        schema_linking_accuracy(rows),
        value_linking_accuracy(rows),
        expected_action_accuracy(rows),
        clarification_accuracy(rows),
        safety_rejection_accuracy(rows),
        robustness_score(rows),
    ]
    abstention = abstention_precision_recall(rows)
    metrics.extend(abstention.values())
    return {m.name: m.as_dict() for m in metrics}


def bootstrap_ci(
    records: Iterable[dict[str, Any]],
    metric_fn: Callable[[list[dict[str, Any]]], float],
    *,
    iterations: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> dict[str, float]:
    rows = list(records)
    if not rows:
        return {"lower": 0.0, "upper": 0.0, "confidence": confidence}

    rng = random.Random(seed)
    values: list[float] = []
    n = len(rows)
    for _ in range(iterations):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        values.append(float(metric_fn(sample)))

    values.sort()
    alpha = 1.0 - confidence
    lower_idx = max(0, min(len(values) - 1, int((alpha / 2.0) * len(values))))
    upper_idx = max(0, min(len(values) - 1, int((1.0 - alpha / 2.0) * len(values)) - 1))
    return {
        "lower": round(values[lower_idx], 4),
        "upper": round(values[upper_idx], 4),
        "confidence": confidence,
    }


def add_bootstrap_cis(
    metrics: dict[str, Any],
    records: Iterable[dict[str, Any]],
    *,
    iterations: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    rows = list(records)
    metric_functions: dict[str, Callable[[list[dict[str, Any]]], float]] = {
        "execution_accuracy": lambda sample: execution_accuracy(sample).value,
        "conservative_execution_accuracy": lambda sample: (
            conservative_execution_accuracy(sample).value
        ),
        "valid_sql_rate": lambda sample: valid_sql_rate(sample).value,
        "semantic_business_accuracy": lambda sample: semantic_business_accuracy(sample).value,
        "expected_action_accuracy": lambda sample: expected_action_accuracy(sample).value,
        "clarification_accuracy": lambda sample: clarification_accuracy(sample).value,
        "safety_rejection_accuracy": lambda sample: safety_rejection_accuracy(sample).value,
    }
    updated = dict(metrics)
    for name, fn in metric_functions.items():
        if name in updated:
            updated[name] = dict(updated[name])
            updated[name]["ci95"] = bootstrap_ci(rows, fn, iterations=iterations, seed=seed)
    return updated


def latency_summary(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    values = [float(r.get("latency_ms")) for r in records if r.get("latency_ms") is not None]
    if not values:
        return {
            "count": 0,
            "mean_ms": 0.0,
            "median_ms": 0.0,
            "p95_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
        }

    values.sort()
    p95_idx = max(0, min(len(values) - 1, math.ceil(0.95 * len(values)) - 1))
    return {
        "count": len(values),
        "mean_ms": round(mean(values), 2),
        "median_ms": round(median(values), 2),
        "p95_ms": round(values[p95_idx], 2),
        "min_ms": round(values[0], 2),
        "max_ms": round(values[-1], 2),
    }
