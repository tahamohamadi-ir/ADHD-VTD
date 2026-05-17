from __future__ import annotations

from typing import Any

from src.core.query_ir import QueryIR
from src.sql_validation.validation_result import ValidationIssue, ValidationResult


_DASHBOARD_TERMS = ("dashboard", "story", "\u062f\u0627\u0634\u0628\u0648\u0631\u062f", "\u062f\u0627\u0633\u062a\u0627\u0646", "\u0631\u0648\u0627\u06cc\u062a")
_CHANGE_TERMS = ("change", "delta", "\u062a\u063a\u06cc\u06cc\u0631", "\u0627\u0641\u0632\u0627\u06cc\u0634", "\u06a9\u0627\u0647\u0634")
_QUANTILE_TERMS = ("quartile", "percentile", "ntile", "\u0686\u0647\u0627\u0631\u06a9", "\u0635\u062f\u06a9")
_RISK_TERMS = ("risk", "mental_health_risk", "\u0631\u06cc\u0633\u06a9")
_AVERAGE_TERMS = ("average", "mean", "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646", "\u0628\u0627\u0644\u0627\u062a\u0631", "\u067e\u0627\u06cc\u06cc\u0646")
_STRESS_TERMS = ("stress", "\u0627\u0633\u062a\u0631\u0633")
_SLEEP_TERMS = ("sleep", "\u062e\u0648\u0627\u0628")
_BY_GROUP_TERMS = (" by ", "based on", "\u0628\u0631 \u0627\u0633\u0627\u0633")
_RATE_TERMS = ("rate", "percent", "percentage", "\u0646\u0631\u062e", "\u062f\u0631\u0635\u062f")
_DEPRESSION_TERMS = ("depression", "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc")
_DISORDER_TERMS = ("eating_disorder", "depression", "anxiety", "bipolar", "schizophrenia")


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _compact(sql: str) -> str:
    return " ".join((sql or "").lower().replace("\n", " ").split())


def _table_columns(schema: dict[str, Any] | None, table_name: str) -> set[str]:
    if not schema:
        return set()
    table = schema.get(table_name)
    if table is None:
        columns = []
    elif isinstance(table, dict):
        columns = table.get("columns", [])
    else:
        columns = getattr(table, "columns", [])
    if isinstance(columns, dict):
        return {str(name).lower() for name in columns}
    names: set[str] = set()
    for col in columns:
        if isinstance(col, dict):
            name = col.get("name") or col.get("column") or col.get("column_name")
        else:
            name = getattr(col, "name", "")
        if name:
            names.add(str(name).lower())
    return names


def _add(issues: list[ValidationIssue], code: str, message: str) -> None:
    issues.append(ValidationIssue(code=code, message=message, severity="error"))


