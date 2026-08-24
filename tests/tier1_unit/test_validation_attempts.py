from __future__ import annotations

from src.graph.nodes.validation_attempts import (
    build_missing_sql_attempt,
    build_validation_attempt,
    decide_validation_retry,
    missing_sql_validation_errors,
    repair_action_from_plan,
    validation_error_message,
    validation_errors_from_issues,
)
from src.graph.state import VTDState
from src.sql_validation.validation_result import ValidationIssue


def test_missing_sql_validation_errors_preserves_parser_errors() -> None:
    errors = [{"type": "OUTPUT_PARSE_ERROR", "message": "Invalid JSON format"}]

    assert missing_sql_validation_errors(errors) == errors


def test_missing_sql_validation_errors_adds_canonical_validation_error() -> None:
    assert missing_sql_validation_errors([]) == [
        {"type": "VALIDATION_ERROR", "message": "No SQL to validate"}
    ]


def test_build_missing_sql_attempt_records_parse_failure_without_sql() -> None:
    state = VTDState(
        trace_id="trace",
        raw_question="question",
        prompt="PROMPT",
        raw_model_response="DROP TABLE student_depression",
        parsed_payload=None,
        generation_latency_ms=7,
        retry_count=2,
    )
    errors = [{"type": "OUTPUT_PARSE_ERROR", "message": "Invalid JSON format"}]

    attempt = build_missing_sql_attempt(state, validation_errors=errors)

    assert attempt.iteration == 2
    assert attempt.sql is None
    assert attempt.validation_passed is False
    assert attempt.error_type == "OUTPUT_PARSE_ERROR"
    assert attempt.error_message == "Invalid JSON format"
    assert attempt.raw_model_response == "DROP TABLE student_depression"
    assert attempt.generation_latency_ms == 7


def test_validation_errors_from_issues_matches_graph_node_contract() -> None:
    issues = [ValidationIssue(code="FORBIDDEN_KEYWORD", message="DROP is not allowed")]
    expected = str(issues[0])

    assert validation_errors_from_issues(issues) == [{"message": expected}]
    assert validation_error_message(validation_errors_from_issues(issues)) == expected


def test_repair_action_from_plan_prioritizes_shape_patch() -> None:
    assert repair_action_from_plan("shape_surgeon_patch_applied=true; patch_applied=true") == (
        "shape_surgeon"
    )
    assert repair_action_from_plan("surgeon_patch_applied=true") == "schema_surgeon"
    assert repair_action_from_plan("surgeon_patch_applied=false") is None
    assert repair_action_from_plan(None) is None


def test_build_validation_attempt_records_repair_plan_and_error_message() -> None:
    state = VTDState(
        trace_id="trace",
        raw_question="question",
        prompt="PROMPT",
        raw_model_response='{"sql":"SELECT missing_col FROM student_depression"}',
        parsed_payload={"sql": "SELECT missing_col FROM student_depression"},
        retry_count=1,
    )
    issues = [ValidationIssue(code="UNKNOWN_COLUMN", message="Unknown column: missing_col")]
    errors = validation_errors_from_issues(issues)
    expected_message = str(issues[0])

    attempt = build_validation_attempt(
        state,
        sql="SELECT missing_col FROM student_depression",
        validation_passed=False,
        validation_errors=errors,
        issues=issues,
        repair_plan="surgeon_invoked=true; surgeon_patch_applied=false",
    )

    assert attempt.iteration == 1
    assert attempt.parsed is True
    assert attempt.validation_passed is False
    assert attempt.validation_errors == errors
    assert attempt.error_message == expected_message
    assert attempt.repair_action is None
    assert attempt.repair_plan == "surgeon_invoked=true; surgeon_patch_applied=false"


def test_decide_validation_retry_keeps_existing_priority_order() -> None:
    assert (
        decide_validation_retry(
            validation_passed=True,
            surgeon_fail_fast=True,
            surgeon_single_retry=True,
            shape_single_retry=True,
            has_shape_errors=True,
        )
        == "success"
    )
    assert (
        decide_validation_retry(
            validation_passed=False,
            surgeon_fail_fast=True,
            surgeon_single_retry=True,
            shape_single_retry=True,
            has_shape_errors=True,
        )
        == "fail_fast"
    )
    assert (
        decide_validation_retry(
            validation_passed=False,
            surgeon_fail_fast=False,
            surgeon_single_retry=True,
            shape_single_retry=False,
            has_shape_errors=False,
        )
        == "single_retry"
    )
    assert (
        decide_validation_retry(
            validation_passed=False,
            surgeon_fail_fast=False,
            surgeon_single_retry=False,
            shape_single_retry=False,
            has_shape_errors=True,
        )
        == "single_retry"
    )
    assert (
        decide_validation_retry(
            validation_passed=False,
            surgeon_fail_fast=False,
            surgeon_single_retry=False,
            shape_single_retry=False,
            has_shape_errors=False,
        )
        == "retry_increment"
    )
