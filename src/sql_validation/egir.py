from __future__ import annotations

import re
from dataclasses import dataclass, field


AGGREGATE_TERMS_FA: tuple[str, ...] = (
    "میانگین",
    "مجموع",
    "تعداد",
    "درصد",
    "نسبت",
    "حداکثر",
    "حداقل",
)
SPLIT_TERMS_FA: tuple[str, ...] = ("به تفکیک", "تفکیک", "بر اساس", "به ازای هر", "هر")
TREND_TERMS_FA: tuple[str, ...] = ("روند", "طی زمان", "سالانه", "ماهانه", "تغییرات")
LIST_TERMS_FA: tuple[str, ...] = ("لیست", "فهرست", "نمونه", "کدام دانشجویان", "کدام افراد")

_AGG_FUNCS = re.compile(r"\b(count|sum|avg|min|max)\s*\(", re.IGNORECASE)
_HAS_GROUP_BY = re.compile(r"\bgroup\s+by\b", re.IGNORECASE)
_HAS_ORDER_BY_DATE = re.compile(
    r"order\s+by[^)]*\b(date|year|month|time)\b", re.IGNORECASE
)
_HAS_LIMIT = re.compile(r"\blimit\s+\d+", re.IGNORECASE)


@dataclass(frozen=True)
class EgirIssue:
    code: str
    message: str
    feedback_fa: str


@dataclass(frozen=True)
class EgirReport:
    ok: bool
    issues: tuple[EgirIssue, ...] = ()
    matched_intents: tuple[str, ...] = field(default_factory=tuple)


def detect_intents(question: str) -> tuple[str, ...]:
    q = (question or "").lower()
    intents: list[str] = []
    if AGGREGATE_TERMS_FA and any(t in q for t in AGGREGATE_TERMS_FA):
        intents.append("aggregate")
    if any(t in q for t in SPLIT_TERMS_FA):
        intents.append("split_by_group")
    if any(t in q for t in TREND_TERMS_FA):
        intents.append("trend_over_time")
    if any(t in q for t in LIST_TERMS_FA):
        intents.append("raw_list")
    return tuple(intents)


def check_intent_result_alignment(question: str, sql: str, row_count: int | None = None) -> EgirReport:
    """Deterministic EGIR-style critic: Persian question intent vs SQL/result shape.

    Runs AFTER successful execution. It never proves correctness; it catches the
    classic intent/shape mismatches (missing GROUP BY for split questions,
    aggregate-vs-rows confusion, trend without temporal ordering).
    """
    sql_text = (sql or "").strip()
    intents = detect_intents(question)
    issues: list[EgirIssue] = []
    has_agg = bool(_AGG_FUNCS.search(sql_text))
    has_group = bool(_HAS_GROUP_BY.search(sql_text))

    if "split_by_group" in intents and has_agg and not has_group:
        issues.append(
            EgirIssue(
                code="MISSING_GROUP_BY",
                message="Question asks per-group breakdown but SQL aggregates without GROUP BY.",
                feedback_fa=(
                    "سوال به تفکیک گروه خواسته شده اما کوئری GROUP BY ندارد؛ "
                    "ستون‌های تفکیک را به SELECT و GROUP BY اضافه کن."
                ),
            )
        )

    if "aggregate" not in intents and "raw_list" not in intents and has_agg and has_group and (
        row_count is not None and row_count == 1
    ):
        issues.append(
            EgirIssue(
                code="SINGLE_ROW_FOR_OPEN_QUESTION",
                message="Open-ended question produced a single aggregated row.",
                feedback_fa="سوال باز پرسیده شده ولی خروجی یک ردیف تجمعی است؛ شکل پرسش و کوئری را بسنج.",
            )
        )

    if "trend_over_time" in intents and not _HAS_ORDER_BY_DATE.search(sql_text) and "date" not in sql_text.lower() and "year" not in sql_text.lower():
        issues.append(
            EgirIssue(
                code="TREND_WITHOUT_TEMPORAL_COLUMN",
                message="Trend question but SQL references no temporal column or ordering.",
                feedback_fa="برای تحلیل روند، ستون زمانی (تاریخ/سال/ماه) باید در SELECT یا ORDER BY بیاید.",
            )
        )

    if "raw_list" in intents and has_agg and "count(*)" in sql_text.lower().replace(" ", ""):
        issues.append(
            EgirIssue(
                code="LIST_REQUEST_ANSWERED_BY_COUNT",
                message="List request answered by COUNT(*) instead of returning rows.",
                feedback_fa="کاربر فهرست خواسته نه شمارش؛ به‌جای COUNT(*) ردیف‌ها را برگردان (با LIMIT).",
            )
        )

    if row_count is None and "raw_list" in intents and not _HAS_LIMIT.search(sql_text):
        issues.append(
            EgirIssue(
                code="UNBOUNDED_LIST_QUERY",
                message="List-style query without LIMIT.",
                feedback_fa="کوئری فهرستی بدون LIMIT ناامن است؛ LIMIT 100 بگذار.",
            )
        )

    return EgirReport(ok=not issues, issues=tuple(issues), matched_intents=intents)
