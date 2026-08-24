from __future__ import annotations

from typing import Any
import re

from src.core.query_ir import QueryIR
from src.sql_validation.validation_result import ValidationIssue, ValidationResult


_DASHBOARD_TERMS = (
    "dashboard",
    "story",
    "\u062f\u0627\u0634\u0628\u0648\u0631\u062f",
    "\u062f\u0627\u0633\u062a\u0627\u0646",
    "\u0631\u0648\u0627\u06cc\u062a",
)
_CHANGE_TERMS = (
    "change",
    "delta",
    "\u062a\u063a\u06cc\u06cc\u0631",
    "\u0627\u0641\u0632\u0627\u06cc\u0634",
    "\u06a9\u0627\u0647\u0634",
)
_QUANTILE_TERMS = (
    "quartile",
    "percentile",
    "ntile",
    "\u0686\u0647\u0627\u0631\u06a9",
    "\u0635\u062f\u06a9",
)
_RISK_TERMS = ("risk", "mental_health_risk", "\u0631\u06cc\u0633\u06a9")
_MENTAL_HEALTH_RISK_TERMS = (
    "mental_health_risk",
    "mental health risk",
    "\u0631\u06cc\u0633\u06a9 \u0633\u0644\u0627\u0645\u062a \u0631\u0648\u0627\u0646",
    "\u0633\u0637\u062d \u0631\u06cc\u0633\u06a9",
)
_AVERAGE_TERMS = (
    "average",
    "mean",
    "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646",
    "\u0628\u0627\u0644\u0627\u062a\u0631",
    "\u067e\u0627\u06cc\u06cc\u0646",
)
_STRESS_TERMS = ("stress", "\u0627\u0633\u062a\u0631\u0633")
_SLEEP_TERMS = ("sleep", "\u062e\u0648\u0627\u0628")
_BY_GROUP_TERMS = (" by ", "based on", "\u0628\u0631 \u0627\u0633\u0627\u0633")
_RATE_TERMS = (
    "rate",
    "percent",
    "percentage",
    "\u0646\u0631\u062e",
    "\u062f\u0631\u0635\u062f",
)
_DEPRESSION_TERMS = ("depression", "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc")
_GROUPING_TERMS = (
    "distribution",
    "group by",
    " by ",
    "based on",
    "per ",
    "\u062a\u0648\u0632\u06cc\u0639",
    "\u0628\u0647 \u062a\u0641\u06a9\u06cc\u06a9",
    "\u0628\u0631 \u0627\u0633\u0627\u0633",
    "\u062f\u0631 \u0647\u0631",
    "\u0647\u0631 ",
)
_TWO_SIDED_TERMS = (
    "\u0628\u0627 \u0648 \u0628\u062f\u0648\u0646",
    "\u062f\u0627\u0631\u0627\u06cc \u0648 \u0628\u062f\u0648\u0646",
    "\u0627\u0641\u0633\u0631\u062f\u0647 \u0648 \u063a\u06cc\u0631\u0627\u0641\u0633\u0631\u062f\u0647",
    "with and without",
    "depressed and non-depressed",
    "depressed and non depressed",
)
_MULTI_DIM_TERMS = (
    "\u062a\u0631\u06a9\u06cc\u0628",
    "\u0645\u0627\u062a\u0631\u06cc\u0633",
    "matrix",
    "combination",
)
_DISORDER_TERMS = (
    "eating_disorder",
    "depression",
    "anxiety",
    "bipolar",
    "schizophrenia",
)
_MATRIX_TERMS = ("matrix", "\u0645\u0627\u062a\u0631\u06cc\u0633")
_DIET_TERMS = (
    "diet",
    "dietary",
    "\u0631\u0698\u06cc\u0645",
    "\u063a\u0630\u0627\u06cc\u06cc",
)
_CGPA_TERMS = ("cgpa", "gpa")
_RANKING_TERMS = (
    "rank",
    "ranking",
    "top",
    "highest",
    "lowest",
    "best",
    "worst",
    "most",
    "least",
    "\u0631\u062a\u0628\u0647",
    "\u0628\u0631\u062a\u0631",
    "\u0628\u06cc\u0634\u062a\u0631\u06cc\u0646",
    "\u06a9\u0645\u062a\u0631\u06cc\u0646",
    "\u0628\u0627\u0644\u0627\u062a\u0631\u06cc\u0646",
    "\u067e\u0627\u06cc\u06cc\u0646\u200c\u062a\u0631\u06cc\u0646",
)
_TOP_N_TERMS = (
    "top",
    "highest",
    "lowest",
    "best",
    "worst",
    "most",
    "least",
    "\u0628\u0631\u062a\u0631",
    "\u0628\u06cc\u0634\u062a\u0631\u06cc\u0646",
    "\u06a9\u0645\u062a\u0631\u06cc\u0646",
    "\u0628\u0627\u0644\u0627\u062a\u0631\u06cc\u0646",
    "\u067e\u0627\u06cc\u06cc\u0646\u200c\u062a\u0631\u06cc\u0646",
)


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _compact(sql: str) -> str:
    return " ".join((sql or "").lower().replace("\n", " ").split())


