from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import time
from typing import Any, Literal

CandidateVerifierAction = Literal["select", "clarify"]

GOLD_LEAKAGE_KEYS = {
    "case_id",
    "id",
    "audit_id",
    "source_id",
    "gold_sql",
    "expected_sql",
    "gold_result_hash",
    "gold_result_preview",
    "expected_result_hash",
    "expected_result_preview",
    "execution_correct",
    "result_match",
    "ok",
    "error",
    "benchmark_error",
    "strict_policy_label",
    "semantic_policy_label",
    "combined_label",
    "semantic_business_correct",
    "judge_label",
}

UNSAFE_ISSUE_MARKERS = (
    "FORBIDDEN",
    "NOT_SELECT",
    "MULTIPLE_STATEMENTS",
    "SQL_COMMENT",
    "SELECT_STAR",
    "PRIVACY_",
    "SAFETY",
)
SCHEMA_ISSUE_MARKERS = (
    "UNKNOWN_COLUMN",
    "UNKNOWN_TABLE",
    "SCHEMA",
    "JOIN",
)
SHAPE_ISSUE_MARKERS = (
    "ANALYTICAL_SHAPE",
    "SHAPE",
)


@dataclass(slots=True)
class CandidateVerificationReport:
    action: CandidateVerifierAction
    reason: str
    selected_candidate_id: str | None
    candidates: list[dict[str, Any]]
    disagreement_high: bool = False
    issues: list[dict[str, Any]] = field(default_factory=list)
    score_version: str = "runtime_v1"
    latency_ms: int | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "action": self.action,
            "reason": self.reason,
            "selected_candidate_id": self.selected_candidate_id,
            "disagreement_high": self.disagreement_high,
            "issues": [dict(issue) for issue in self.issues],
            "score_version": self.score_version,
            "score_inputs": [
                "validation_ok",
                "execution_ok",
                "shape_ok",
                "schema_coverage",
                "value_coverage",
                "candidate_agreement",
                "unsafe_penalty",
                "schema_error_penalty",
                "shape_error_penalty",
            ],
        }
        if self.latency_ms is not None:
            payload["latency_ms"] = self.latency_ms
        return payload


def verify_sql_candidates(
    candidates: list[dict[str, Any]],
    *,
    consistency_report: dict[str, Any] | None = None,
    schema_context: dict[str, Any] | None = None,
    value_links: dict[str, Any] | None = None,
) -> CandidateVerificationReport:
    """Score SQL candidates using runtime-only signals and select or clarify.

    The verifier intentionally ignores benchmark IDs, gold SQL, result-match
    labels, and policy labels. It can therefore be used in real runtime traces
    and benchmark ablations without gold leakage.
    """

    started = time.perf_counter()
    sanitized = [_sanitize_candidate(candidate) for candidate in candidates]
    consistency = consistency_report if isinstance(consistency_report, dict) else {}
    hard_issues = _hard_consistency_issues(consistency)
    disagreement_high = bool(hard_issues)

    scored = [
        _with_candidate_score(
            candidate,
            candidates=sanitized,
            consistency_report=consistency,
            schema_context=schema_context or {},
            value_links=value_links or {},
        )
        for candidate in sanitized
    ]

    if not scored:
        return _with_latency(
            CandidateVerificationReport(
                action="clarify",
                reason="no_candidates",
                selected_candidate_id=None,
                candidates=[],
                disagreement_high=False,
            ),
            started,
        )

    if disagreement_high:
        return _with_latency(
            CandidateVerificationReport(
                action="clarify",
                reason="candidate_disagreement",
                selected_candidate_id=None,
                candidates=scored,
                disagreement_high=True,
                issues=hard_issues,
            ),
            started,
        )

    viable = [candidate for candidate in scored if _candidate_is_viable(candidate)]
    if not viable:
        return _with_latency(
            CandidateVerificationReport(
                action="clarify",
                reason="no_viable_candidate",
                selected_candidate_id=None,
                candidates=scored,
                disagreement_high=False,
                issues=_listish(consistency.get("issues")),
            ),
            started,
        )

    selected = max(
        viable,
        key=lambda candidate: (
            _candidate_score_value(candidate),
            -_candidate_position(candidate.get("candidate_id"), scored),
        ),
    )
    return _with_latency(
        CandidateVerificationReport(
            action="select",
            reason="best_runtime_candidate",
            selected_candidate_id=str(selected.get("candidate_id")),
            candidates=scored,
            disagreement_high=False,
            issues=_listish(consistency.get("issues")),
        ),
        started,
    )


def _with_latency(
    report: CandidateVerificationReport, started: float
) -> CandidateVerificationReport:
    report.latency_ms = int((time.perf_counter() - started) * 1000)
    return report


