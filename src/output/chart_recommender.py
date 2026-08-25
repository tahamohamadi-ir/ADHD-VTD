from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal

try:
    import sqlglot
    from sqlglot import exp
except Exception:  # pragma: no cover
    sqlglot = None
    exp = None


VizIntentName = Literal["trend", "comparison", "distribution", "kpi", "ranking"]

_DATE_TOKENS = ("date", "month", "year", "تاریخ")
_NUMERIC_TOKENS = (
    "count",
    "sum",
    "avg",
    "total",
    "num",
    "rate",
    "score",
    "gpa",
    "تعداد",
    "میانگین",
    "مجموع",
    "نرخ",
)
_AGG_FUNC_RE = re.compile(r"\b(count|sum|avg|min|max|total)\s*\(", re.IGNORECASE)
_BUCKET_TOKENS = ("histogram", "width_bucket", "ntile", "bucket")

_INTENT_TITLES_FA: dict[str, str] = {
    "trend": "روند در طول زمان",
    "comparison": "مقایسه میان گروه‌ها",
    "distribution": "توزیع مقادیر",
    "kpi": "شاخص کلیدی",
    "ranking": "رتبه‌بندی موارد",
}

_INTENT_TO_CHART: dict[str, str] = {
    "trend": "line_chart",
    "comparison": "bar_chart",
    "distribution": "bar_chart",
    "kpi": "kpi",
    "ranking": "bar_chart",
}

_SELECT_CLAUSE_RE = re.compile(r"\bselect\b(?P<cols>.*?)\bfrom\b", re.IGNORECASE | re.DOTALL)
_GROUP_BY_RE = re.compile(
    r"\bgroup\s+by\b(?P<cols>.*?)(?=\border\s+by\b|\bhaving\b|\blimit\b|$)",
    re.IGNORECASE | re.DOTALL,
)
_ORDER_BY_RE = re.compile(
    r"\border\s+by\b\s+(?P<col>[^\s,()]+)(?:\s+(?P<dir>asc|desc))?", re.IGNORECASE
)
_LIMIT_RE = re.compile(r"\blimit\s+(\d+)", re.IGNORECASE)
_AS_ALIAS_RE = re.compile(
    r"\bas\s+(\"[^\"]+\"|\[[^\]]+\]|`[^`]+`|[A-Za-z_\u0600-\u06FF][\w\u0600-\u06FF]*)",
    re.IGNORECASE,
)
_IDENT_RE = re.compile(r"[A-Za-z_\u0600-\u06FF][\w\u0600-\u06FF]*")


@dataclass(frozen=True)
class VizIntentResult:
    intent: VizIntentName
    x_column: str | None
    y_column: str | None
    title_hint_fa: str


@dataclass(frozen=True)
class _SqlShape:
    projections: list[str]
    group_by: list[str]
    order_col: str | None
    order_desc: bool
    limit: int | None
    has_aggregate: bool


def recommend_chart(
    execution_result: List[Dict[str, Any]] | None, sql: str | None = None
) -> Dict[str, str]:
    """Recommend a chart type based on the shape of the execution result."""
    if not execution_result:
        fallback = _fallback_recommendation(sql)
        if fallback is not None:
            return fallback
        return {"recommended_visual": None, "chart_reason": None}

    rows = execution_result
    if not rows:
        return {"recommended_visual": None, "chart_reason": "No data"}

    num_rows = len(rows)
    num_cols = len(rows[0]) if num_rows > 0 else 0
    headers = list(rows[0].keys()) if num_rows > 0 else []

    if num_rows == 1 and num_cols == 1:
        return {"recommended_visual": "kpi", "chart_reason": "Single scalar value"}

    if num_rows > 1 and num_cols == 2:
        return {
            "recommended_visual": "bar_chart",
            "chart_reason": "Two columns typically represent a dimension and a metric",
        }

    if num_rows > 1 and num_cols >= 3:
        if any("year" in h.lower() or "date" in h.lower() or "month" in h.lower() for h in headers):
            return {"recommended_visual": "line_chart", "chart_reason": "Time dimension detected"}
        return {
            "recommended_visual": "heatmap",
            "chart_reason": "Matrix data suitable for heatmap or stacked bar chart",
        }

    return {"recommended_visual": "table", "chart_reason": "Default table representation"}


def classify_viz_intent(sql: str) -> VizIntentResult:
    """Classify the visualization intent of a read-only SELECT statement."""
    text = (sql or "").strip()
    shape: _SqlShape | None = None
    if sqlglot is not None:
        shape = _shape_with_sqlglot(text)
    if shape is None:
        shape = _shape_with_regex(text)
    return _classify_shape(shape, text.lower())


