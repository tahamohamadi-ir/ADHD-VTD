from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Callable, Iterable


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    lower: float
    upper: float
    confidence: float
    iterations: int
    seed: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "lower": self.lower,
            "upper": self.upper,
            "confidence": self.confidence,
            "iterations": self.iterations,
            "seed": self.seed,
        }


@dataclass(frozen=True, slots=True)
class McNemarResult:
    compared_cases: int
    baseline_correct_system_wrong: int
    baseline_wrong_system_correct: int
    both_correct: int
    both_wrong: int
    statistic: float
    p_value: float
    exact_p_value: float | None
    method: str
    warning: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "compared_cases": self.compared_cases,
            "baseline_correct_system_wrong": self.baseline_correct_system_wrong,
            "baseline_wrong_system_correct": self.baseline_wrong_system_correct,
            "both_correct": self.both_correct,
            "both_wrong": self.both_wrong,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "exact_p_value": self.exact_p_value,
            "method": self.method,
            "warning": self.warning,
        }


def bootstrap_ci(
    records: Iterable[dict[str, Any]],
    metric_fn: Callable[[list[dict[str, Any]]], float],
    *,
    iterations: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> ConfidenceInterval:
    rows = list(records)
    if not rows:
        return ConfidenceInterval(0.0, 0.0, confidence, iterations, seed)

    rng = random.Random(seed)
    values: list[float] = []
    n = len(rows)
    for _ in range(iterations):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        values.append(_safe_float(metric_fn(sample)))

    values.sort()
    alpha = 1.0 - confidence
    lower_idx = max(0, min(len(values) - 1, math.floor((alpha / 2.0) * len(values))))
    upper_idx = max(0, min(len(values) - 1, math.ceil((1.0 - alpha / 2.0) * len(values)) - 1))
    return ConfidenceInterval(
        lower=round(values[lower_idx], 4),
        upper=round(values[upper_idx], 4),
        confidence=confidence,
        iterations=iterations,
        seed=seed,
    )


def _case_id(record: dict[str, Any]) -> str:
    return str(
        record.get("id")
        or record.get("case_id")
        or record.get("audit_id")
        or record.get("source_id")
        or ""
    )


def _is_correct(record: dict[str, Any], correctness_key: str) -> bool:
    return bool(record.get(correctness_key) or record.get("ok") or record.get("result_match"))


def _chi_square_df1_survival(statistic: float) -> float:
    if statistic <= 0:
        return 1.0
    # For df=1, survival function is erfc(sqrt(x / 2)).
    return math.erfc(math.sqrt(statistic / 2.0))


def _two_sided_binomial_p_value(successes: int, trials: int) -> float:
    if trials <= 0:
        return 1.0
    tail = sum(math.comb(trials, i) for i in range(0, successes + 1)) / (2**trials)
    return min(1.0, 2.0 * tail)


@dataclass(frozen=True, slots=True)
class ExactMcNemarResult:
    b: int
    c: int
    n: int
    statistic: float
    p_value: float
    significant_at_0_05: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "b": self.b,
            "c": self.c,
            "n": self.n,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "significant_at_0_05": self.significant_at_0_05,
        }


def _continuity_corrected_mcnemar_statistic(b: int, c: int) -> float:
    discordant = b + c
    if discordant == 0:
        return 0.0
    return (abs(b - c) - 1) ** 2 / discordant


def _exact_two_sided_binomial_tail(b: int, c: int) -> float:
    if b == c:
        return 1.0
    n = b + c
    tail = sum(math.comb(n, k) for k in range(0, min(b, c) + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def exact_mcnemar_test(correct_a: int, incorrect_b: int) -> ExactMcNemarResult:
    """Exact McNemar test over discordant paired outcomes only.

    correct_a (b) counts pairs where system A is correct and system B is wrong;
    incorrect_b (c) counts pairs where system A is wrong and system B is correct.
    """
    b = max(0, correct_a)
    c = max(0, incorrect_b)
    p_value = round(_exact_two_sided_binomial_tail(b, c), 6)
    return ExactMcNemarResult(
        b=b,
        c=c,
        n=b + c,
        statistic=round(_continuity_corrected_mcnemar_statistic(b, c), 6),
        p_value=p_value,
        significant_at_0_05=p_value < 0.05,
    )


def mcnemar_test(
    baseline_records: Iterable[dict[str, Any]],
    system_records: Iterable[dict[str, Any]],
    *,
    correctness_key: str = "execution_correct",
    exact_threshold: int = 25,
) -> McNemarResult:
    baseline_by_id = {_case_id(row): row for row in baseline_records if _case_id(row)}
    system_by_id = {_case_id(row): row for row in system_records if _case_id(row)}
    common_ids = sorted(set(baseline_by_id) & set(system_by_id))

    both_correct = 0
    both_wrong = 0
    baseline_correct_system_wrong = 0
    baseline_wrong_system_correct = 0

    for case_id in common_ids:
        base_correct = _is_correct(baseline_by_id[case_id], correctness_key)
        sys_correct = _is_correct(system_by_id[case_id], correctness_key)
        if base_correct and sys_correct:
            both_correct += 1
        elif not base_correct and not sys_correct:
            both_wrong += 1
        elif base_correct and not sys_correct:
            baseline_correct_system_wrong += 1
        else:
            baseline_wrong_system_correct += 1

    b = baseline_wrong_system_correct
    c = baseline_correct_system_wrong
    discordant = b + c
    if discordant == 0:
        statistic = 0.0
        p_value = 1.0
        exact_p_value = 1.0
    else:
        statistic = (abs(b - c) - 1) ** 2 / discordant
        p_value = _chi_square_df1_survival(statistic)
        exact_p_value = (
            _two_sided_binomial_p_value(min(b, c), discordant)
            if discordant <= exact_threshold
            else None
        )

    warning = None
    if not common_ids:
        warning = "No overlapping case IDs; paired McNemar test is not meaningful."
    elif len(common_ids) < 20:
        warning = "Small paired sample; treat p-value as descriptive only."

    return McNemarResult(
        compared_cases=len(common_ids),
        baseline_correct_system_wrong=baseline_correct_system_wrong,
        baseline_wrong_system_correct=baseline_wrong_system_correct,
        both_correct=both_correct,
        both_wrong=both_wrong,
        statistic=round(statistic, 6),
        p_value=round(p_value, 6),
        exact_p_value=round(exact_p_value, 6) if exact_p_value is not None else None,
        method="exact_binomial"
        if exact_p_value is not None
        else "mcnemar_chi_square_continuity_corrected",
        warning=warning,
    )