class SQLShapeValidator:
    """Conservative SQL shape checks derived from question, intent, schema and SQLite.

    This validator intentionally avoids gold SQL. It catches cases where SQL is valid
    but clearly violates a defensible output-shape contract for the user request.
    """

    def validate(
        self,
        sql: str,
        *,
        question: str,
        qir: QueryIR | None = None,
        schema: dict[str, Any] | None = None,
    ) -> ValidationResult:
        lower_sql = _compact(sql)
        lower_question = (question or "").lower()
        task_type = str(getattr(qir, "task_type", "") or "").lower()
        issues: list[ValidationIssue] = []

        self._validate_sqlite_dialect(lower_sql, issues)
        self._validate_global_change_shape(lower_sql, lower_question, task_type, schema, issues)
        self._validate_risk_summary_shape(lower_sql, lower_question, schema, issues)
        self._validate_grouped_rate_shape(lower_sql, lower_question, task_type, schema, issues)

        return ValidationResult(not issues, issues, sql)

    def _validate_sqlite_dialect(self, sql: str, issues: list[ValidationIssue]) -> None:
        if "percentile_cont" in sql or " within group " in f" {sql} ":
            _add(
                issues,
                "UNSUPPORTED_SQLITE_ANALYTIC_FUNCTION",
                "SQLite does not support PERCENTILE_CONT or WITHIN GROUP. Use NTILE(4) or grouped bins for quartile/percentile-style summaries.",
            )

    def _validate_global_change_shape(
        self,
        sql: str,
        question: str,
        task_type: str,
        schema: dict[str, Any] | None,
        issues: list[ValidationIssue],
    ) -> None:
        has_prevalence_long = bool(_table_columns(schema, "country_prevalence_long"))
        asks_change = _has_any(question, _CHANGE_TERMS)
        asks_dashboard = task_type == "grouping_query" or _has_any(question, _DASHBOARD_TERMS)
        asks_bins = _has_any(question, _QUANTILE_TERMS)
        names_disorder = _has_any(question, _DISORDER_TERMS)
        if not (has_prevalence_long and asks_change and asks_dashboard and names_disorder):
            return

        if "country_prevalence_long" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_LONG_PREVALENCE_TABLE",
                "Global named-disorder change dashboards must use country_prevalence_long with disorder/prevalence_pct, not a latest-year scalar from country_prevalence_wide.",
            )
        if "disorder" not in sql or "prevalence_pct" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_PREVALENCE_LONG_COLUMNS",
                "Global named-disorder change SQL must filter disorder and compute over prevalence_pct from country_prevalence_long.",
            )
        if "-" not in sql or "change" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_CHANGE_MEASURE",
                "Change questions must compute an explicit latest-minus-baseline change measure before summarizing.",
            )
        if asks_bins and "ntile" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_BINNING",
                "Percentile/quartile-style change dashboards must use SQLite-supported binning such as NTILE(4), not a single scalar aggregate.",
            )

    def _validate_risk_summary_shape(
        self,
        sql: str,
        question: str,
        schema: dict[str, Any] | None,
        issues: list[ValidationIssue],
    ) -> None:
        general_cols = _table_columns(schema, "mental_health_general")
        if not {"mental_health_risk", "stress_level", "sleep_hours"}.issubset(general_cols):
            return
        asks_risk_average = _has_any(question, _RISK_TERMS) and _has_any(question, _AVERAGE_TERMS)
        if not asks_risk_average:
            return
        asks_stress_sleep_thresholds = _has_any(question, _STRESS_TERMS) and _has_any(question, _SLEEP_TERMS)
        asks_grouped_risk_profile = asks_stress_sleep_thresholds or _has_any(f" {question} ", _BY_GROUP_TERMS)

        if asks_grouped_risk_profile and "group by mental_health_risk" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RISK_GROUPING",
                "Risk-profile questions must summarize by GROUP BY mental_health_risk instead of returning row-level risk values.",
            )
        if asks_grouped_risk_profile and "select mental_health_risk" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RISK_KEY",
                "Risk-profile SQL must include mental_health_risk in the SELECT list as the grouping key.",
            )
        if asks_stress_sleep_thresholds and ("count(" not in sql or " as n" not in sql):
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RISK_COUNT",
                "Risk summary SQL must include COUNT(*) AS n so the result explains how many records are in each risk group.",
            )
        if asks_stress_sleep_thresholds and ("avg(stress_level" not in sql or "avg(sleep_hours" not in sql):
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RISK_AVERAGES",
                "Risk summary SQL should include AVG(stress_level) and AVG(sleep_hours) for the filtered population.",
            )
        if asks_stress_sleep_thresholds and not (
            "stress_level >" in sql
            and "avg(stress_level" in sql
            and "sleep_hours <" in sql
            and "avg(sleep_hours" in sql
        ):
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RISK_AVERAGE_FILTERS",
                "Risk-above/below-average questions must filter stress_level above its average and sleep_hours below its average before grouping.",
            )

    def _validate_grouped_rate_shape(
        self,
        sql: str,
        question: str,
        task_type: str,
        schema: dict[str, Any] | None,
        issues: list[ValidationIssue],
    ) -> None:
        student_cols = _table_columns(schema, "student_depression")
        if not {"sleep_duration_category", "depression_flag"}.issubset(student_cols):
            return
        asks_sleep_rate = (
            task_type == "rate_query"
            and _has_any(question, _SLEEP_TERMS)
            and (_has_any(question, _RATE_TERMS) or _has_any(question, _DEPRESSION_TERMS))
        )
        if not asks_sleep_rate:
            return

        if "sleep_duration_category as group_value" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_GROUP_ALIAS",
                "Grouped sleep-rate SQL must expose sleep_duration_category AS group_value for stable benchmark/report columns.",
            )
        if "sleep_duration_category is not null" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_NULL_FILTER",
                "Grouped sleep-rate SQL must filter WHERE sleep_duration_category IS NOT NULL to avoid a null bucket.",
            )
        if "sum(depression_flag)" not in sql or "positives" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_POSITIVES",
                "Grouped depression-rate SQL must include SUM(depression_flag) AS positives.",
            )
        if "rate_pct" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RATE_ALIAS",
                "Grouped rate SQL must include a rate_pct output column.",
            )
