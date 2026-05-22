from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from src.evaluation.sql_consistency_critic import analyze_question_sql_consistency


ReliabilityGateAction = Literal[
    "answer",
    "retry",
    "ask_clarification",
    "needs_review",
    "refuse_unsafe",
]


@dataclass(slots=True)
class ReliabilityGatePolicy:
    min_intent_confidence: float = 0.4
    review_empty_results: bool = True
    use_judge_signals: bool = True


@dataclass(slots=True)
class ReliabilityGateDecision:
    action: ReliabilityGateAction
    reason: str
    confidence: float
    warnings: list[str] = field(default_factory=list)
    signals: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "confidence": self.confidence,
            "warnings": list(self.warnings),
            "signals": dict(self.signals),
        }


def evaluate_reliability_gate(
    record: dict[str, Any],
    *,
    policy: ReliabilityGatePolicy | None = None,
) -> ReliabilityGateDecision:
    """Decide whether a runtime result is safe enough to answer.

    The gate intentionally avoids gold labels, case IDs, and exact benchmark outcomes.
    It uses only runtime-style signals plus optional judge labels when those labels are
    already present in the record.
    """

    p = policy or ReliabilityGatePolicy()
    signals = _extract_signals(record)

    if signals["unsafe_request"] or signals["unsafe_sql"]:
        return _decision("refuse_unsafe", "unsafe_request", 0.95, signals=signals)

    if signals["needs_clarification"]:
        return _decision("ask_clarification", "clarification_requested", 0.9, signals=signals)

    if signals["intent_confidence"] is not None and signals["intent_confidence"] < p.min_intent_confidence:
        return _decision("ask_clarification", "low_intent_confidence", 0.85, signals=signals)

    if signals["should_generate_sql"] is False:
        return _decision("ask_clarification", "non_sql_or_ambiguous_request", 0.8, signals=signals)

    if not signals["generated_sql"]:
        return _retry_or_review(signals, "missing_generated_sql")

    if signals["validation_failed"]:
        return _retry_or_review(signals, "validation_failed")

    if signals["consistency_failed"]:
        return _retry_or_review(signals, "consistency_failed")

    if signals["candidate_consistency_failed"]:
        return _retry_or_review(signals, "candidate_consistency_failed")

    if signals["candidate_evidence_missing_after_trigger"]:
        return _decision(
            "needs_review",
            "candidate_evidence_missing_after_trigger",
            0.75,
            warnings=["multi_candidate_evidence_unavailable"],
            signals=signals,
        )

    if signals["execution_failed"]:
        return _retry_or_review(signals, "execution_failed")

    if p.use_judge_signals:
        judge_decision = _decision_from_judge_signals(signals)
        if judge_decision is not None:
            return judge_decision

    warnings: list[str] = []
    if signals["strict_policy_label"] == "incorrect":
        warnings.append("strict_reference_mismatch")

    if p.review_empty_results and signals["execution_result_empty"]:
        return _decision(
            "needs_review",
            "empty_execution_result",
            0.75,
            warnings=warnings,
            signals=signals,
        )

    if signals["execution_succeeded"]:
        return _decision("answer", "validated_executed_sql", 0.9, warnings=warnings, signals=signals)

    return _decision("needs_review", "insufficient_runtime_evidence", 0.6, signals=signals)


def _decision(
    action: ReliabilityGateAction,
    reason: str,
    confidence: float,
    *,
    warnings: list[str] | None = None,
    signals: dict[str, Any],
) -> ReliabilityGateDecision:
    return ReliabilityGateDecision(
        action=action,
        reason=reason,
        confidence=round(confidence, 4),
        warnings=warnings or [],
        signals=signals,
    )


def _retry_or_review(signals: dict[str, Any], reason: str) -> ReliabilityGateDecision:
    if signals["retry_count"] < signals["max_retries"]:
        return _decision("retry", f"{reason}_retryable", 0.8, signals=signals)
    return _decision("needs_review", f"{reason}_exhausted", 0.85, signals=signals)


def _decision_from_judge_signals(signals: dict[str, Any]) -> ReliabilityGateDecision | None:
    semantic = signals["semantic_policy_label"]
    strict = signals["strict_policy_label"]
    combined = signals["combined_label"]
    if semantic == "incorrect":
        return _decision(
            "needs_review",
            "semantic_judge_incorrect",
            0.9,
            signals=signals,
        )
    if semantic in {"adjudication_required", "partial_business_match"}:
        return _decision(
            "needs_review",
            "semantic_judge_unresolved",
            0.8,
            signals=signals,
        )
    if combined == "semantic_correct_strict_incorrect" or (
        semantic == "correct" and strict == "incorrect"
    ):
        return _decision(
            "answer",
            "semantic_correct_with_strict_reference_mismatch",
            0.8,
            warnings=["strict_reference_mismatch"],
            signals=signals,
        )
    return None