def _with_candidate_score(
    candidate: dict[str, Any],
    *,
    candidates: list[dict[str, Any]],
    consistency_report: dict[str, Any],
    schema_context: dict[str, Any],
    value_links: dict[str, Any],
) -> dict[str, Any]:
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    issues = _candidate_issues(candidate)
    validation_ok = candidate.get("valid_sql") is True
    execution_ok = candidate.get("execution_passed") is True
    shape_ok = _candidate_shape_ok(metadata, issues)
    unsafe_penalty = 1.0 if _has_issue_marker(issues, UNSAFE_ISSUE_MARKERS) else 0.0
    schema_error_penalty = 1.0 if _has_issue_marker(issues, SCHEMA_ISSUE_MARKERS) else 0.0
    shape_error_penalty = 1.0 if _has_issue_marker(issues, SHAPE_ISSUE_MARKERS) else 0.0
    schema_coverage = _schema_coverage(candidate.get("sql"), schema_context)
    value_coverage = _value_coverage(candidate.get("sql"), value_links)
    candidate_agreement = _candidate_agreement(candidate, candidates, consistency_report)

    score = (
        (3.0 if validation_ok else 0.0)
        + (3.0 if execution_ok else 0.0)
        + (2.0 if shape_ok else 0.0)
        + schema_coverage
        + value_coverage
        + (2.0 * candidate_agreement)
        - (4.0 * unsafe_penalty)
        - (2.0 * schema_error_penalty)
        - (2.0 * shape_error_penalty)
    )
    score_signals = {
        "score": round(score, 6),
        "validation_ok": validation_ok,
        "execution_ok": execution_ok,
        "shape_ok": shape_ok,
        "schema_coverage": round(schema_coverage, 6),
        "value_coverage": round(value_coverage, 6),
        "candidate_agreement": round(candidate_agreement, 6),
        "unsafe_penalty": unsafe_penalty,
        "schema_error_penalty": schema_error_penalty,
        "shape_error_penalty": shape_error_penalty,
    }
    updated_metadata = {**metadata, "candidate_score": score_signals}
    return {**candidate, "metadata": updated_metadata}


def _sanitize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    sanitized = {key: value for key, value in candidate.items() if key not in GOLD_LEAKAGE_KEYS}
    metadata = sanitized.get("metadata")
    if isinstance(metadata, dict):
        sanitized["metadata"] = {
            key: value for key, value in metadata.items() if key not in GOLD_LEAKAGE_KEYS
        }
    return sanitized


def _hard_consistency_issues(report: dict[str, Any]) -> list[dict[str, Any]]:
    issues = [
        issue
        for issue in _listish(report.get("issues"))
        if isinstance(issue, dict) and str(issue.get("severity") or "error") == "error"
    ]
    if report.get("passed") is False and not issues:
        return [
            {
                "code": "CANDIDATE_CONSISTENCY_FAILED",
                "message": "Candidate consistency failed without a structured issue.",
                "severity": "error",
            }
        ]
    return issues


def _candidate_issues(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    return [
        issue for issue in _listish(metadata.get("validation_errors")) if isinstance(issue, dict)
    ]


def _candidate_shape_ok(metadata: dict[str, Any], issues: list[dict[str, Any]]) -> bool:
    if isinstance(metadata.get("shape_ok"), bool):
        return bool(metadata["shape_ok"])
    return not _has_issue_marker(issues, SHAPE_ISSUE_MARKERS)


def _has_issue_marker(issues: list[dict[str, Any]], markers: tuple[str, ...]) -> bool:
    for issue in issues:
        text = " ".join(str(issue.get(key) or "") for key in ("code", "message", "type")).upper()
        if any(marker in text for marker in markers):
            return True
    return False


def _schema_coverage(sql: Any, schema_context: dict[str, Any]) -> float:
    expected_tables = {str(table).lower() for table in schema_context if table}
    if not expected_tables:
        return 1.0
    lower_sql = str(sql or "").lower()
    hits = sum(1 for table in expected_tables if table in lower_sql)
    return hits / len(expected_tables)


def _value_coverage(sql: Any, value_links: dict[str, Any]) -> float:
    values = [
        str(value).lower()
        for value in value_links.values()
        if value is not None and str(value) != ""
    ]
    if not values:
        return 1.0
    lower_sql = str(sql or "").lower()
    hits = sum(1 for value in values if value in lower_sql)
    return hits / len(values)


def _candidate_agreement(
    candidate: dict[str, Any],
    candidates: list[dict[str, Any]],
    consistency_report: dict[str, Any],
) -> float:
    result_hash = candidate.get("result_hash")
    viable_hashes = Counter(
        other.get("result_hash")
        for other in candidates
        if _candidate_is_viable(other) and other.get("result_hash")
    )
    if result_hash and viable_hashes:
        return viable_hashes.get(result_hash, 0) / sum(viable_hashes.values())
    if consistency_report.get("passed") is True:
        return 0.75
    return 0.0


def _candidate_is_viable(candidate: dict[str, Any]) -> bool:
    return (
        bool(candidate.get("sql"))
        and candidate.get("valid_sql") is True
        and candidate.get("execution_passed") is True
    )


def _candidate_score_value(candidate: dict[str, Any]) -> float:
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    score = (
        metadata.get("candidate_score") if isinstance(metadata.get("candidate_score"), dict) else {}
    )
    try:
        return float(score.get("score"))
    except (TypeError, ValueError):
        return 0.0


def _candidate_position(candidate_id: Any, candidates: list[dict[str, Any]]) -> int:
    for index, candidate in enumerate(candidates):
        if str(candidate.get("candidate_id")) == str(candidate_id):
            return index
    return len(candidates)


def _listish(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
