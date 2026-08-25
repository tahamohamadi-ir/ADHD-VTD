from __future__ import annotations

from typing import Any

from src.graph.state import SQLAttempt, VTDState


def latest_reflexion_context(state: VTDState) -> tuple[str, str]:
    latest = state.attempts[-1]
    return latest.error_message or "Unknown failure", latest.sql or ""


def seed_transition_memory(attempts: list[SQLAttempt], memory: Any) -> None:
    for attempt in attempts:
        memory.update(attempt.sql or "", attempt.error_message or "")


def update_latest_attempt_with_reflexion(
    attempts: list[SQLAttempt],
    *,
    critic_feedback: str,
    repair_plan: str,
) -> list[SQLAttempt]:
    new_attempts = list(attempts)
    if new_attempts:
        latest = new_attempts[-1]
        new_attempts[-1] = latest.model_copy(
            update={"critic_feedback": critic_feedback, "repair_plan": repair_plan}
        )
    return new_attempts


def repair_validation_error_text(state: VTDState, fallback_error_message: str) -> str:
    if state.validation_errors:
        return "\n".join(
            [
                str(error.get("message", error)) if isinstance(error, dict) else str(error)
                for error in state.validation_errors
            ]
        )

    validation_error_text = fallback_error_message or "Unknown failure"
    if (
        validation_error_text == "Unknown failure"
        and state.candidate_consistency_report
        and not state.candidate_consistency_report.get("passed")
    ):
        issues = state.candidate_consistency_report.get("issues", [])
        if issues:
            return "\n".join(
                [
                    str(issue.get("message", issue)) if isinstance(issue, dict) else str(issue)
                    for issue in issues
                ]
            )
    return validation_error_text


def repair_critic_feedback(critic_feedback: str, repair_plan: str) -> str:
    return f"{critic_feedback}\n\nRepair Plan: {repair_plan}"


def repair_attempt_history(attempts: list[SQLAttempt], *, limit: int = 3) -> list[dict[str, str]]:
    failed = [a for a in attempts if (a.error_message or "").strip() and (a.sql or "").strip()]
    recent = failed[-limit:] if limit > 0 else []
    return [
        {"sql": attempt.sql or "", "error": attempt.error_message or ""} for attempt in recent
    ]


def reflexion_updates(*, prompt: str, attempts: list[SQLAttempt]) -> dict[str, Any]:
    return {
        "prompt": prompt,
        "attempts": attempts,
        "repair_attempt_history": repair_attempt_history(attempts),
    }
