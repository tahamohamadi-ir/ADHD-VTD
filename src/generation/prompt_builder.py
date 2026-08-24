from pathlib import Path
from typing import Any
from jinja2 import Environment, FileSystemLoader

from src.core.query_ir import QueryIR


import re

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
_RATE_TERMS = (
    "rate",
    "percentage",
    "percent",
    "_pct",
    "\u0646\u0631\u062e",
    "\u062f\u0631\u0635\u062f",
)
_RISK_TERMS = (
    "risk",
    "mental_health_risk",
    "\u0631\u06cc\u0633\u06a9",
)
_AVERAGE_COMPARISON_TERMS = (
    "average",
    "mean",
    "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646",
    "\u0628\u0627\u0644\u0627\u062a\u0631",
    "\u067e\u0627\u06cc\u06cc\u0646",
)
_FAMILY_HISTORY_TERMS = (
    "family history",
    "family_history",
    "\u0633\u0627\u0628\u0642\u0647 \u062e\u0627\u0646\u0648\u0627\u062f\u06af\u06cc",
)
_MATRIX_TERMS = ("matrix", "\u0645\u0627\u062a\u0631\u06cc\u0633")
_SLEEP_TERMS = ("sleep", "\u062e\u0648\u0627\u0628")
_DIET_TERMS = (
    "diet",
    "dietary",
    "\u0631\u0698\u06cc\u0645",
    "\u063a\u0630\u0627\u06cc\u06cc",
)
_DEPRESSION_TERMS = (
    "depression",
    "depressed",
    "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc",
    "\u0627\u0641\u0633\u0631\u062f\u0647",
)
_CGPA_TERMS = ("cgpa", "gpa")
_MENTAL_HEALTH_GENERAL_TERMS = (
    "mental health",
    "\u0633\u0644\u0627\u0645\u062a \u0631\u0648\u0627\u0646",
    "\u0633\u0644\u0627\u0645\u062a \u0631\u0648\u0627\u0646\u06cc",
)
_DISORDER_NAME_TERMS = (
    "depression",
    "anxiety",
    "bipolar",
    "schizophrenia",
    "eating_disorder",
    "eating disorder",
    "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc",
    "\u0627\u0636\u0637\u0631\u0627\u0628",
    "\u062f\u0648\u0642\u0637\u0628\u06cc",
    "\u0627\u0633\u06a9\u06cc\u0632\u0648\u0641\u0631\u0646\u06cc",
    "\u0627\u062e\u062a\u0644\u0627\u0644 \u062e\u0648\u0631\u062f\u0646",
)
_DISORDER_GROUP_TERMS = (
    "each disorder",
    "by disorder",
    "\u0647\u0631 \u0627\u062e\u062a\u0644\u0627\u0644",
    "\u0627\u0632 \u0647\u0631 \u0627\u062e\u062a\u0644\u0627\u0644",
    "\u0628\u0647 \u062a\u0641\u06a9\u06cc\u06a9 \u0627\u062e\u062a\u0644\u0627\u0644",
)
_GROUPING_TERMS = (
    "distribution",
    "breakdown",
    "group by",
    " by ",
    "based on",
    "per ",
    "category",
    "categories",
    "compare",
    "comparison",
    "\u062a\u0648\u0632\u06cc\u0639",
    "\u0628\u0647 \u062a\u0641\u06a9\u06cc\u06a9",
    "\u0628\u0631 \u0627\u0633\u0627\u0633",
    "\u062f\u0633\u062a\u0647",
    "\u06af\u0631\u0648\u0647",
    "\u0645\u0642\u0627\u06cc\u0633\u0647",
    "\u0647\u0631 ",
)
_SCALAR_TASK_TYPES = {"count_query", "aggregation_query", "rate_query"}
_GROUPED_TASK_TYPES = {"grouping_query", "comparison_query"}
_GENERIC_SHAPE_TASK_TYPES = {"ranking_query", "raw_retrieval_query"}
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


def _table_columns(schema: dict[str, Any], table_name: str) -> set[str]:
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


