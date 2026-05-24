from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


ConsistencySeverity = Literal["warning", "error"]


@dataclass(slots=True)
class SqlConsistencyIssue:
    code: str
    message: str
    severity: ConsistencySeverity = "error"

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


@dataclass(slots=True)
class SqlConsistencyReport:
    passed: bool
    issues: list[SqlConsistencyIssue]

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": [issue.as_dict() for issue in self.issues],
        }


_AVG_TERMS = (
    "average",
    "avg",
    "mean",
    "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646",
)
_ABOVE_TERMS = (
    "above average",
    "higher than average",
    "greater than average",
    "\u0628\u0627\u0644\u0627\u062a\u0631 \u0627\u0632 \u0645\u06cc\u0627\u0646\u06af\u06cc\u0646",
    "\u0628\u06cc\u0634\u062a\u0631 \u0627\u0632 \u0645\u06cc\u0627\u0646\u06af\u06cc\u0646",
)
_BELOW_TERMS = (
    "below average",
    "lower than average",
    "less than average",
    "\u067e\u0627\u06cc\u06cc\u0646\u200c\u062a\u0631 \u0627\u0632 \u0645\u06cc\u0627\u0646\u06af\u06cc\u0646",
    "\u06a9\u0645\u062a\u0631 \u0627\u0632 \u0645\u06cc\u0627\u0646\u06af\u06cc\u0646",
)
_RATE_TERMS = (
    "rate",
    "percentage",
    "percent",
    "\u062f\u0631\u0635\u062f",
    "\u0646\u0631\u062e",
)
_GROUP_TERMS = (
    "grouped by",
    "breakdown",
    "break down",
    "for each",
    "\u0628\u0647 \u062a\u0641\u06a9\u06cc\u06a9",
    "\u0628\u0631 \u0627\u0633\u0627\u0633",
    "\u0628\u0631\u0627\u06cc \u0647\u0631",
)
_CHANGE_TERMS = (
    "change",
    "increase",
    "decrease",
    "difference",
    "delta",
    "\u062a\u063a\u06cc\u06cc\u0631",
    "\u0627\u0641\u0632\u0627\u06cc\u0634",
    "\u06a9\u0627\u0647\u0634",
    "\u0627\u062e\u062a\u0644\u0627\u0641",
)
_BINNING_TERMS = (
    "quartile",
    "percentile",
    "ntile",
    "\u0686\u0647\u0627\u0631\u06a9",
    "\u067e\u0631\u0633\u0646\u062a\u0627\u06cc\u0644",
)
_TOP_BOTTOM_TERMS = (
    "top",
    "highest",
    "lowest",
    "most",
    "least",
    "\u0628\u06cc\u0634\u062a\u0631\u06cc\u0646",
    "\u06a9\u0645\u062a\u0631\u06cc\u0646",
)
_RISK_TERMS = (
    "risk",
    "mental_health_risk",
    "\u0631\u06cc\u0633\u06a9",
)
_STRESS_TERMS = (
    "stress",
    "\u0627\u0633\u062a\u0631\u0633",
)
_SLEEP_TERMS = (
    "sleep",
    "\u062e\u0648\u0627\u0628",
)
_COMPARATIVE_TERMS = (
    "more",
    "higher",
    "greater",
    "increase",
    "compare",
    "compared",
    "\u0628\u06cc\u0634\u062a\u0631",
    "\u0628\u0627\u0644\u0627\u062a\u0631",
    "\u0645\u0642\u0627\u06cc\u0633\u0647",
)


