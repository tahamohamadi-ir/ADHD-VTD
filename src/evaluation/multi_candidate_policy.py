from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

MultiCandidateMode = Literal["disabled", "adaptive", "always"]


@dataclass(slots=True)
class MultiCandidatePolicy:
    mode: MultiCandidateMode = "adaptive"
    default_candidates: int = 1
    adaptive_candidates: int = 2
    max_candidates: int = 3
    low_confidence_threshold: float = 0.65
    allowed_triggers: tuple[str, ...] | None = None
    blocked_triggers: tuple[str, ...] = ()


@dataclass(slots=True)
class MultiCandidateDecision:
    enabled: bool
    candidate_count: int
    reason: str
    triggers: list[str] = field(default_factory=list)
    suppressed_triggers: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "enabled": self.enabled,
            "candidate_count": self.candidate_count,
            "reason": self.reason,
            "triggers": list(self.triggers),
        }
        if self.suppressed_triggers:
            payload["suppressed_triggers"] = list(self.suppressed_triggers)
        return payload


_COMPLEX_INTENTS = {
    "aggregation_query",
    "grouping_query",
    "rate_query",
    "dashboard_query",
    "comparison_query",
}

_COMPLEX_CATEGORIES = {
    "advanced_analysis",
    "advanced_sql",
    "complex_dashboard",
    "global_change_dashboard",
}


def decide_multi_candidate(
    record: dict[str, Any],
    *,
    policy: MultiCandidatePolicy | None = None,
) -> MultiCandidateDecision:
    """Decide whether extra SQL candidates are worth the latency cost.

    The decision uses runtime-style uncertainty and complexity signals. It does
    not use gold SQL, benchmark correctness, result-match labels, or case IDs.
    """

    p = policy or MultiCandidatePolicy()
    if p.mode == "disabled":
        return MultiCandidateDecision(False, 1, "disabled")
    if p.mode == "always":
        return MultiCandidateDecision(
            True, _clamp(p.max_candidates, p.adaptive_candidates), "always"
        )

    raw_triggers = _adaptive_triggers(record, p)
    triggers, suppressed_triggers = _filter_triggers(raw_triggers, p)
    if not triggers:
        if suppressed_triggers:
            return MultiCandidateDecision(
                False,
                _clamp(p.max_candidates, p.default_candidates),
                "triggers_filtered_by_policy",
                suppressed_triggers=suppressed_triggers,
            )
        return MultiCandidateDecision(
            False,
            _clamp(p.max_candidates, p.default_candidates),
            "simple_or_confident_query",
        )
    return MultiCandidateDecision(
        True,
        _clamp(p.max_candidates, p.adaptive_candidates),
        "adaptive_triggers_present",
        triggers=triggers,
        suppressed_triggers=suppressed_triggers,
    )


def multi_candidate_policy_from_config(
    config: dict[str, Any] | None,
) -> MultiCandidatePolicy:
    runtime_config = config or {}
    return MultiCandidatePolicy(
        allowed_triggers=_trigger_tuple_or_none(
            runtime_config.get("multi_candidate_allowed_triggers")
        ),
        blocked_triggers=_trigger_tuple(
            runtime_config.get("multi_candidate_blocked_triggers")
        ),
    )


def _trigger_tuple_or_none(value: Any) -> tuple[str, ...] | None:
    if value is None:
        return None
    return _trigger_tuple(value)


def _trigger_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_values: Iterable[Any] = value.split(",")
    elif isinstance(value, Iterable):
        raw_values = value
    else:
        raw_values = (value,)
    return tuple(
        sorted({str(item).strip() for item in raw_values if str(item).strip()})
    )


def _adaptive_triggers(
    record: dict[str, Any], policy: MultiCandidatePolicy
) -> list[str]:
    triggers: list[str] = []
    retry_count = _int_or_default(record.get("retry_count"), 0)
    if retry_count > 0:
        triggers.append("retry_in_progress")
    if (
        _generation_was_attempted(record, retry_count=retry_count)
        and record.get("generated_sql") is None
        and record.get("sql") is None
        and record.get("should_generate_sql") is not False
    ):
        triggers.append("missing_generated_sql")
    if (
        record.get("valid_sql") is False
        or record.get("validation_errors")
        or record.get("validation_issues")
    ):
        triggers.append("validation_failed")
    if record.get("execution_error"):
        triggers.append("execution_failed")

    confidence = _float_or_none(record.get("intent_confidence"))
    if confidence is not None and confidence < policy.low_confidence_threshold:
        triggers.append("low_intent_confidence")

    intent = str(record.get("intent") or "").lower()
    if intent in _COMPLEX_INTENTS and _has_complexity_marker(record):
        triggers.append("complex_intent")

    category = str(record.get("category") or "").lower()
    if category in _COMPLEX_CATEGORIES:
        triggers.append("complex_category")

    difficulty = str(record.get("difficulty") or "").lower()
    if difficulty in {"hard", "complex"}:
        triggers.append("difficulty_hint")

    return sorted(set(triggers))


def _filter_triggers(
    triggers: list[str],
    policy: MultiCandidatePolicy,
) -> tuple[list[str], list[str]]:
    allowed = (
        set(policy.allowed_triggers) if policy.allowed_triggers is not None else None
    )
    blocked = set(policy.blocked_triggers)
    kept = sorted(
        {
            trigger
            for trigger in triggers
            if (allowed is None or trigger in allowed) and trigger not in blocked
        }
    )
    suppressed = sorted(set(triggers) - set(kept))
    return kept, suppressed


def _has_complexity_marker(record: dict[str, Any]) -> bool:
    qir = record.get("qir")
    qir_dict = qir if isinstance(qir, dict) else {}
    if qir_dict.get("chart_intent") or qir_dict.get("time_range"):
        return True
    if (
        len(qir_dict.get("metrics") or []) > 1
        or len(qir_dict.get("dimensions") or []) > 1
    ):
        return True
    if qir_dict.get("expected_result_shape") == "table" and (
        len(qir_dict.get("dimensions") or []) >= 1
        or len(qir_dict.get("metrics") or []) >= 1
    ):
        return True

    text = " ".join(
        str(record.get(key) or "")
        for key in ("question", "normalized_question", "raw_question")
    ).lower()
    markers = (
        "dashboard",
        "matrix",
        "quartile",
        "percentile",
        "change",
        "\u062f\u0627\u0634\u0628\u0648\u0631\u062f",
        "\u0645\u0627\u062a\u0631\u06cc\u0633",
        "\u0686\u0647\u0627\u0631\u06a9",
        "\u062a\u063a\u06cc\u06cc\u0631",
    )
    return any(marker in text for marker in markers)


def _generation_was_attempted(record: dict[str, Any], *, retry_count: int) -> bool:
    if record.get("generation_attempted"):
        return True
    if retry_count > 0:
        return True
    if record.get("attempts"):
        return True
    if (
        record.get("validation_errors")
        or record.get("validation_issues")
        or record.get("execution_error")
    ):
        return True
    actual_action = str(record.get("actual_action") or "")
    return actual_action in {
        "generate_sql",
        "format_answer",
        "fail_gracefully",
        "ask_clarification",
    }


def _clamp(max_value: int, value: int) -> int:
    return max(1, min(max_value, value))


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
