from __future__ import annotations

import re
from typing import Any

from src.core.enums import IntentLabel
from src.core.query_ir import QueryIR
from src.core.types import SchemaLinkResult
from src.schema.concept_registry import ConceptRegistry


_TABLE_SHAPE_INTENTS = {
    IntentLabel.GROUPING_QUERY,
    IntentLabel.RANKING_QUERY,
    IntentLabel.TREND_QUERY,
    IntentLabel.RATE_QUERY,
    IntentLabel.COMPARISON_QUERY,
    IntentLabel.CHART_QUERY,
}

_GROUPING_TERMS = (
    "distribution",
    "by ",
    "based on",
    "per ",
    "group",
    "\u062a\u0648\u0632\u06cc\u0639",
    "\u0628\u0647 \u062a\u0641\u06a9\u06cc\u06a9",
    "\u0628\u0631 \u0627\u0633\u0627\u0633",
    "\u062f\u0631 \u0647\u0631",
    "\u0647\u0631 ",
    "\u0645\u0642\u0627\u06cc\u0633\u0647",
)
_TWO_SIDED_TERMS = (
    "\u0628\u0627 \u0648 \u0628\u062f\u0648\u0646",
    "\u0627\u0641\u0633\u0631\u062f\u0647 \u0648 \u063a\u06cc\u0631\u0627\u0641\u0633\u0631\u062f\u0647",
    "\u062f\u0627\u0631\u0627\u06cc \u0648 \u0628\u062f\u0648\u0646",
    "with and without",
    "depressed and non-depressed",
    "depressed and non depressed",
)
_RATE_TERMS = ("rate", "percent", "percentage", "\u0646\u0631\u062e", "\u062f\u0631\u0635\u062f")
_AVG_TERMS = ("avg", "average", "mean", "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646")
_COUNT_TERMS = ("count", "\u062a\u0639\u062f\u0627\u062f", "\u0686\u0646\u062f")

_METRIC_SUFFIXES = (
    "_score",
    "_pct",
    "_rate",
    "_mid",
    "_hours",
)
_METRIC_COLUMNS = {
    "age",
    "cgpa",
    "cgpa_10",
    "cgpa_mid",
    "academic_pressure",
    "work_pressure",
    "study_satisfaction",
    "job_satisfaction",
    "work_study_hours",
    "financial_stress",
    "sleep_mid_hours",
    "sleep_hours",
    "study_hours_per_day",
    "social_media_hours",
    "netflix_hours",
    "attendance_percentage",
    "exam_score",
    "mental_health_rating",
    "stress_level",
    "productivity_score",
    "depression_score",
    "anxiety_score",
    "prevalence_pct",
}
_BINARY_METRICS = {
    "depression_flag",
    "depression_diagnosis",
    "anxiety_diagnosis",
    "treatment",
    "seeks_treatment",
    "treatment_seeking",
    "obs_consequence",
}
_ID_COLUMNS = {
    "id",
    "student_id",
    "source_row_id",
    "student_depression_id",
    "habit_row_id",
    "habit_id",
    "general_row_id",
    "survey_id",
    "university_row_id",
}


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _column_name(linked_column: Any) -> str:
    if isinstance(linked_column, str):
        return linked_column.split(".", 1)[-1]
    return str(getattr(linked_column, "column", "") or "").split(".", 1)[-1]


def _table_name(linked_column: Any) -> str:
    if isinstance(linked_column, str):
        return linked_column.split(".", 1)[0] if "." in linked_column else ""
    return str(getattr(linked_column, "table", "") or "")


def _column_score(linked_column: Any) -> float:
    try:
        return float(getattr(linked_column, "score", 1.0))
    except (TypeError, ValueError):
        return 1.0


def _is_metric_column(column: str) -> bool:
    column = column.lower()
    return column in _METRIC_COLUMNS or column.endswith(_METRIC_SUFFIXES)


def _is_id_column(column: str) -> bool:
    column = column.lower()
    return column in _ID_COLUMNS or column.endswith("_id") or column.endswith("_row_id")