def analyze_question_sql_consistency(question: str | None, sql: str | None) -> SqlConsistencyReport:
    """Check broad question-to-SQL obligations without using gold labels.

    This critic is intentionally conservative. It only checks explicit obligations
    that can be inferred from the user's question text and the generated SQL text.
    It must not be used to encode benchmark case IDs or reference SQL templates.
    """

    q = _norm(question)
    s = _norm(sql)
    issues: list[SqlConsistencyIssue] = []

    if not q or not s:
        return SqlConsistencyReport(passed=True, issues=issues)

    if _has_any(q, _RATE_TERMS) and not _looks_like_rate_sql(s):
        issues.append(
            SqlConsistencyIssue(
                code="QUESTION_SQL_MISSING_RATE_COMPUTATION",
                message="Question asks for a rate/percentage but SQL does not compute an explicit rate.",
            )
        )

    if _has_any(q, _GROUP_TERMS) and not _looks_like_segmented_sql(s):
        issues.append(
            SqlConsistencyIssue(
                code="QUESTION_SQL_MISSING_GROUPING",
                message="Question asks for a grouped or per-segment result but SQL has no GROUP BY.",
            )
        )

    if (_has_any(q, _ABOVE_TERMS) or _has_any(q, _BELOW_TERMS)) and not _looks_like_average_threshold_filter(s):
        issues.append(
            SqlConsistencyIssue(
                code="QUESTION_SQL_MISSING_AVERAGE_THRESHOLD",
                message="Question asks for above/below-average filtering but SQL does not compute an AVG threshold.",
            )
        )

    if _asks_risk_average_profile(q):
        if "group by mental_health_risk" not in s:
            issues.append(
                SqlConsistencyIssue(
                    code="QUESTION_SQL_MISSING_RISK_GROUPING",
                    message="Question asks for a risk summary/profile but SQL does not group by mental_health_risk.",
                )
            )
        if "count(" not in s:
            issues.append(
                SqlConsistencyIssue(
                    code="QUESTION_SQL_MISSING_RISK_COUNT",
                    message="Risk summary questions should include COUNT(*) so the result size is visible.",
                )
            )
        if not _selects_average_for(s, "stress_level") or not _selects_average_for(s, "sleep_hours"):
            issues.append(
                SqlConsistencyIssue(
                    code="QUESTION_SQL_MISSING_RISK_CONTEXT_AVERAGES",
                    message="Risk summary for stress/sleep threshold questions should include AVG(stress_level) and AVG(sleep_hours).",
                )
            )

    if _asks_comparative_question(q) and _looks_like_single_group_filter_without_comparator(s):
        issues.append(
            SqlConsistencyIssue(
                code="QUESTION_SQL_MISSING_COMPARISON_BASELINE",
                message="Comparative questions need a comparison baseline or grouped comparison, not only a single filtered group.",
            )
        )

    if _has_any(q, _CHANGE_TERMS) and not _looks_like_change_sql(s):
        issues.append(
            SqlConsistencyIssue(
                code="QUESTION_SQL_MISSING_CHANGE_MEASURE",
                message="Question asks for change/difference but SQL does not compute an explicit change measure.",
            )
        )

    if _has_any(q, _BINNING_TERMS) and not _looks_like_binning_sql(s):
        issues.append(
            SqlConsistencyIssue(
                code="QUESTION_SQL_MISSING_BINNING",
                message="Question asks for quartile/percentile-style binning but SQL has no binning construct.",
            )
        )

    if _has_any(q, _TOP_BOTTOM_TERMS) and "order by" not in s:
        issues.append(
            SqlConsistencyIssue(
                code="QUESTION_SQL_MISSING_ORDERING",
                message="Question asks for top/bottom/highest/lowest rows but SQL has no ORDER BY.",
                severity="warning",
            )
        )

    hard_issues = [issue for issue in issues if issue.severity == "error"]
    return SqlConsistencyReport(passed=not hard_issues, issues=issues)


def _norm(value: str | None) -> str:
    return " ".join(str(value or "").lower().replace("\u200c", " ").split())


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _looks_like_rate_sql(sql: str) -> bool:
    return (
        "100" in sql
        and ("avg(" in sql or "sum(" in sql or "count(" in sql)
    ) or "rate" in sql or "pct" in sql or "percent" in sql


def _looks_like_change_sql(sql: str) -> bool:
    if " lag(" in f" {sql}" or " lead(" in f" {sql}":
        return True
    if " - " in sql or "-" in sql.replace("->", ""):
        return any(term in sql for term in ("change", "delta", "diff", "latest", "baseline", "1990"))
    return False


def _looks_like_binning_sql(sql: str) -> bool:
    return any(term in sql for term in ("ntile(", "percent_rank(", "cume_dist(", "quartile"))


def _selects_average_for(sql: str, column: str) -> bool:
    select_clause = sql.split(" from ", 1)[0]
    return f"avg({column}" in select_clause


def _looks_like_average_threshold_filter(sql: str) -> bool:
    for marker in (" where ", " having "):
        if marker in f" {sql} ":
            predicate = f" {sql} ".split(marker, 1)[1]
            if "avg(" in predicate:
                return True
    return False


def _asks_risk_average_profile(question: str) -> bool:
    return (
        _has_any(question, _RISK_TERMS)
        and _has_any(question, _STRESS_TERMS)
        and _has_any(question, _SLEEP_TERMS)
        and (_has_any(question, _ABOVE_TERMS) or _has_any(question, _BELOW_TERMS))
    )


def _looks_like_segmented_sql(sql: str) -> bool:
    return "group by" in sql or "partition by" in sql


def _asks_comparative_question(question: str) -> bool:
    return _has_any(question, _COMPARATIVE_TERMS)


def _looks_like_single_group_filter_without_comparator(sql: str) -> bool:
    has_single_risk_filter = (
        "where mental_health_risk =" in sql
        or "where mental_health_risk='" in sql
        or 'where mental_health_risk="' in sql
    )
    has_comparator = (
        "group by" in sql
        or " union " in f" {sql} "
        or " over " in f" {sql} "
        or "(select avg(" in sql
        or "( select avg(" in sql
    )
    return has_single_risk_filter and not has_comparator
