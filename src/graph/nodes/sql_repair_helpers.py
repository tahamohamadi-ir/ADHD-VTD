import re
from collections.abc import Callable, Sequence
from typing import Any

from src.graph.state import VTDState
from src.nlu.persian_normalizer import PersianNormalizer
from src.schema.schema_registry import SchemaRegistry
from src.sql_validation.shape_rewriter import rewrite_analytical_shape
from src.sql_validation.shape_validator import SQLShapeValidator
from src.sql_validation.validation_pipeline import ValidationPipeline
from src.sql_validation.validation_result import ValidationResult


UNKNOWN_COLUMN_ALIASES: tuple[dict[str, Any], ...] = (
    {
        "table": "student_depression",
        "unknown": "diet_quality",
        "replacement": "dietary_habits",
        "terms": (
            "diet",
            "dietary",
            "\u0631\u0698\u06cc\u0645",
            "\u063a\u0630\u0627\u06cc\u06cc",
        ),
    },
    {
        "table": "student_habits_performance",
        "unknown": "dietary_habits",
        "replacement": "diet_quality",
        "terms": (
            "diet",
            "dietary",
            "\u0631\u0698\u06cc\u0645",
            "\u063a\u0630\u0627\u06cc\u06cc",
        ),
    },
    {
        "table": "university_student_mental_health",
        "unknown": "depression_flag",
        "replacement": "depression_diagnosis",
        "terms": ("depression", "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc"),
    },
    {
        "table": "student_depression",
        "unknown": "depression_diagnosis",
        "replacement": "depression_flag",
        "terms": ("depression", "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc"),
    },
    {
        "table": "mental_health_general",
        "unknown": "depression_flag",
        "replacement": "depression_score",
        "terms": ("depression", "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc"),
    },
)


def unknown_column_names(issues: list[Any]) -> list[str]:
    names: list[str] = []
    for issue in issues:
        if getattr(issue, "code", "") != "UNKNOWN_COLUMN":
            continue
        message = str(getattr(issue, "message", ""))
        match = re.search(
            r"Unknown (?:unqualified )?column: ([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)",
            message,
        )
        if match:
            names.append(match.group(1).split(".")[-1])
    return names


def sql_table_names(sql: str) -> set[str]:
    return {
        match.group(1)
        for match in re.finditer(
            r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)",
            sql or "",
            flags=re.IGNORECASE,
        )
    }


def patch_column_name(sql: str, unknown: str, replacement: str) -> str:
    return re.sub(rf"(?<![A-Za-z0-9_]){re.escape(unknown)}(?![A-Za-z0-9_])", replacement, sql)


def has_shape_errors(issues: list[Any]) -> bool:
    return any(str(getattr(issue, "code", "")).startswith("ANALYTICAL_SHAPE_") for issue in issues)


def try_unknown_column_surgeon(
    sql: str,
    *,
    question: str,
    state: VTDState,
    registry: SchemaRegistry,
    validator_factory: Callable[..., ValidationPipeline] = ValidationPipeline,
    aliases: Sequence[dict[str, Any]] = UNKNOWN_COLUMN_ALIASES,
) -> tuple[str | None, ValidationResult | None, str]:
    validator = validator_factory(registry=registry)
    initial = validator.validate(sql)
    unknown_columns = unknown_column_names(initial.issues)
    if not unknown_columns:
        return None, None, "surgeon_invoked=false"

    tables = sql_table_names(sql)
    normalized_question = PersianNormalizer().normalize_text(question or "").lower()
    for spec in aliases:
        table = str(spec["table"])
        unknown = str(spec["unknown"])
        replacement = str(spec["replacement"])
        terms = tuple(str(term) for term in spec["terms"])
        if unknown not in unknown_columns:
            continue
        if table not in tables:
            continue
        if not any(term in normalized_question for term in terms):
            continue

        patched_sql = patch_column_name(sql, unknown, replacement)
        if patched_sql == sql:
            continue
        patched_result = validator.validate(patched_sql)
        if patched_result.ok:
            shape_result = SQLShapeValidator().validate(
                patched_result.normalized_sql or patched_sql,
                question=state.raw_question,
                qir=state.qir,
                schema=state.schema_context,
            )
            if not shape_result.ok:
                patched_result = ValidationResult(
                    ok=False,
                    issues=[*patched_result.issues, *shape_result.issues],
                    normalized_sql=patched_result.normalized_sql,
                )
        if patched_result.ok:
            return (
                patched_result.normalized_sql or patched_sql,
                patched_result,
                "surgeon_invoked=true; surgeon_patch_applied=true; "
                f"surgeon_patch_validated=true; {unknown}->{replacement}",
            )
        return (
            patched_sql,
            patched_result,
            "surgeon_invoked=true; surgeon_patch_applied=true; "
            f"surgeon_patch_validated=false; surgeon_fail_fast=true; {unknown}->{replacement}",
        )

    return (
        None,
        None,
        "surgeon_invoked=true; surgeon_patch_applied=false; surgeon_deferred_to_single_retry=true",
    )


def try_shape_surgeon(
    sql: str,
    *,
    state: VTDState,
    registry: SchemaRegistry,
    issues: list[Any],
    validator_factory: Callable[..., ValidationPipeline] = ValidationPipeline,
    shape_validator_factory: Callable[..., SQLShapeValidator] = SQLShapeValidator,
    rewrite_fn: Callable[..., Any] = rewrite_analytical_shape,
) -> tuple[str | None, ValidationResult | None, str]:
    rewrite = rewrite_fn(
        sql,
        question=state.raw_question,
        qir=state.qir,
        schema=state.schema_context,
        issues=issues,
    )
    if not rewrite.rewritten or not rewrite.sql:
        return None, None, rewrite.action

    validator = validator_factory(registry=registry)
    patched_result = validator.validate(rewrite.sql)
    patched_sql = patched_result.normalized_sql or rewrite.sql
    if patched_result.ok:
        shape_result = shape_validator_factory().validate(
            patched_sql,
            question=state.raw_question,
            qir=state.qir,
            schema=state.schema_context,
        )
        if not shape_result.ok:
            patched_result = ValidationResult(
                ok=False,
                issues=[*patched_result.issues, *shape_result.issues],
                normalized_sql=patched_sql,
            )
    action = f"{rewrite.action}; shape_surgeon_patch_validated={str(patched_result.ok).lower()}"
    return patched_sql, patched_result, action
