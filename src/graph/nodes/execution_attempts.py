from __future__ import annotations

from typing import Any

from src.graph.state import SQLAttempt


def update_latest_attempt_with_execution_result(
    attempts: list[SQLAttempt],
    result: Any,
) -> list[SQLAttempt]:
    """Attach a read-only execution result to the latest recorded attempt."""

    if not attempts:
        return attempts

    latest = attempts[-1]
    return attempts[:-1] + [
        latest.model_copy(
            update={
                "execution_passed": result.ok,
                "execution_result_preview": result.rows[:5] if result.ok else None,
                "execution_result_hash": result.result_hash if result.ok else None,
                "latency_ms": result.latency_ms,
                "error_message": result.error if not result.ok else latest.error_message,
            }
        )
    ]


def execution_state_updates(
    *,
    attempts: list[SQLAttempt],
    result: Any,
) -> dict[str, Any]:
    return {
        "attempts": attempts,
        "execution_result": result.rows if result.ok else None,
        "execution_error": result.error if not result.ok else None,
        "semantic_passed": result.ok,
    }


def execution_needs_retry(result: Any) -> bool:
    return not bool(result.ok)