def _has_not_null_filter(sql: str, column: str) -> bool:
    compact = re.sub(r"\s+", "", sql.lower())
    col = re.escape(column.lower())
    return bool(
        re.search(col + r"isnotnull", compact)
        or re.search(r"not" + col + r"isnull", compact)
        or re.search(r"not\(" + col + r"isnull\)", compact)
    )


def _select_clause(sql: str) -> str:
    return sql.split(" from ", 1)[0]


def _selects_column(sql: str, column: str) -> bool:
    return column.lower() in _select_clause(sql)


def _has_group_by(sql: str) -> bool:
    return bool(re.search(r"\bgroup\s+by\b", sql))


def _has_order_by(sql: str) -> bool:
    return bool(re.search(r"\border\s+by\b", sql))


def _has_limit(sql: str) -> bool:
    return bool(re.search(r"\blimit\b", sql))


def _group_by_fragment(sql: str) -> str:
    match = re.search(
        r"\bgroup\s+by\b(?P<body>.*?)(\border\s+by\b|\bhaving\b|\blimit\b|$)", sql, re.S
    )
    if not match:
        return ""
    return match.group("body").strip()


def _group_by_count(sql: str) -> int:
    fragment = _group_by_fragment(sql)
    if not fragment:
        return 0
    return max(1, len([part for part in fragment.split(",") if part.strip()]))


def _has_aggregate(sql: str) -> bool:
    return bool(re.search(r"\b(count|avg|sum|min|max)\s*\(", sql))


def _has_rate_formula(sql: str, metrics: list[str]) -> bool:
    if "100" not in sql and "rate" not in sql and "pct" not in sql:
        return False
    if re.search(r"\bavg\s*\(", sql):
        return True
    if re.search(r"\bsum\s*\([^)]*\)\s*/\s*count\s*\(", sql):
        return True
    if metrics:
        return any(metric.lower() in sql and ("avg(" in sql or "sum(" in sql) for metric in metrics)
    return "sum(" in sql or "avg(" in sql


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