class PromptBuilder:
    """Builds prompts for LLM generation using Jinja2 templates."""

    def __init__(self, templates_dir: str | Path = "src/generation/prompts") -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def build_sql_generation_prompt(
        self,
        question: str,
        qir: QueryIR,
        schema: dict[str, Any],
        value_links: dict[str, str] | None = None,
        few_shot: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Builds the main SQL generation prompt.
        """
        if few_shot:
            for ex in few_shot:
                if (
                    "thought_process" not in ex
                    or not ex["thought_process"]
                    or ex["thought_process"] == "Generating query for user request."
                ):
                    ex["thought_process"] = self._generate_synthetic_thought(ex.get("sql", ""))
                # If skeleton is missing, we could try to extract it, but usually it is pre-populated in golden examples.
                # Since golden_examples doesn't have it, we'll auto-generate a pseudo-skeleton if missing.
                if "sql_skeleton" not in ex:
                    ex["sql_skeleton"] = re.sub(
                        r"([A-Za-z0-9_]+\.[A-Za-z0-9_]+|[A-Za-z0-9_]+) (?:=|<|>|<=|>=|LIKE) (?:\'([^\']+)\'|\d+)",
                        r"\1 = {value}",
                        ex.get("sql", ""),
                    )

        template_name = self._select_sql_generation_template(question, qir)
        template = self.env.get_template(template_name)

        # Serialize QIR to dict for easier templating if needed, but jinja can access properties
        return template.render(
            question=question,
            qir=qir,
            schema=schema,
            value_links=value_links or {},
            few_shot=few_shot or [],
            analysis_hints=self._build_analysis_hints(question, qir, schema),
            prompt_template_name=template_name,
        )

    def _select_sql_generation_template(self, question: str, qir: QueryIR) -> str:
        task_type = str(qir.task_type or "").lower()
        expected_shape = str(qir.expected_result_shape or "").lower()
        if task_type in _GENERIC_SHAPE_TASK_TYPES or expected_shape in {
            "ranking",
            "raw_rows",
        }:
            return "sql_generation.j2"
        if self._looks_grouped(question, qir):
            return "sql_generation_grouped.j2"
        if self._looks_scalar(question, qir):
            return "sql_generation_scalar.j2"
        return "sql_generation.j2"

    def _looks_grouped(self, question: str, qir: QueryIR) -> bool:
        q = (question or "").lower()
        task_type = str(qir.task_type or "").lower()
        expected_shape = str(qir.expected_result_shape or "").lower()
        return (
            expected_shape == "table"
            or bool(qir.dimensions)
            or task_type in _GROUPED_TASK_TYPES
            or _has_any(q, _GROUPING_TERMS)
            or _has_any(q, _DISORDER_GROUP_TERMS)
        )

    def _looks_scalar(self, question: str, qir: QueryIR) -> bool:
        q = (question or "").lower()
        task_type = str(qir.task_type or "").lower()
        expected_shape = str(qir.expected_result_shape or "").lower()
        if qir.dimensions:
            return False
        if expected_shape in {
            "scalar",
            "single_value",
            "single_value_metric",
            "number",
            "kpi",
        }:
            return True
        if task_type == "count_query":
            return True
        if task_type in _SCALAR_TASK_TYPES:
            non_scalar_cues = (
                _has_any(q, _DASHBOARD_TERMS)
                or _has_any(q, _MATRIX_TERMS)
                or _has_any(q, _CHANGE_TERMS)
                or _has_any(q, _QUANTILE_TERMS)
                or (_has_any(q, _RISK_TERMS) and _has_any(q, _AVERAGE_COMPARISON_TERMS))
            )
            return not non_scalar_cues
        return False

    def _generate_synthetic_thought(self, sql: str) -> str:
        tables = re.findall(r"FROM\s+([a-zA-Z0-9_]+)", sql, re.IGNORECASE)
        joins = re.findall(r"JOIN\s+([a-zA-Z0-9_]+)", sql, re.IGNORECASE)
        all_tables = list(set(tables + joins))

        has_groupby = "GROUP BY" in sql.upper()

        thought = f"1. Identify main tables: {', '.join(all_tables) if all_tables else 'Unknown'}. "

        if has_groupby:
            thought += "2. Query requires grouping (GROUP BY) to summarize metrics. "
        else:
            thought += "2. Query is a simple filter or global aggregation. "

        if "WHERE" in sql.upper():
            thought += "3. Apply specific filters in WHERE clause. "

        thought += "4. Format output columns according to analysis shape hints."

        return thought

    def build_repair_prompt(
        self,
        question: str,
        schema: dict[str, Any],
        qir: Any,
        value_links: dict[str, str],
        previous_sql: str,
        validation_errors: str,
        critic_feedback: str | None = None,
    ) -> str:
        template = self.env.get_template("sql_repair.j2")
        return template.render(
            question=question,
            schema=schema,
            qir=qir,
            value_links=value_links,
            previous_sql=previous_sql,
            validation_errors=validation_errors,
            critic_feedback=critic_feedback,
        )

    def _build_analysis_hints(
        self,
        question: str,
        qir: QueryIR,
        schema: dict[str, Any],
    ) -> list[str]:
        q = (question or "").lower()
        task_type = str(qir.task_type or "").lower()
        schema_tables = set(schema)
        hints: list[str] = []

        hints.append(
            "If you use a CASE WHEN expression in the SELECT clause and also use GROUP BY, "
            "you MUST repeat the entire CASE WHEN expression in the GROUP BY clause."
        )

        if qir.dimensions:
            hints.append(
                "The QIR Dimensions are required output grouping keys, not optional filters. "
                "Include each requested dimension in SELECT and GROUP BY unless the user asks "
                "for raw rows instead of an aggregate."
            )
        if qir.metrics:
            hints.append(
                "The QIR Metrics are the measurement columns. Use them in aggregate formulas "
                "such as COUNT, AVG, SUM, rates, ranks, or gaps according to the question; do "
                "not replace them with unrelated context columns from examples."
            )
        if qir.expected_result_shape == "table":
            hints.append(
                "The expected result shape is a table. Do not answer with one scalar COUNT or "
                "AVG when the question asks for distribution, comparison, ranking, trend, or "
                "grouped rate."
            )

        expected_shape = str(qir.expected_result_shape or "").lower()
        asks_ranking = (
            task_type == "ranking_query"
            or expected_shape == "ranking"
            or _has_any(q, _RANKING_TERMS)
        )
        if asks_ranking:
            hints.append(
                "For ranking questions, define the ranking metric explicitly, include "
                "ORDER BY on that metric, and return the ranked dimension plus the metric. "
                "If the user asks for top/highest/lowest/best/worst/most/least, include "
                "LIMIT for the requested top-N slice; use LIMIT 15 when no N is specified."
            )

        asks_raw_rows = task_type == "raw_retrieval_query" or expected_shape == "raw_rows"
        if asks_raw_rows:
            hints.append(
                "For raw row/list requests, select only explicit non-identifier columns, "
                "never use SELECT *, and include LIMIT 100 unless the user requests a "
                "smaller limit. For sensitive mental-health or personal-information rows, "
                "prefer clarification/refusal or an aggregate summary instead of row-level output."
            )

        if (
            task_type in ("aggregation_query", "rate_query", "grouping_query")
            or _has_any(q, _RATE_TERMS)
            or _has_any(q, _AVERAGE_COMPARISON_TERMS)
            or "sum" in q
            or "avg" in q
            or "min" in q
            or "max" in q
            or "count" in q
        ):
            hints.append(
                "When calculating AVG, SUM, MIN, or MAX, always add a `WHERE column IS NOT NULL` "
                "filter for the aggregated column unless you already have other WHERE conditions."
            )

        if schema:
            hints.append(
                "Do not copy table or column names from examples unless that exact "
                "table and every referenced column are present in the Database Schema "
                "section above. If an example uses a similar concept with a different "
                "column name, map the concept to the current schema column instead."
            )
            if "student_depression" in schema:
                hints.append(
                    "Note: 'دانشجویان افسردگی' or 'student_depression' refers to the table name. "
                    "Do NOT add 'WHERE depression_flag = 1' just because the dataset is named 'depression'. "
                    "Only filter by depression_flag if the user explicitly asks for depressed students (e.g. دانشجویانی که افسردگی دارند)."
                )

        if task_type == "rate_query" or _has_any(q, _RATE_TERMS):
            rate_hint = (
                "For grouped rate questions, return the group key, COUNT(*) AS n, "
                "SUM(binary_flag) AS positives when a binary flag is present, "
                "ROUND(100.0 * SUM(binary_flag) / COUNT(*), 2) AS rate_pct, "
                "an IS NOT NULL filter on the grouping column, ORDER BY rate_pct "
                "DESC, and LIMIT 15 unless the user asks otherwise."
            )
            student_cols = _table_columns(schema, "student_depression")
            if {"depression_flag", "cgpa_10"}.issubset(student_cols):
                rate_hint += (
                    " For student_depression depression-rate groupings, use "
                    "sleep_duration_category AS group_value when grouping by sleep, "
                    "depression_flag as the binary flag, WHERE sleep_duration_category "
                    "IS NOT NULL. Do not add unrelated context columns unless the "
                    "user asks for them."
                )
            hints.append(rate_hint)

        student_cols = _table_columns(schema, "student_depression")
        if _has_any(q, _FAMILY_HISTORY_TERMS) and "family_history_mental_illness" in student_cols:
            hints.append(
                "For family-history questions over student_depression, use "
                "family_history_mental_illness. Do not use family_history unless "
                "that exact column is present in the selected table."
            )

        if (
            _has_any(q, _MATRIX_TERMS)
            and _has_any(q, _SLEEP_TERMS)
            and _has_any(q, _DIET_TERMS)
            and _has_any(q, _DEPRESSION_TERMS)
            and _has_any(q, _CGPA_TERMS)
            and {
                "sleep_duration_category",
                "dietary_habits",
                "depression_flag",
                "cgpa_10",
            }.issubset(student_cols)
        ):
            hints.append(
                "For student_depression sleep/diet matrix questions about depression "
                "and CGPA, use sleep_duration_category and dietary_habits as the two "
                "grouping keys, filter both grouping columns with IS NOT NULL, include "
                "COUNT(*) AS n, ROUND(100.0 * SUM(depression_flag) / COUNT(*), 2) AS "
                "depression_rate_pct, and ROUND(AVG(cgpa_10), 2) AS avg_cgpa. Apply "
                "HAVING COUNT(*) >= 50 as a minimum support threshold for stable matrix "
                "cells and ORDER BY depression_rate_pct DESC. Do not use sleep_hours "
                "or diet_quality unless those exact columns are in student_depression."
            )

        if task_type in {
            "grouping_query",
            "comparison_query",
            "trend_query",
        } or _has_any(q, _DASHBOARD_TERMS):
            hints.append(
                "For dashboard, storytelling, grouping, or comparison requests, "
                "do not collapse the answer to a single scalar. Return a compact "
                "analytical table with the requested grouping key and the relevant "
                "aggregate columns needed to support the dashboard."
            )

        if "country_prevalence_long" in schema_tables and _has_any(q, _CHANGE_TERMS):
            hints.append(
                "For global prevalence change questions with a named disorder, use "
                "country_prevalence_long, whose relevant columns are country_name, "
                "year, is_country_like, disorder, and prevalence_pct. Do not use "
                "prevalence_pct or disorder with country_prevalence_wide; the wide "
                "table has disorder-specific *_pct columns instead. When a named "
                "disorder and change/quartile cues are both present, MUST use "
                "country_prevalence_long, filter disorder to the named value, compute "
                "baseline and latest endpoints per country with conditional "
                "aggregation, and calculate value_latest - value_baseline as the "
                "change."
            )

        if "country_prevalence_long" in schema_tables:
            if _has_any(q, _MENTAL_HEALTH_GENERAL_TERMS) and not _has_any(q, _DISORDER_NAME_TERMS):
                hints.append(
                    "In global prevalence data, generic 'mental health' is a topic label, "
                    "not a value in the disorder column. Do not add a disorder filter unless "
                    "the user names a specific disorder such as depression, anxiety, bipolar, "
                    "schizophrenia, or eating disorder."
                )
            if _has_any(q, _DISORDER_GROUP_TERMS):
                hints.append(
                    "If the user asks for counts or summaries for each disorder, GROUP BY "
                    "disorder and do not filter disorder to a made-up or single value."
                )

        if _has_any(q, _QUANTILE_TERMS):
            hints.append(
                "When quartiles, percentiles, or bins are requested, compute the "
                "measure first and then use NTILE(4) or an equivalent grouped binning "
                "step over that measure before producing the final grouped summary. "
                "SQLite does not support PERCENTILE_CONT or WITHIN GROUP; do not use "
                "those functions. For change dashboards, the final summary should "
                "include the bin key, COUNT(*) AS country_count, and rounded "
                "AVG/MIN/MAX of the change."
            )

        if _has_any(q, _RISK_TERMS) and _has_any(q, _AVERAGE_COMPARISON_TERMS):
            risk_hint = (
                "For risk questions over people matching above/below-average filters, "
                "the final query must summarize by mental_health_risk with GROUP BY "
                "mental_health_risk and COUNT(*) AS n. Use subqueries for average "
                "thresholds instead of fixed constants unless the user gives an "
                "explicit threshold."
            )
            general_cols = _table_columns(schema, "mental_health_general")
            if {"stress_level", "sleep_hours", "mental_health_risk"}.issubset(general_cols):
                risk_hint += (
                    " For mental_health_general, include "
                    "ROUND(AVG(stress_level), 2) AS avg_stress and "
                    "ROUND(AVG(sleep_hours), 2) AS avg_sleep, then ORDER BY n DESC."
                )
            hints.append(risk_hint)

        return hints
