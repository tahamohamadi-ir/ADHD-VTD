from __future__ import annotations

import math
import random
import re
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from typing import Any

Rule = tuple[re.Pattern[str], str]

PARAPHRASE_RULES: list[Rule] = [
    (re.compile(r"\bبیشترین\b"), "بالاترین"),
    (re.compile(r"\bکمترین\b"), "پایین\u200cترین"),
    (re.compile(r"\bتعداد\b"), "شمار"),
    (re.compile(r"\bنشان\s+بده\b"), "نمایش بده"),
    (re.compile(r"\bدیتاست\b"), "مجموعه\u200cداده"),
    (re.compile(r"\bنمره\s+امتحان\b"), "نمره آزمون"),
    (re.compile(r"\bدرباره\b"), "پیرامون"),
    (re.compile(r"\bدر\s+طول\s+زمان\b"), "طی زمان"),
    (re.compile(r"\bآخرین\s+سال\b"), "واپسین سال"),
    (re.compile(r"\bبه\s+تفکیک\b"), "بر حسب"),
    (re.compile(r"\bبر\s+اساس\b"), "بر حسب"),
    (re.compile(r"\bبگو\b"), "ذکر کن"),
    (re.compile(r"\bبنویس\b"), "بیان کن"),
    (re.compile(r"\bبساز\b"), "ایجاد کن"),
    (re.compile(r"\bحساب\s+کن\b"), "محاسبه کن"),
    (re.compile(r"\bتحلیل\s+کن\b"), "بررسی کن"),
    (re.compile(r"\bمقایسه\s+کن\b"), "با یکدیگر مقایسه کن"),
    (re.compile(r"\bدانشجوها(ی)?\b"), "دانشجویان"),
    (re.compile(r"\bچند\s+رکورد\b"), "چه تعداد رکورد"),
    (re.compile(r"\bچقدره\b"), "چقدر است"),
    (re.compile(r"\bچیه\b"), "چیست"),
    (re.compile(r"\bچطوریه\b"), "چگونه است"),
    (re.compile(r"\bدارن\b"), "دارند"),
    (re.compile(r"\bdاره\b"), "دارد"),
    (re.compile(r"\bهستن\b"), "هستند"),
    (re.compile(r"\bکیه\b"), "کدام است"),
    (re.compile(r"\bچندتا\b"), "چند"),
    (re.compile(r"^(?!.*لطفا)"), "لطفاً "),
    (re.compile(r"\.(?=\s*$)"), "؟"),
    (re.compile(r"([^\s؟!?.])\s*$"), "\\1؟"),
]

METHOD = "rule_based_paraphrase_v1"
DIFFICULTY_LEVELS: tuple[str, ...] = ("easy", "medium", "hard", "complex")


def _apply_rules(text: str, rule_indices: Iterable[int]) -> str:
    result = text
    for index in rule_indices:
        pattern, replacement = PARAPHRASE_RULES[index]
        result = pattern.sub(replacement, result)
    return result


def _candidate_rule_sets(variant_index: int, total: int) -> Iterator[list[int]]:
    for offset in range(total):
        first = (variant_index + offset) % total
        second = (first + 1) % total
        if second != first:
            yield sorted([first, second])
    for offset in range(total):
        yield [(variant_index + offset) % total]


def paraphrase_question(question: str, variant_index: int) -> str:
    if not isinstance(question, str):
        raise ValueError("question must be a string.")
    if not question.strip():
        raise ValueError("question must be non-empty.")
    total = len(PARAPHRASE_RULES)
    for rule_indices in _candidate_rule_sets(variant_index, total):
        candidate = _apply_rules(question, rule_indices)
        if candidate != question:
            return candidate
    raise ValueError(f"No paraphrase rule is applicable to question: {question!r}")


def _case_id(case: dict[str, Any], fallback: str) -> str:
    cid = case.get("id") or case.get("case_id") or case.get("audit_id") or case.get("source_id")
    return str(cid) if cid else fallback


def _dedupe_cases(cases: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for position, case in enumerate(cases):
        cid = _case_id(case, f"__idx_{position}")
        if cid in seen:
            continue
        seen.add(cid)
        unique.append(case)
    return unique


def _proportional_quotas(counts: dict[str, int], total: int) -> dict[str, int]:
    keys = sorted(counts)
    pool_size = sum(counts[key] for key in keys)
    if pool_size <= 0:
        return {key: 0 for key in keys}
    quotas = {key: min(counts[key], math.floor(total * counts[key] / pool_size)) for key in keys}
    leftover = total - sum(quotas.values())
    order = sorted(
        keys,
        key=lambda key: (-(total * counts[key] / pool_size - quotas[key]), key),
    )
    for key in order[: max(leftover, 0)]:
        quotas[key] = min(quotas[key] + 1, counts[key])
    return quotas


def _case_id_for_sort(case: dict[str, Any]) -> str:
    return _case_id(case, "")


def select_holdout_cases(
    cases: Iterable[dict[str, Any]],
    n: int,
    seed: int,
) -> list[dict[str, Any]]:
    if n <= 0:
        raise ValueError("n must be a positive integer.")
    pool = _dedupe_cases(cases)
    if not pool:
        return []
    target = min(n, len(pool))
    groups: dict[str, list[dict[str, Any]]] = {}
    for case in pool:
        difficulty = str(case.get("difficulty") or "unknown")
        groups.setdefault(difficulty, []).append(case)
    rng = random.Random(seed)
    shuffled = {key: rng.sample(members, len(members)) for key, members in groups.items()}
    quotas = _proportional_quotas({key: len(members) for key, members in groups.items()}, target)
    selected: list[dict[str, Any]] = []
    for difficulty in sorted(groups):
        selected.extend(shuffled[difficulty][: quotas[difficulty]])
    selected.sort(key=_case_id_for_sort)
    return [dict(case) for case in selected]


def build_holdout_dataset(
    cases: Iterable[dict[str, Any]],
    n: int,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_pool = _dedupe_cases(cases)
    selected = select_holdout_cases(source_pool, n, seed)
    holdout: list[dict[str, Any]] = []
    for variant_index, case in enumerate(selected):
        new_case = dict(case)
        question_key = "question_fa" if "question_fa" in new_case else "question"
        original_question = str(new_case.get(question_key) or "")
        cid = _case_id(case, f"__idx_{variant_index}")
        new_case[question_key] = paraphrase_question(original_question, variant_index)
        new_case["id"] = f"{cid}-P"
        new_case["original_case_id"] = cid
        holdout.append(new_case)
    difficulty_counts: dict[str, int] = {}
    for case in selected:
        difficulty = str(case.get("difficulty") or "unknown")
        difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "method": METHOD,
        "source_count": len(source_pool),
        "held_out_count": len(holdout),
        "difficulty_counts": dict(sorted(difficulty_counts.items())),
    }
    return holdout, manifest


def build_metadata_block(source_case_count: int, held_out_count: int, seed: int) -> dict[str, Any]:
    return {
        "method": METHOD,
        "seed": seed,
        "source_case_count": source_case_count,
        "held_out_count": held_out_count,
    }