def _extract_signals(record: dict[str, Any]) -> dict[str, Any]:
    validation_issues = _listish(record.get("validation_issues") or record.get("validation_errors"))
    consistency_issues = _extract_consistency_issues(record)
    candidate_consistency_issues = _extract_candidate_consistency_issues(record)
    multi_candidate_policy = record.get("multi_candidate_policy")
    multi_candidate_policy_dict = multi_candidate_policy if isinstance(multi_candidate_policy, dict) else {}
    candidate_sqls = _listish(record.get("candidate_sqls"))
    execution_result = record.get("execution_result")
    attempts = _listish(record.get("attempts"))
    retry_count = _int_or_default(record.get("retry_count"), _attempt_retry_count(attempts))
    max_retries = _int_or_default(record.get("max_retries"), 3)
    generated_sql = record.get("generated_sql") or record.get("sql")
    valid_sql = record.get("valid_sql")
    execution_error = record.get("execution_error")
    safety_label = str(record.get("safety_label") or "")
    intent = str(record.get("intent") or "")
    actual_action = str(record.get("actual_action") or "")

    execution_result_present = execution_result is not None
    execution_result_empty = isinstance(execution_result, list) and len(execution_result) == 0
    execution_succeeded = bool(
        record.get("execution_passed")
        or record.get("execution_ok")
        or (execution_result_present and not execution_error)
    )
    validation_failed = bool(validation_issues) or valid_sql is False
    execution_failed = bool(execution_error)
    multi_candidate_expected = bool(multi_candidate_policy_dict.get("enabled")) and _int_or_default(
        multi_candidate_policy_dict.get("candidate_count"),
        1,
    ) > 1
    multi_candidate_generation_enabled = bool(
        record.get("multi_candidate_generation_enabled")
        or record.get("multi_candidate_generation")
        or (
            isinstance(record.get("ablation_config"), dict)
            and record["ablation_config"].get("multi_candidate_generation")
        )
    )
    candidate_evidence_missing = multi_candidate_expected and not candidate_sqls and not (
        record.get("candidate_consistency") or record.get("candidate_consistency_report")
    ) and multi_candidate_generation_enabled

    return {
        "actual_action": actual_action,
        "combined_label": record.get("combined_label"),
        "candidate_evidence_missing_after_trigger": candidate_evidence_missing,
        "candidate_evidence_present": bool(candidate_sqls or record.get("candidate_consistency") or record.get("candidate_consistency_report")),
        "candidate_consistency_failed": bool(candidate_consistency_issues),
        "candidate_consistency_issue_count": len(candidate_consistency_issues),
        "candidate_consistency_issues": candidate_consistency_issues,
        "candidate_sql_count": len(candidate_sqls),
        "consistency_failed": bool(consistency_issues),
        "consistency_issue_count": len(consistency_issues),
        "consistency_issues": consistency_issues,
        "execution_error": execution_error,
        "execution_failed": execution_failed,
        "execution_result_empty": execution_result_empty,
        "execution_result_present": execution_result_present,
        "execution_succeeded": execution_succeeded,
        "generated_sql": bool(generated_sql),
        "intent": intent,
        "intent_confidence": _float_or_none(record.get("intent_confidence")),
        "max_retries": max_retries,
        "multi_candidate_policy_enabled": bool(multi_candidate_policy_dict.get("enabled")),
        "multi_candidate_generation_enabled": multi_candidate_generation_enabled,
        "multi_candidate_policy_triggers": list(multi_candidate_policy_dict.get("triggers") or []),
        "needs_clarification": bool(record.get("needs_clarification")),
        "retry_count": retry_count,
        "safety_label": safety_label,
        "semantic_policy_label": record.get("semantic_policy_label"),
        "should_generate_sql": record.get("should_generate_sql"),
        "strict_policy_label": record.get("strict_policy_label"),
        "unsafe_request": intent == "unsafe_query" or safety_label.startswith(("unsafe", "prompt_injection", "privacy")),
        "unsafe_sql": bool(record.get("unsafe_sql_generated") or record.get("unsafe_sql") or record.get("safety_violation")),
        "valid_sql": valid_sql,
        "validation_failed": validation_failed,
        "validation_issue_count": len(validation_issues),
    }


def _extract_consistency_issues(record: dict[str, Any]) -> list[dict[str, Any]]:
    supplied = _listish(record.get("sql_consistency_issues") or record.get("consistency_issues"))
    supplied_dicts = [item for item in supplied if isinstance(item, dict)]
    hard_supplied = [
        item for item in supplied_dicts if str(item.get("severity") or "error") == "error"
    ]
    if hard_supplied:
        return hard_supplied

    question = record.get("question") or record.get("normalized_question")
    sql = record.get("generated_sql") or record.get("sql")
    if not question or not sql:
        return []
    report = analyze_question_sql_consistency(str(question), str(sql))
    return [issue.as_dict() for issue in report.issues if issue.severity == "error"]


def _extract_candidate_consistency_issues(record: dict[str, Any]) -> list[dict[str, Any]]:
    report = record.get("candidate_consistency") or record.get("candidate_consistency_report")
    if not isinstance(report, dict):
        return []
    issues = [
        issue
        for issue in _listish(report.get("issues"))
        if isinstance(issue, dict) and str(issue.get("severity") or "error") == "error"
    ]
    if report.get("passed") is False and not issues:
        return [
            {
                "code": "CANDIDATE_CONSISTENCY_FAILED",
                "message": "Candidate consistency report failed without a structured issue.",
                "severity": "error",
            }
        ]
    return issues


def _listish(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _attempt_retry_count(attempts: list[Any]) -> int:
    return max(len(attempts) - 1, 0)


def _int_or_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