def _add(issues: list[ValidationIssue], code: str, message: str, severity: str = "error") -> None:
    issues.append(ValidationIssue(code=code, message=message, severity=severity))


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
        self._validate_generic_qir_shape(lower_sql, lower_question, task_type, qir, issues)
        self._validate_global_change_shape(lower_sql, lower_question, task_type, schema, issues)
        self._validate_risk_summary_shape(lower_sql, lower_question, schema, issues)
        self._validate_grouped_rate_shape(lower_sql, lower_question, task_type, schema, issues)
        self._validate_student_sleep_diet_matrix_shape(
            lower_sql, lower_question, task_type, schema, issues
        )

        has_errors = any(issue.severity == "error" for issue in issues)
        return ValidationResult(not has_errors, issues, sql)

    def _validate_sqlite_dialect(self, sql: str, issues: list[ValidationIssue]) -> None:
        if "percentile_cont" in sql or " within group " in f" {sql} ":
            _add(
                issues,
                "UNSUPPORTED_SQLITE_ANALYTIC_FUNCTION",
                "SQLite does not support PERCENTILE_CONT or WITHIN GROUP. Use NTILE(4) or grouped bins for quartile/percentile-style summaries.",
            )

    def _validate_generic_qir_shape(
        self,
        sql: str,
        question: str,
        task_type: str,
        qir: QueryIR | None,
        issues: list[ValidationIssue],
    ) -> None:
        dimensions = [str(dim).lower() for dim in (getattr(qir, "dimensions", []) or [])]
        metrics = [str(metric).lower() for metric in (getattr(qir, "metrics", []) or [])]
        expected_shape = str(getattr(qir, "expected_result_shape", "") or "").lower()
        asks_grouping = (
            expected_shape == "table"
            or bool(dimensions)
            or task_type
            in {
                "grouping_query",
                "comparison_query",
                "ranking_query",
                "trend_query",
                "rate_query",
            }
            or _has_any(question, _GROUPING_TERMS)
            or _has_any(question, _TWO_SIDED_TERMS)
        )
        if task_type == "raw_retrieval_query":
            if not _has_limit(sql):
                _add(
                    issues,
                    "ANALYTICAL_SHAPE_MISSING_RAW_ROW_LIMIT",
                    "Raw row/list queries must include LIMIT to avoid unbounded row-level output.",
                )
            if _has_group_by(sql):
                _add(
                    issues,
                    "ANALYTICAL_SHAPE_RAW_ROWS_SHOULD_NOT_GROUP",
                    "Raw row/list queries should return bounded records, not grouped aggregates.",
                )
            return

        if asks_grouping and _has_aggregate(sql) and not _has_group_by(sql):
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_GROUP_BY",
                "This question asks for grouped/tabular analysis, but the SQL collapses the answer to a scalar aggregate. Include the requested dimension in SELECT and GROUP BY.",
            )

        asks_rate = task_type == "rate_query" or _has_any(question, _RATE_TERMS)
        if asks_rate and not _has_rate_formula(sql, metrics):
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RATE_FORMULA",
                "Rate/percentage questions must compute a numerator over COUNT(*) or AVG(binary_flag), not only COUNT(*).",
            )

        two_sided = _has_any(question, _TWO_SIDED_TERMS)
        single_sided_depression_filter = bool(
            re.search(r"\bwhere\b[^;]*(depression_flag|depression_diagnosis)\s*=\s*[01]", sql)
            or re.search(
                r"\bwhere\b[^;]*(part_time_job|treatment|seeks_treatment)\s*=\s*[01]",
                sql,
            )
        )
        if two_sided and single_sided_depression_filter and not _has_group_by(sql):
            _add(
                issues,
                "ANALYTICAL_SHAPE_SINGLE_SIDED_COMPARISON",
                "Two-sided comparison questions such as 'with and without' must group by the binary column instead of filtering to only one side.",
            )

        asks_multi_dim = (
            _has_any(question, _MULTI_DIM_TERMS)
            or question.count("\u0628\u0647 \u062a\u0641\u06a9\u06cc\u06a9") >= 1
            and "\u0648" in question
        )
        if asks_multi_dim and _has_group_by(sql) and _group_by_count(sql) < 2:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_MULTI_DIMENSION_GROUPING",
                "Multi-dimensional/matrix questions must GROUP BY at least two dimensions.",
            )

        asks_ranking = task_type == "ranking_query" or _has_any(question, _RANKING_TERMS)
        if asks_ranking and not _has_order_by(sql):
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RANKING_ORDER_BY",
                "Ranking/top-N questions must include ORDER BY on the ranking metric.",
            )
        if asks_ranking and _has_any(question, _TOP_N_TERMS) and not _has_limit(sql):
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RANKING_LIMIT",
                "Top/highest/lowest ranking questions must include LIMIT for the requested top-N slice.",
            )

        if dimensions and _has_group_by(sql):
            group_fragment = _group_by_fragment(sql)
            missing_dimensions = [
                dim
                for dim in dimensions
                if dim not in group_fragment and dim in sql and not dim.endswith("_flag")
            ]
            if missing_dimensions:
                _add(
                    issues,
                    "ANALYTICAL_SHAPE_GROUP_BY_DIMENSION_MISMATCH",
                    "The SQL references requested dimensions but does not include them in GROUP BY: "
                    + ", ".join(missing_dimensions),
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
        asks_stress_sleep_thresholds = _has_any(question, _STRESS_TERMS) and _has_any(
            question, _SLEEP_TERMS
        )
        asks_explicit_mental_health_risk_group = _has_any(
            question, _MENTAL_HEALTH_RISK_TERMS
        ) and _has_any(f" {question} ", _BY_GROUP_TERMS)
        asks_grouped_risk_profile = (
            asks_stress_sleep_thresholds or asks_explicit_mental_health_risk_group
        )

        if asks_grouped_risk_profile and "group by mental_health_risk" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RISK_GROUPING",
                "Risk-profile questions must summarize by GROUP BY mental_health_risk instead of returning row-level risk values.",
            )
        if asks_grouped_risk_profile and not _selects_column(sql, "mental_health_risk"):
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
        if asks_stress_sleep_thresholds and (
            "avg(stress_level" not in sql or "avg(sleep_hours" not in sql
        ):
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RISK_AVERAGES",
                "Risk summary SQL should include AVG(stress_level) and AVG(sleep_hours) for the filtered population.",
            )
        if asks_stress_sleep_thresholds and not (
            re.search(r"stress_level\s*>", sql)
            and "avg(stress_level" in sql
            and re.search(r"sleep_hours\s*<", sql)
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
                severity="warning",
            )
        if not _has_not_null_filter(sql, "sleep_duration_category"):
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_NULL_FILTER",
                "Grouped sleep-rate SQL must filter WHERE sleep_duration_category IS NOT NULL to avoid a null bucket.",
                severity="warning",
            )
        if "sum(depression_flag)" not in sql and "avg(depression_flag)" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RATE_NUMERATOR",
                "Grouped depression-rate SQL must compute the rate from depression_flag.",
            )
        if "rate_pct" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_RATE_ALIAS",
                "Grouped rate SQL must include a rate_pct output column.",
            )

    def _validate_student_sleep_diet_matrix_shape(
        self,
        sql: str,
        question: str,
        task_type: str,
        schema: dict[str, Any] | None,
        issues: list[ValidationIssue],
    ) -> None:
        student_cols = _table_columns(schema, "student_depression")
        required_cols = {
            "sleep_duration_category",
            "dietary_habits",
            "depression_flag",
            "cgpa_10",
        }
        if not required_cols.issubset(student_cols):
            return
        asks_matrix = (
            (task_type == "grouping_query" or _has_any(question, _MATRIX_TERMS))
            and _has_any(question, _SLEEP_TERMS)
            and _has_any(question, _DIET_TERMS)
            and _has_any(question, _DEPRESSION_TERMS)
            and _has_any(question, _CGPA_TERMS)
        )
        if not asks_matrix:
            return

        if "from student_depression" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_STUDENT_DEPRESSION_TABLE",
                "Sleep/diet depression-CGPA matrix questions should use student_depression.",
            )
        if "sleep_duration_category" not in sql or "dietary_habits" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_SLEEP_DIET_KEYS",
                "Sleep/diet matrix SQL must group by sleep_duration_category and dietary_habits, not columns from another table.",
            )
        if "sleep_hours" in sql or "diet_quality" in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_WRONG_TABLE_SLEEP_DIET_COLUMNS",
                "Do not use sleep_hours or diet_quality with student_depression; use sleep_duration_category and dietary_habits.",
            )
        if "depression_flag" not in sql or "depression_rate" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_DEPRESSION_RATE",
                "Sleep/diet matrix SQL must include a depression rate computed from depression_flag.",
            )
        if "cgpa_10" not in sql or "avg" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_AVG_CGPA",
                "Sleep/diet matrix SQL must include AVG(cgpa_10).",
            )
        if not _has_min_support_threshold(sql, minimum=50):
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_MATRIX_SUPPORT_THRESHOLD",
                "Sleep/diet matrix SQL must include HAVING COUNT(*) >= 50 to suppress unstable sparse cells.",
            )
        if "order by depression_rate_pct desc" not in sql:
            _add(
                issues,
                "ANALYTICAL_SHAPE_MISSING_PRIMARY_METRIC_SORT",
                "Sleep/diet matrix SQL must sort by the primary requested metric: ORDER BY depression_rate_pct DESC.",
            )


def _has_min_support_threshold(sql: str, *, minimum: int) -> bool:
    compact = sql.replace(" ", "")
    if re.search(r"havingcount\(\*\)>=" + str(minimum), compact):
        return True
    if re.search(r"havingcount\(\*\)>" + str(minimum - 1), compact):
        return True
    return False