class QueryPlanner:
    """Orchestrates NLU output and schema linking to build a QueryIR."""

    def __init__(self) -> None:
        self.registry = ConceptRegistry()

    def build_qir(
        self,
        normalized_question: str,
        extracted_terms: list[str],
        intent: IntentLabel,
        schema_link: SchemaLinkResult | None = None,
    ) -> QueryIR:
        """Build the structured QueryIR representation."""
        
        # 1. Base initialization from Intent
        qir = QueryIR(
            task_type=str(intent),
            should_generate_sql=intent not in (
                IntentLabel.UNSAFE_QUERY,
                IntentLabel.AMBIGUOUS_QUERY,
                IntentLabel.DEFINITION_QUERY,
                IntentLabel.NON_SQL_REQUEST,
            )
        )

        normalized = (normalized_question or "").lower()

        if intent in (IntentLabel.AGGREGATION_QUERY, IntentLabel.COUNT_QUERY):
            qir.expected_result_shape = "scalar"
        elif intent in _TABLE_SHAPE_INTENTS:
            qir.expected_result_shape = "table"
        elif intent == IntentLabel.RAW_RETRIEVAL_QUERY:
            qir.expected_result_shape = "table"
        if intent == IntentLabel.CHART_QUERY:
            qir.chart_intent = True

        # 2. Add elements from Schema Linking directly (if provided)
        if schema_link:
            for linked_col in getattr(schema_link, "columns", []) or []:
                column = _column_name(linked_col).lower()
                if not column or _is_id_column(column):
                    continue
                score = _column_score(linked_col)
                if score < 0.55:
                    continue
                if _is_metric_column(column):
                    self._append_unique(qir.metrics, column)
                else:
                    self._append_unique(qir.dimensions, column)

        # 3. Enrich using Semantic Concepts
        qir = self.registry.enrich_qir(qir, extracted_terms)
        self._remove_dataset_name_filters(qir, normalized)
        self._remove_filter_only_dimensions(qir, normalized, intent)
        self._apply_text_shape_hints(qir, normalized, schema_link)
        self._finalize_shape(qir, normalized, intent)

        return qir

    @staticmethod
    def _append_unique(items: list[str], value: str) -> None:
        if value and value not in items:
            items.append(value)

    def _apply_text_shape_hints(
        self,
        qir: QueryIR,
        normalized: str,
        schema_link: SchemaLinkResult | Any | None,
    ) -> None:
        tables = {
            str(table.table if hasattr(table, "table") else table)
            for table in (getattr(schema_link, "tables", []) or [])
        }
        columns = {
            _column_name(column).lower(): _table_name(column)
            for column in (getattr(schema_link, "columns", []) or [])
            if _column_name(column)
        }

        if _contains_any(normalized, _TWO_SIDED_TERMS):
            if "student_depression" in tables or "depression_flag" in columns:
                self._append_unique(qir.dimensions, "depression_flag")
            if "part_time_job" in columns:
                self._append_unique(qir.dimensions, "part_time_job")

        if _contains_any(normalized, _RATE_TERMS):
            if "depression_flag" in columns or "student_depression" in tables:
                self._append_unique(qir.metrics, "depression_flag")
            elif "treatment" in columns or "workplace_mental_health_survey" in tables:
                self._append_unique(qir.metrics, "treatment")
            elif "seeks_treatment" in columns or "mental_health_general" in tables:
                self._append_unique(qir.metrics, "seeks_treatment")
            qir.expected_result_shape = "table" if qir.dimensions else qir.expected_result_shape or "scalar"
            qir.dimensions = [dim for dim in qir.dimensions if dim not in qir.metrics]

        if _contains_any(normalized, _AVG_TERMS):
            for metric in ("cgpa_10", "exam_score", "prevalence_pct", "depression_score", "anxiety_score"):
                if metric in columns:
                    self._append_unique(qir.metrics, metric)

        # Common Persian group keys that are not always extracted as terms.
        text_dimension_aliases = {
            "\u062c\u0646\u0633\u06cc\u062a": "gender",
            "gender": "gender",
            "\u0634\u0647\u0631": "city",
            "city": "city",
            "\u06a9\u0634\u0648\u0631": "country_name",
            "country": "country_name",
            "\u0633\u0627\u0644": "year",
            "year": "year",
            "\u062e\u0648\u0627\u0628": "sleep_duration_category",
            "sleep": "sleep_duration_category",
            "\u0631\u0698\u06cc\u0645": "dietary_habits",
            "diet": "dietary_habits",
            "\u0645\u0632\u0627\u06cc\u0627": "benefits",
            "benefits": "benefits",
            "care options": "care_options",
            "\u062f\u0648\u0631\u06a9\u0627\u0631": "remote_work",
            "remote": "remote_work",
            "\u0627\u0646\u062f\u0627\u0632\u0647 \u0634\u0631\u06a9\u062a": "no_employees",
            "company size": "no_employees",
            "\u0631\u06cc\u0633\u06a9": "mental_health_risk",
            "risk": "mental_health_risk",
        }
        asks_grouping = _contains_any(normalized, _GROUPING_TERMS) or _contains_any(normalized, _TWO_SIDED_TERMS)
        if asks_grouping:
            for term, column in text_dimension_aliases.items():
                if term in normalized and (not columns or column in columns or self._column_available_in_tables(column, tables)):
                    self._append_unique(qir.dimensions, column)

    def _finalize_shape(self, qir: QueryIR, normalized: str, intent: IntentLabel) -> None:
        asks_grouping = _contains_any(normalized, _GROUPING_TERMS) or _contains_any(normalized, _TWO_SIDED_TERMS)
        if intent in _TABLE_SHAPE_INTENTS or asks_grouping or len(qir.dimensions) > 0:
            qir.expected_result_shape = "table"
        if intent == IntentLabel.COUNT_QUERY and asks_grouping:
            qir.task_type = IntentLabel.GROUPING_QUERY.value
            qir.expected_result_shape = "table"
        if intent == IntentLabel.RATE_QUERY and qir.metrics and qir.dimensions:
            qir.expected_result_shape = "table"

    def _remove_dataset_name_filters(self, qir: QueryIR, normalized: str) -> None:
        dataset_context = (
            "\u062f\u06cc\u062a\u0627\u0633\u062a \u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u0627\u0646 \u0627\u0641\u0633\u0631\u062f\u06af\u06cc" in normalized
            or "student_depression" in normalized
        )
        two_sided = _contains_any(normalized, _TWO_SIDED_TERMS)
        if not (dataset_context or two_sided):
            return
        qir.filters = [
            filt
            for filt in qir.filters
            if not (filt.get("column") == "depression_flag" and filt.get("value") == 1)
        ]

    def _remove_filter_only_dimensions(self, qir: QueryIR, normalized: str, intent: IntentLabel) -> None:
        asks_grouping = _contains_any(normalized, _GROUPING_TERMS) or _contains_any(normalized, _TWO_SIDED_TERMS)
        if asks_grouping or intent in _TABLE_SHAPE_INTENTS:
            return
        filter_columns = {str(filt.get("column")) for filt in qir.filters}
        qir.dimensions = [dim for dim in qir.dimensions if dim not in filter_columns]

    @staticmethod
    def _column_available_in_tables(column: str, tables: set[str]) -> bool:
        # This keeps QueryPlanner schema-format agnostic. Schema validation later
        # remains the source of truth; here we only avoid dropping obvious hints.
        if not tables:
            return True
        table_column_hints = {
            "sleep_duration_category": {"student_depression"},
            "dietary_habits": {"student_depression"},
            "remote_work": {"workplace_mental_health_survey"},
            "no_employees": {"workplace_mental_health_survey"},
            "benefits": {"workplace_mental_health_survey"},
            "care_options": {"workplace_mental_health_survey"},
            "mental_health_risk": {"mental_health_general"},
            "country_name": {"country_prevalence_long", "country_prevalence_wide"},
            "year": {"country_prevalence_long", "country_prevalence_wide"},
        }
        allowed = table_column_hints.get(column)
        return allowed is None or bool(allowed & tables)
