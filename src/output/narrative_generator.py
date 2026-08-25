from __future__ import annotations

import re
from typing import Any

from src.output.answer_formatter import EMPTY_RESULT_ANSWER, RESEARCH_DISCLAIMER

_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_CHART_SENTENCES: dict[str, str] = {
    "kpi": "برای نمایش این مقدار، کارت شاخص (KPI) پیشنهاد می‌شود.",
    "bar_chart": "برای مقایسه بهتر گروه‌ها، نمودار میله‌ای پیشنهاد می‌شود.",
    "line_chart": "به دلیل وجود بُعد زمانی، نمودار خطی پیشنهاد می‌شود.",
    "heatmap": "برای نمایش هم‌زمان چند بُعد، نمودار حرارتی پیشنهاد می‌شود.",
    "table": "نمایش جدولی برای بررسی دقیق این نتیجه مناسب است.",
}

_CATEGORY_OPENINGS: dict[str, str] = {
    "comparison": "برای پاسخ به پرسش مقایسه‌ای شما",
    "distribution": "برای بررسی توزیع درخواست‌شده",
    "trend": "برای بررسی روند",
    "ranking": "برای رتبه‌بندی درخواست‌شده",
    "analysis": "برای تحلیل درخواست‌شده",
    "aggregation": "برای محاسبه تجمعی درخواست‌شده",
}

_DEFAULT_OPENING = "برای پرسش شما"
_HIGHLIGHT_CAP_ROWS = 10

_NUMBER_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
_IGNORED_YEAR_RANGES = ((1300, 1500), (1900, 2100))
_GROUNDING_TOLERANCE = 1e-9
_GROUNDING_WARNING_HEADER = "\n⚠️ اعداد زیر در نتایج یافت نشدند: "


def find_ungrounded_numbers(narrative: str, rows: list[dict] | list[tuple]) -> list[str]:
    """Return Latin-digit numerals (>100, ignoring year ranges) missing from row values."""
    known = _row_numeric_values(rows)
    findings: list[str] = []
    for match in _NUMBER_RE.finditer(narrative or ""):
        lexeme = match.group(0).replace(",", "")
        try:
            value = float(lexeme)
        except ValueError:
            continue
        if abs(value) <= 100 or _is_year_like(value):
            continue
        if not any(abs(value - cell) <= _GROUNDING_TOLERANCE for cell in known):
            findings.append(lexeme)
    return findings


def _row_numeric_values(rows: list[dict] | list[tuple]) -> list[float]:
    values: list[float] = []
    for row in rows or []:
        cells = row.values() if isinstance(row, dict) else tuple(row)
        for cell in cells:
            if isinstance(cell, bool) or cell is None:
                continue
            if isinstance(cell, (int, float)):
                values.append(float(cell))
            elif isinstance(cell, str):
                try:
                    values.append(float(cell.replace(",", "")))
                except ValueError:
                    continue
    return values


def _is_year_like(value: float) -> bool:
    if value != int(value):
        return False
    year = int(value)
    return any(low <= year <= high for low, high in _IGNORED_YEAR_RANGES)


def _with_grounding_warning(narrative: str, rows: list | None) -> str:
    if rows is None:
        return narrative
    ungrounded = find_ungrounded_numbers(narrative, rows)
    if not ungrounded:
        return narrative
    listed = "، ".join(ungrounded[:5])
    return f"{narrative}{_GROUNDING_WARNING_HEADER}{listed}"


def to_persian_digits(value: Any) -> str:
    return str(value).translate(_PERSIAN_DIGITS)


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return to_persian_digits(round(value, 2))
    if isinstance(value, int):
        return to_persian_digits(value)
    return str(value)


def _rows(execution_result: Any) -> list[dict[str, Any]]:
    if not execution_result:
        return []
    if isinstance(execution_result, dict):
        return [execution_result]
    try:
        return list(execution_result)
    except TypeError:
        return []


def _numeric_column(rows: list[dict[str, Any]], headers: list[str]) -> str | None:
    for header in headers[1:]:
        values = [row.get(header) for row in rows]
        if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            return header
    return None


def _opening_sentence(category: str | None) -> str:
    normalized = (category or "").strip().lower()
    return _CATEGORY_OPENINGS.get(normalized, _DEFAULT_OPENING)


def generate_narrative(
    *,
    question: str | None = None,
    execution_result: Any = None,
    chart_recommendation: dict[str, Any] | None = None,
    category: str | None = None,
    rows: list | None = None,
) -> str:
    """Build a short deterministic Persian narrative for a successful answer.

    When ``rows`` is provided, numbers in the narrative that do not appear among the
    row values trigger a grounding warning suffix; ``None`` keeps legacy behavior.
    """
    result_rows = _rows(execution_result)
    opening = _opening_sentence(category)

    if not result_rows:
        sentences = [
            f"{opening} بررسی شد، اما {EMPTY_RESULT_ANSWER.rstrip('.')}",
            "می‌توانید شرط‌های پرسش را بازنگری کنید یا بازهٔ داده را تغییر دهید.",
        ]
        return _with_grounding_warning(" ".join(sentences), rows)

    num_rows = len(result_rows)
    headers = list(result_rows[0].keys())

    if num_rows == 1 and len(headers) == 1:
        value_text = _format_value(result_rows[0].get(headers[0]))
        sentences = [
            f"{opening} یک مقدار واحد به دست آمد.",
            f"مقدار محاسبه‌شده برابر است با {value_text}.",
        ]
    else:
        row_count_text = (
            f"حدود {_HIGHLIGHT_CAP_ROWS} ردیف"
            if num_rows > _HIGHLIGHT_CAP_ROWS
            else f"{to_persian_digits(num_rows)} ردیف"
        )
        highlight: str | None = None
        metric_header = _numeric_column(result_rows, headers)
        if metric_header is not None and len(headers) >= 2:
            label_header = headers[0]
            top_row = max(result_rows, key=lambda row: row.get(metric_header) or 0)
            top_label = top_row.get(label_header)
            top_value = _format_value(top_row.get(metric_header))
            highlight = (
                f"بیشترین مقدار «{metric_header}» برابر {top_value} و مربوط به «{top_label}» است."
            )
        sentences = [f"{opening} نتیجه در قالب {row_count_text} برگردانده شد."]
        if highlight:
            sentences.append(highlight)

    recommended_visual = (chart_recommendation or {}).get("recommended_visual")
    chart_sentence = _CHART_SENTENCES.get(str(recommended_visual))
    if chart_sentence:
        sentences.append(chart_sentence)

    sentences.append(RESEARCH_DISCLAIMER.replace("**", ""))
    return _with_grounding_warning(" ".join(sentences), rows)
