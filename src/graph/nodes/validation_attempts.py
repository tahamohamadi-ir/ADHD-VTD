from __future__ import annotations

from typing import Any, Literal

from src.graph.state import SQLAttempt, VTDState

ValidationRetryDecision = Literal["success", "fail_fast", "single_retry", "retry_increment"]


def missing_sql_validation_errors(
    existing_errors: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Preserve parser errors; otherwise emit the canonical no-SQL error."""

    errors = list(existing_errors or [])
    return errors or [{"type": "VALIDATION_ERROR", "message": "No SQL to validate"}]


def validation_errors_from_issues(issues: list[Any]) -> list[dict[str, Any]]:
    return [{"message": str(issue)} for issue in issues]


def validation_error_message(validation_errors: list[Any]) -> str:
    return ", ".join(
        str(error.get("message", error)) if isinstance(error, dict) else str(error)
        for error in validation_errors
    )


def issue_error_message(issues: list[Any]) -> str | None:
    if not issues:
        return None
    return ", ".join(str(issue) for issue in issues)


def missing_sql_error_type(validation_errors: list[dict[str, Any]]) -> str:
    if not validation_errors:
        return "VALIDATION_ERROR"
    return str(validation_errors[0].get("type") or "VALIDATION_ERROR")


def build_missing_sql_attempt(
    state: VTDState,
    *,
    validation_errors: list[dict[str, Any]],
) -> SQLAttempt:
    return SQLAttempt(
        iteration=state.retry_count,
        prompt=state.prompt,
        raw_model_response=state.raw_model_response,
        generation_latency_ms=state.generation_latency_ms,
        parsed_payload=state.parsed_payload,
        sql=None,
        parsed=bool(state.parsed_payload),
        validation_passed=False,
        validation_errors=validation_errors,
        error_type=missing_sql_error_type(validation_errors),
        error_message=validation_error_message(validation_errors),
    )


def repair_action_from_plan(repair_plan: str | None) -> str | None:
    if repair_plan and "shape_surgeon_patch_applied=true" in repair_plan:
        return "shape_surgeon"
    if repair_plan and "patch_applied=true" in repair_plan:
        return "schema_surgeon"
    return None


def build_validation_attempt(
    state: VTDState,
    *,
    sql: str,
    validation_passed: bool,
    validation_errors: list[dict[str, Any]],
    issues: list[Any],
    repair_plan: str | None,
) -> SQLAttempt:
    return SQLAttempt(
        iteration=state.retry_count,
        prompt=state.prompt,
        raw_model_response=state.raw_model_response,
        generation_latency_ms=state.generation_latency_ms,
        parsed_payload=state.parsed_payload,
        sql=sql,
        parsed=bool(state.parsed_payload),
        validation_passed=validation_passed,
        validation_errors=validation_errors,
        error_message=issue_error_message(issues) if not validation_passed else None,
        repair_action=repair_action_from_plan(repair_plan),
        repair_plan=repair_plan,
    )


def decide_validation_retry(
    *,
    validation_passed: bool,
    surgeon_fail_fast: bool,
    surgeon_single_retry: bool,
    shape_single_retry: bool,
    has_shape_errors: bool,
) -> ValidationRetryDecision:
    if validation_passed:
        return "success"
    if surgeon_fail_fast:
        return "fail_fast"
    if surgeon_single_retry or shape_single_retry or has_shape_errors:
        return "single_retry"
    return "retry_increment"
