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

    if _has_any(q, _GROUP_TERMS) and "group by" not in s:
        issues.append(
            SqlConsistencyIssue(
                code="QUESTION_SQL_MISSING_GROUPING",
                message="Question asks for a grouped or per-segment result but SQL has no GROUP BY.",
            )
        )

    if (_has_any(q, _ABOVE_TERMS) or _has_any(q, _BELOW_TERMS)) and "avg(" not in s:
        issues.append(
            SqlConsistencyIssue(
                code="QUESTION_SQL_MISSING_AVERAGE_THRESHOLD",
                message="Question asks for above/below-average filtering but SQL does not compute an AVG threshold.",
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
