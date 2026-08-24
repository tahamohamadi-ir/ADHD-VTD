from __future__ import annotations

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
) -> str:
    """Build a short deterministic Persian narrative for a successful answer."""
    rows = _rows(execution_result)
    opening = _opening_sentence(category)

    if not rows:
        sentences = [
            f"{opening} بررسی شد، اما {EMPTY_RESULT_ANSWER.rstrip('.')}",
            "می‌توانید شرط‌های پرسش را بازنگری کنید یا بازهٔ داده را تغییر دهید.",
        ]
        return " ".join(sentences)

    num_rows = len(rows)
    headers = list(rows[0].keys())

    if num_rows == 1 and len(headers) == 1:
        value_text = _format_value(rows[0].get(headers[0]))
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
        metric_header = _numeric_column(rows, headers)
        if metric_header is not None and len(headers) >= 2:
            label_header = headers[0]
            top_row = max(rows, key=lambda row: row.get(metric_header) or 0)
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
    return " ".join(sentences)