def _fallback_recommendation(sql: str | None) -> Dict[str, str] | None:
    """Consult classify_viz_intent only when the shape-based logic has no answer."""
    if not sql:
        return None
    try:
        result = classify_viz_intent(sql)
    except Exception:  # pragma: no cover - defensive, never break legacy behavior
        return None
    chart = _INTENT_TO_CHART.get(result.intent)
    if chart is None:
        return None
    return {"recommended_visual": chart, "chart_reason": f"Viz intent fallback: {result.intent}"}


def _classify_shape(shape: _SqlShape, sql_lower: str) -> VizIntentResult:
    first = shape.projections[0] if shape.projections else None
    second = shape.projections[1] if len(shape.projections) > 1 else None
    temporal_names = shape.group_by + ([shape.order_col] if shape.order_col else [])

    if any(token in sql_lower for token in _BUCKET_TOKENS):
        intent: VizIntentName = "distribution"
    elif any(_is_date_like(name) for name in temporal_names):
        intent = "trend"
    elif (
        shape.order_desc
        and shape.limit is not None
        and shape.limit <= 20
        and shape.order_col is not None
        and (_looks_numeric(shape.order_col) or shape.has_aggregate)
    ):
        intent = "ranking"
    elif len(shape.projections) <= 1 and shape.has_aggregate and not shape.group_by:
        intent = "kpi"
    else:
        intent = "comparison"

    x_column = first if intent != "kpi" else None
    y_column = second if intent != "kpi" else first
    return VizIntentResult(
        intent=intent, x_column=x_column, y_column=y_column,
        title_hint_fa=_INTENT_TITLES_FA[intent],
    )


def _shape_with_sqlglot(sql: str) -> _SqlShape | None:
    try:
        tree = sqlglot.parse_one((sql or "").strip().rstrip(";"), read="sqlite")
        if tree is None or not hasattr(tree, "selects"):
            return None
        projections = [e.alias_or_name for e in tree.selects if e.alias_or_name]
        group_arg = tree.args.get("group")
        group_by = [
            getattr(e, "name", "") or e.sql(dialect="sqlite")
            for e in (group_arg.expressions if group_arg is not None else [])
        ]
        order_col, order_desc = None, False
        order_arg = tree.args.get("order")
        if order_arg is not None and getattr(order_arg, "expressions", None):
            key = order_arg.expressions[0].this
            order_col = getattr(key, "name", "") or key.sql(dialect="sqlite")
            order_desc = bool(order_arg.expressions[0].args.get("desc"))
        limit = None
        limit_arg = tree.args.get("limit")
        if limit_arg is not None:
            try:
                limit = int(limit_arg.expression.this)
            except Exception:
                limit = None
        has_aggregate = any(e.find(exp.AggFunc) is not None for e in tree.selects)
        return _SqlShape(projections, group_by, order_col, order_desc, limit, has_aggregate)
    except Exception:
        return None


def _shape_with_regex(sql: str) -> _SqlShape:
    select_match = _SELECT_CLAUSE_RE.search(sql)
    projections: list[str] = []
    if select_match is not None:
        projections = [
            name
            for part in _split_top_level(select_match.group("cols"))
            if (name := _projection_name(part))
        ]

    group_by: list[str] = []
    group_match = _GROUP_BY_RE.search(sql)
    if group_match is not None:
        group_by = [n for p in _split_top_level(group_match.group("cols")) if (n := _clean_name(p))]

    order_col, order_desc = None, False
    order_match = _ORDER_BY_RE.search(sql)
    if order_match is not None:
        order_col = _clean_name(order_match.group("col"))
        order_desc = (order_match.group("dir") or "").lower() == "desc"

    limit_match = _LIMIT_RE.search(sql)
    limit = int(limit_match.group(1)) if limit_match is not None else None
    has_aggregate = bool(_AGG_FUNC_RE.search(sql))
    return _SqlShape(projections, group_by, order_col, order_desc, limit, has_aggregate)


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        if ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _projection_name(part: str) -> str | None:
    alias = _AS_ALIAS_RE.search(part)
    if alias is not None:
        return _clean_name(alias.group(1))
    identifiers = _IDENT_RE.findall(part)
    return identifiers[-1] if identifiers else None


def _clean_name(raw: str) -> str:
    name = raw.strip().strip("\"'`[]")
    _, _, tail = name.rpartition(".")
    return tail.strip() if tail else name.strip()


def _is_date_like(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in _DATE_TOKENS)


def _looks_numeric(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in _NUMERIC_TOKENS)
