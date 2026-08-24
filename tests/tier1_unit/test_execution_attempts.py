from __future__ import annotations

from src.db.read_only_executor import QueryExecutionResult
from src.graph.nodes.execution_attempts import (
    execution_needs_retry,
    execution_state_updates,
    update_latest_attempt_with_execution_result,
)
from src.graph.state import SQLAttempt


def test_update_latest_attempt_with_execution_result_leaves_empty_attempts_empty() -> None:
    result = QueryExecutionResult(ok=True, sql="SELECT 1", rows=[{"n": 1}])

    assert update_latest_attempt_with_execution_result([], result) == []


def test_update_latest_attempt_with_execution_result_records_success_preview_and_hash() -> None:
    attempts = [
        SQLAttempt(iteration=0, sql="SELECT 1", error_message="validation warning"),
        SQLAttempt(iteration=1, sql="SELECT 2", error_message=None),
    ]
    rows = [{"n": index} for index in range(7)]
    result = QueryExecutionResult(
        ok=True,
        sql="SELECT 2",
        rows=rows,
        result_hash="hash-2",
        latency_ms=42,
    )

    updated = update_latest_attempt_with_execution_result(attempts, result)

    assert updated[0] is attempts[0]
    assert updated[-1].execution_passed is True
    assert updated[-1].execution_result_preview == rows[:5]
    assert updated[-1].execution_result_hash == "hash-2"
    assert updated[-1].latency_ms == 42
    assert updated[-1].error_message is None


def test_update_latest_attempt_with_execution_result_records_failure_error() -> None:
    attempts = [SQLAttempt(iteration=0, sql="SELECT missing_col", error_message="old error")]
    result = QueryExecutionResult(
        ok=False,
        sql="SELECT missing_col",
        latency_ms=9,
        error="no such column: missing_col",
    )

    updated = update_latest_attempt_with_execution_result(attempts, result)

    assert updated[-1].execution_passed is False
    assert updated[-1].execution_result_preview is None
    assert updated[-1].execution_result_hash is None
    assert updated[-1].latency_ms == 9
    assert updated[-1].error_message == "no such column: missing_col"


def test_execution_state_updates_separates_success_and_failure_fields() -> None:
    attempts = [SQLAttempt(iteration=0, sql="SELECT 1")]
    success = QueryExecutionResult(ok=True, sql="SELECT 1", rows=[{"n": 1}], result_hash="h")
    failure = QueryExecutionResult(ok=False, sql="SELECT missing", error="bad sql")

    assert execution_state_updates(attempts=attempts, result=success) == {
        "attempts": attempts,
        "execution_result": [{"n": 1}],
        "execution_error": None,
        "semantic_passed": True,
    }
    assert execution_state_updates(attempts=attempts, result=failure) == {
        "attempts": attempts,
        "execution_result": None,
        "execution_error": "bad sql",
        "semantic_passed": False,
    }


def test_execution_needs_retry_follows_result_ok_flag() -> None:
    assert execution_needs_retry(QueryExecutionResult(ok=False, sql="SELECT missing")) is True
    assert execution_needs_retry(QueryExecutionResult(ok=True, sql="SELECT 1")) is False
