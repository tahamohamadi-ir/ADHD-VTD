from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from math import ceil
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl

COMPARISON_REQUIRED_FILES = {
    "summary": "multi_candidate_ablation_summary.json",
    "cases": "multi_candidate_ablation_cases.jsonl",
    "report": "multi_candidate_ablation_report.md",
}
AGGREGATE_REQUIRED_SUMMARY_KEYS = {
    "candidate_diversity_summary",
    "component_latency_summary",
    "latency_diagnostics",
}
AGGREGATE_OPTIONAL_SUMMARY_KEYS = {
    "candidate_issue_outcome_summary",
    "latency_regression_summary",
}
COMPONENT_LATENCY_REQUIRED_KEYS = {
    "available_component_stats",
    "unavailable_components",
}
LATENCY_DIAGNOSTIC_REQUIRED_KEYS = {
    "by_adaptive_multi_candidate_policy",
    "by_adaptive_candidate_sql_count",
    "by_adaptive_reliability_gate_action",
    "by_candidate_issue_code",
}
OPTIONAL_COMPONENT_LATENCIES = {
    "candidate_verification_latency_ms",
    "reliability_gate_latency_ms",
}
AGGREGATE_FORBIDDEN_MARKERS = {
    "case_id",
    "gold_sql",
    "generated_sql",
    "execution_correct",
    "strict_policy_label",
    "semantic_policy_label",
    "strict_reference",
    "semantic_business_correct",
}
COMPARISON_ACCEPTANCE_STATUSES = {
    "blocked",
    "eligible_for_review",
    "insufficient_semantic_evidence",
    "needs_review",
}


@dataclass(frozen=True)
class MultiCandidateAblationIssue:
    code: str
    message: str
    path: str | None = None
    severity: str = "error"

    def as_dict(self) -> dict[str, str]:
        payload = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        if self.path is not None:
            payload["path"] = self.path
        return payload


@dataclass(frozen=True)
class MultiCandidateAblationValidationReport:
    ok: bool
    issues: list[MultiCandidateAblationIssue] = field(default_factory=list)
    checked: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [issue.as_dict() for issue in self.issues],
            "checked": self.checked,
        }


def _first_file(root: Path, pattern: str) -> Path:
    matches = sorted(
        path for path in root.glob(pattern) if "_partial_" not in path.name
    )
    if not matches:
        matches = sorted(root.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern!r} found in {root}")
    return matches[0]


def compare_multi_candidate_ablation(
    baseline_artifact_dir: str | Path,
    adaptive_artifact_dir: str | Path,
    *,
    output_dir: str | Path,
    baseline_dual_policy_dir: str | Path | None = None,
    adaptive_dual_policy_dir: str | Path | None = None,
    max_latency_p95_delta_ms: float | None = None,
    max_latency_mean_delta_ms: float | None = None,
) -> dict[str, Path]:
    """Compare single-candidate and adaptive multi-candidate benchmark artifacts.

    This report is intentionally artifact-backed. It reads benchmark and optional
    dual-policy judgment artifacts only; it does not call a model, execute SQL, or
    infer semantic correctness from benchmark IDs or gold SQL.
    """

    baseline = _load_benchmark_artifact(baseline_artifact_dir)
    adaptive = _load_benchmark_artifact(adaptive_artifact_dir)
    baseline_dual = _load_dual_policy_cases(baseline_dual_policy_dir)
    adaptive_dual = _load_dual_policy_cases(adaptive_dual_policy_dir)

    baseline_by_id = {
        str(row.get("id") or row.get("case_id")): row for row in baseline["predictions"]
    }
    adaptive_by_id = {
        str(row.get("id") or row.get("case_id")): row for row in adaptive["predictions"]
    }
    common_ids = sorted(set(baseline_by_id) & set(adaptive_by_id))

    cases: list[dict[str, Any]] = []
    ex_change_counts: Counter[str] = Counter()
    valid_sql_change_counts: Counter[str] = Counter()
    candidate_issue_counts: Counter[str] = Counter()
    semantic_change_counts: Counter[str] = Counter()
    strict_change_counts: Counter[str] = Counter()
    for case_id in common_ids:
        baseline_row = baseline_by_id[case_id]
        adaptive_row = adaptive_by_id[case_id]
        baseline_correct = _execution_correct(baseline_row)
        adaptive_correct = _execution_correct(adaptive_row)
        baseline_valid = bool(baseline_row.get("valid_sql"))
        adaptive_valid = bool(adaptive_row.get("valid_sql"))
        ex_change = _binary_change_label(baseline_correct, adaptive_correct)
        valid_sql_change = _binary_change_label(baseline_valid, adaptive_valid)
        ex_change_counts[ex_change] += 1
        valid_sql_change_counts[valid_sql_change] += 1

        policy = adaptive_row.get("multi_candidate_policy")
        policy_dict = policy if isinstance(policy, dict) else {}
        candidate_consistency = adaptive_row.get("candidate_consistency")
        consistency_dict = (
            candidate_consistency if isinstance(candidate_consistency, dict) else {}
        )
        selected_candidate_id = _selected_candidate_id(adaptive_row, consistency_dict)
        baseline_components = _component_latency_record(baseline_row)
        adaptive_components = _component_latency_record(adaptive_row)
        issue_codes = [
            str(issue.get("code"))
            for issue in consistency_dict.get("issues") or []
            if isinstance(issue, dict) and issue.get("code")
        ]
        candidate_issue_counts.update(issue_codes)

        baseline_policy_label = _dual_policy_labels(baseline_dual.get(case_id))
        adaptive_policy_label = _dual_policy_labels(adaptive_dual.get(case_id))
        semantic_change = _label_change(
            baseline_policy_label.get("semantic_policy_label"),
            adaptive_policy_label.get("semantic_policy_label"),
        )
        strict_change = _label_change(
            baseline_policy_label.get("strict_policy_label"),
            adaptive_policy_label.get("strict_policy_label"),
        )
        semantic_change_counts[semantic_change] += 1
        strict_change_counts[strict_change] += 1

        cases.append(
            {
                "case_id": case_id,
                "baseline_execution_correct": baseline_correct,
                "adaptive_execution_correct": adaptive_correct,
                "execution_change": ex_change,
                "baseline_valid_sql": baseline_valid,
                "adaptive_valid_sql": adaptive_valid,
                "valid_sql_change": valid_sql_change,
                "baseline_error": baseline_row.get("error") or "",
                "adaptive_error": adaptive_row.get("error") or "",
                "baseline_latency_ms": baseline_row.get("latency_ms"),
                "adaptive_latency_ms": adaptive_row.get("latency_ms"),
                "latency_delta_ms": _number_or_none(adaptive_row.get("latency_ms"), 0)
                - _number_or_none(baseline_row.get("latency_ms"), 0),
                "baseline_component_latency_ms": baseline_components,
                "adaptive_component_latency_ms": adaptive_components,
                "adaptive_multi_candidate_enabled": bool(policy_dict.get("enabled")),
                "adaptive_multi_candidate_candidate_count": policy_dict.get(
                    "candidate_count"
                ),
                "adaptive_multi_candidate_triggers": list(
                    policy_dict.get("triggers") or []
                ),
                "adaptive_candidate_sql_count": len(
                    adaptive_row.get("candidate_sqls") or []
                ),
                "adaptive_selected_candidate_id": selected_candidate_id,
                "adaptive_candidate_consistency_passed": consistency_dict.get("passed"),
                "adaptive_candidate_consistency_issue_codes": issue_codes,
                "baseline_reliability_gate_action": baseline_row.get(
                    "reliability_gate_action"
                ),
                "adaptive_reliability_gate_action": adaptive_row.get(
                    "reliability_gate_action"
                ),
                "baseline_semantic_policy_label": baseline_policy_label.get(
                    "semantic_policy_label"
                ),
                "adaptive_semantic_policy_label": adaptive_policy_label.get(
                    "semantic_policy_label"
                ),
                "semantic_policy_change": semantic_change,
                "baseline_strict_policy_label": baseline_policy_label.get(
                    "strict_policy_label"
                ),
                "adaptive_strict_policy_label": adaptive_policy_label.get(
                    "strict_policy_label"
                ),
                "strict_policy_change": strict_change,
            }
        )

    baseline_metrics = _benchmark_metrics(baseline["summary"])
    adaptive_metrics = _benchmark_metrics(adaptive["summary"])
    metric_deltas = _metric_deltas(baseline_metrics, adaptive_metrics)
    activation = _multi_candidate_activation(adaptive["predictions"])
    candidate_diversity = _candidate_diversity_summary(cases)
    candidate_issue_outcomes = _candidate_issue_outcome_summary(cases)
    component_latency = _component_latency_summary(cases)
    latency_diagnostics = _latency_diagnostics(cases)
    latency_regression = _latency_regression_summary(
        latency_diagnostics,
        component_latency,
    )
    acceptance = _acceptance_checks(
        baseline,
        adaptive,
        baseline_metrics=baseline_metrics,
        adaptive_metrics=adaptive_metrics,
        cases=cases,
        baseline_dual_policy_dir=baseline_dual_policy_dir,
        adaptive_dual_policy_dir=adaptive_dual_policy_dir,
        max_latency_p95_delta_ms=max_latency_p95_delta_ms,
        max_latency_mean_delta_ms=max_latency_mean_delta_ms,
    )

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "baseline_artifact_dir": str(baseline_artifact_dir),
        "adaptive_artifact_dir": str(adaptive_artifact_dir),
        "baseline_summary_path": str(baseline["summary_path"]),
        "adaptive_summary_path": str(adaptive["summary_path"]),
        "baseline_predictions_path": str(baseline["predictions_path"]),
        "adaptive_predictions_path": str(adaptive["predictions_path"]),
        "baseline_dual_policy_dir": (
            str(baseline_dual_policy_dir) if baseline_dual_policy_dir else None
        ),
        "adaptive_dual_policy_dir": (
            str(adaptive_dual_policy_dir) if adaptive_dual_policy_dir else None
        ),
        "same_dataset_hash": _config(baseline).get("dataset_hash")
        == _config(adaptive).get("dataset_hash"),
        "same_selected_cases_hash": _config(baseline).get("selected_cases_hash")
        == _config(adaptive).get("selected_cases_hash"),
        "baseline_selected_cases_hash": _config(baseline).get("selected_cases_hash"),
        "adaptive_selected_cases_hash": _config(adaptive).get("selected_cases_hash"),
        "same_model": _config(baseline).get("model_name")
        == _config(adaptive).get("model_name"),
        "baseline_total_predictions": len(baseline["predictions"]),
        "adaptive_total_predictions": len(adaptive["predictions"]),
        "common_cases": len(common_ids),
        "baseline_only_cases": sorted(set(baseline_by_id) - set(adaptive_by_id)),
        "adaptive_only_cases": sorted(set(adaptive_by_id) - set(baseline_by_id)),
        "baseline_metrics": baseline_metrics,
        "adaptive_metrics": adaptive_metrics,
        "metric_deltas": metric_deltas,
        "execution_change_counts": dict(ex_change_counts),
        "valid_sql_change_counts": dict(valid_sql_change_counts),
        "semantic_policy_change_counts": dict(semantic_change_counts),
        "strict_policy_change_counts": dict(strict_change_counts),
        "multi_candidate_activation": activation,
        "candidate_diversity_summary": candidate_diversity,
        "candidate_issue_outcome_summary": candidate_issue_outcomes,
        "component_latency_summary": component_latency,
        "latency_regression_summary": latency_regression,
        "candidate_issue_counts": dict(candidate_issue_counts),
        "latency_diagnostics": latency_diagnostics,
        "acceptance_checks": acceptance,
        "anti_fake_policy": (
            "This report compares existing benchmark and optional dual-policy judgment artifacts only. "
            "It does not run a model, execute SQL, edit predictions, infer missing semantic labels, or "
            "use case IDs/gold SQL as tuning rules."
        ),
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    cases_path = write_jsonl(
        output_root / "multi_candidate_ablation_cases.jsonl", cases
    )
    summary_path = write_json(
        output_root / "multi_candidate_ablation_summary.json", summary
    )
    report_path = output_root / "multi_candidate_ablation_report.md"
    report_path.write_text(_render_report(summary, cases), encoding="utf-8")
    return {"summary": summary_path, "cases": cases_path, "report": report_path}


def validate_multi_candidate_ablation_artifact(
    root: str | Path,
) -> MultiCandidateAblationValidationReport:
    """Validate a diagnostic multi-candidate comparison artifact.

    The validator is intentionally artifact-only. It does not execute SQL, call a
    model, infer semantic labels, or inspect gold references.
    """

    artifact_root = Path(root)
    issues: list[MultiCandidateAblationIssue] = []
    checked: dict[str, Any] = {"artifact_dir": str(artifact_root)}
    required_paths = {
        name: artifact_root / relative
        for name, relative in COMPARISON_REQUIRED_FILES.items()
    }
    checked["required_files"] = {
        name: str(path) for name, path in required_paths.items()
    }
    missing = [name for name, path in required_paths.items() if not path.exists()]
    checked["missing_files"] = missing
    for name in missing:
        issues.append(
            MultiCandidateAblationIssue(
                code="COMPARISON_REQUIRED_FILE_MISSING",
                message=f"Missing multi-candidate comparison file: {name}.",
                path=str(required_paths[name]),
            )
        )
    if issues:
        return MultiCandidateAblationValidationReport(False, issues, checked)

    summary_path = required_paths["summary"]
    cases_path = required_paths["cases"]
    report_path = required_paths["report"]
    summary = read_json(summary_path)
    cases = read_jsonl(cases_path)
    report_text = report_path.read_text(encoding="utf-8")

    common_cases = int(summary.get("common_cases") or 0)
    checked["common_cases"] = common_cases
    checked["case_rows"] = len(cases)
    if common_cases != len(cases):
        issues.append(
            MultiCandidateAblationIssue(
                code="COMPARISON_CASE_COUNT_MISMATCH",
                message=(
                    "Comparison case rows must match summary common_cases "
                    f"({len(cases)} rows vs {common_cases})."
                ),
                path=str(cases_path),
            )
        )

    missing_keys = sorted(AGGREGATE_REQUIRED_SUMMARY_KEYS - set(summary))
    checked["aggregate_summary_keys_present"] = not missing_keys
    checked["missing_aggregate_summary_keys"] = missing_keys
    for key in missing_keys:
        issues.append(
            MultiCandidateAblationIssue(
                code="COMPARISON_AGGREGATE_SUMMARY_MISSING",
                message=f"Comparison summary is missing aggregate section {key!r}.",
                path=str(summary_path),
            )
        )

    aggregate_keys_to_validate = (
        AGGREGATE_REQUIRED_SUMMARY_KEYS | AGGREGATE_OPTIONAL_SUMMARY_KEYS
    ) & set(summary)
    for key in sorted(aggregate_keys_to_validate):
        payload = summary.get(key)
        if not isinstance(payload, dict):
            issues.append(
                MultiCandidateAblationIssue(
                    code="COMPARISON_AGGREGATE_SUMMARY_INVALID",
                    message=f"Aggregate section {key!r} must be a JSON object.",
                    path=str(summary_path),
                )
            )
            continue
        anti_tuning_policy = str(payload.get("anti_tuning_policy") or "").lower()
        if (
            "aggregate" not in anti_tuning_policy
            or "gold sql" not in anti_tuning_policy
        ):
            issues.append(
                MultiCandidateAblationIssue(
                    code="COMPARISON_ANTI_TUNING_POLICY_MISSING",
                    message=f"Aggregate section {key!r} must state its anti-tuning policy.",
                    path=str(summary_path),
                )
            )
        leaked = _aggregate_forbidden_markers(payload)
        checked[f"{key}_forbidden_markers"] = leaked
        for marker in leaked:
            issues.append(
                MultiCandidateAblationIssue(
                    code="COMPARISON_AGGREGATE_LEAKAGE_FIELD",
                    message=(
                        f"Aggregate section {key!r} must not include case-level "
                        f"or reference marker {marker!r}."
                    ),
                    path=str(summary_path),
                )
            )
        if key == "latency_diagnostics":
            missing_latency_keys = sorted(
                LATENCY_DIAGNOSTIC_REQUIRED_KEYS - set(payload)
            )
            checked[
                "latency_diagnostics_required_keys_present"
            ] = not missing_latency_keys
            checked["latency_diagnostics_missing_required_keys"] = missing_latency_keys
            for missing_key in missing_latency_keys:
                issues.append(
                    MultiCandidateAblationIssue(
                        code="COMPARISON_LATENCY_DIAGNOSTIC_KEY_MISSING",
                        message=(
                            "Latency diagnostics must include aggregate grouping "
                            f"{missing_key!r}."
                        ),
                        path=str(summary_path),
                    )
                )
        if key == "component_latency_summary":
            missing_component_keys = sorted(
                COMPONENT_LATENCY_REQUIRED_KEYS - set(payload)
            )
            checked[
                "component_latency_required_keys_present"
            ] = not missing_component_keys
            checked["component_latency_missing_required_keys"] = missing_component_keys
            for missing_key in missing_component_keys:
                issues.append(
                    MultiCandidateAblationIssue(
                        code="COMPARISON_COMPONENT_LATENCY_KEY_MISSING",
                        message=(
                            "Component latency summary must include aggregate key "
                            f"{missing_key!r}."
                        ),
                        path=str(summary_path),
                    )
                )

    acceptance = summary.get("acceptance_checks")
    acceptance_status = (
        acceptance.get("status") if isinstance(acceptance, dict) else None
    )
    semantic_evidence_available = (
        acceptance.get("semantic_evidence_available")
        if isinstance(acceptance, dict)
        else None
    )
    checked["acceptance_status"] = acceptance_status
    checked["semantic_evidence_available"] = semantic_evidence_available
    if not isinstance(acceptance, dict):
        issues.append(
            MultiCandidateAblationIssue(
                code="COMPARISON_ACCEPTANCE_CHECKS_MISSING",
                message="Comparison summary must include acceptance_checks as a JSON object.",
                path=str(summary_path),
            )
        )
    normalized_acceptance_status = str(acceptance_status or "").strip().lower()
    if isinstance(acceptance, dict):
        checked["acceptance_status_normalized"] = normalized_acceptance_status
    if isinstance(acceptance, dict) and normalized_acceptance_status not in (
        COMPARISON_ACCEPTANCE_STATUSES
    ):
        issues.append(
            MultiCandidateAblationIssue(
                code="COMPARISON_ACCEPTANCE_STATUS_INVALID",
                message=(
                    "Comparison acceptance_checks.status must be one of: "
                    f"{', '.join(sorted(COMPARISON_ACCEPTANCE_STATUSES))}."
                ),
                path=str(summary_path),
            )
        )
    if isinstance(acceptance, dict) and not isinstance(
        semantic_evidence_available, bool
    ):
        issues.append(
            MultiCandidateAblationIssue(
                code="COMPARISON_SEMANTIC_EVIDENCE_FLAG_INVALID",
                message=(
                    "Comparison acceptance_checks.semantic_evidence_available "
                    "must be a boolean."
                ),
                path=str(summary_path),
            )
        )
    raw_blockers = (
        acceptance.get("blocker_reasons") if isinstance(acceptance, dict) else []
    )
    acceptance_blockers = raw_blockers if isinstance(raw_blockers, list) else []
    checked["acceptance_blockers"] = acceptance_blockers
    if isinstance(acceptance, dict):
        raw_blockers = acceptance.get("blocker_reasons") or []
        if not isinstance(raw_blockers, list) or any(
            not isinstance(blocker, str) for blocker in raw_blockers
        ):
            issues.append(
                MultiCandidateAblationIssue(
                    code="COMPARISON_ACCEPTANCE_BLOCKERS_INVALID",
                    message=(
                        "Comparison acceptance_checks.blocker_reasons must be "
                        "a list of strings when present."
                    ),
                    path=str(summary_path),
                )
            )
    latency_budget = (
        acceptance.get("latency_budget") if isinstance(acceptance, dict) else None
    )
    checked["latency_budget_configured"] = bool(
        latency_budget.get("configured") if isinstance(latency_budget, dict) else False
    )
    checked["latency_budget_exceeded"] = bool(
        latency_budget.get("exceeded") if isinstance(latency_budget, dict) else False
    )
    promotion_blockers = _comparison_promotion_blockers(
        acceptance_status,
        semantic_evidence_available,
        acceptance_blockers,
    )
    checked["promotion_blockers"] = promotion_blockers
    checked["promotion_eligible"] = not promotion_blockers
    checked["promotion_status"] = (
        "eligible_for_review"
        if not promotion_blockers
        else (
            "blocked_until_authoritative_semantic_evidence"
            if "semantic_evidence_unavailable" in promotion_blockers
            else "blocked_by_acceptance_checks"
        )
    )
    anti_fake_policy = str(summary.get("anti_fake_policy") or "").lower()
    checked["anti_fake_policy_present"] = bool(anti_fake_policy)
    if (
        "does not run a model" not in anti_fake_policy
        or "gold sql" not in anti_fake_policy
    ):
        issues.append(
            MultiCandidateAblationIssue(
                code="COMPARISON_ANTI_FAKE_POLICY_INCOMPLETE",
                message=(
                    "Comparison summary must state that it does not run a model "
                    "or use gold SQL as tuning rules."
                ),
                path=str(summary_path),
            )
        )
    checked["report_mentions_aggregate_policy"] = (
        "Aggregate Diagnostic Policy" in report_text
    )
    if "Aggregate Diagnostic Policy" not in report_text:
        issues.append(
            MultiCandidateAblationIssue(
                code="COMPARISON_REPORT_AGGREGATE_POLICY_MISSING",
                message="Comparison report must document aggregate diagnostic policy.",
                path=str(report_path),
            )
        )

    return MultiCandidateAblationValidationReport(
        ok=not issues, issues=issues, checked=checked
    )


def _comparison_promotion_blockers(
    acceptance_status: Any,
    semantic_evidence_available: Any,
    acceptance_blockers: list[str] | None = None,
) -> list[str]:
    blockers: list[str] = []
    normalized_status = str(acceptance_status or "").strip().lower()
    if normalized_status != "eligible_for_review":
        blockers.append(f"acceptance_status_{normalized_status or 'missing'}")
    for blocker in acceptance_blockers or []:
        normalized_blocker = str(blocker).strip().lower()
        if normalized_blocker and normalized_blocker not in blockers:
            blockers.append(normalized_blocker)
    if semantic_evidence_available is not True:
        blockers.append("semantic_evidence_unavailable")
    return blockers


def _aggregate_forbidden_markers(payload: dict[str, Any]) -> list[str]:
    serialized = json_safe_dumps(payload).lower()
    return sorted(
        marker for marker in AGGREGATE_FORBIDDEN_MARKERS if marker in serialized
    )


def json_safe_dumps(payload: Any) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _load_benchmark_artifact(root: str | Path) -> dict[str, Any]:
    artifact_root = Path(root)
    summary_path = _first_file(artifact_root, "*_summary.json")
    predictions_path = _first_file(artifact_root, "*_predictions.jsonl")
    return {
        "root": artifact_root,
        "summary_path": summary_path,
        "predictions_path": predictions_path,
        "summary": read_json(summary_path),
        "predictions": read_jsonl(predictions_path),
    }


def _load_dual_policy_cases(root: str | Path | None) -> dict[str, dict[str, Any]]:
    if not root:
        return {}
    path = Path(root)
    cases_path = path / "dual_policy_cases.jsonl"
    if not cases_path.exists():
        return {}
    return {str(row.get("case_id")): row for row in read_jsonl(cases_path)}


def _dual_policy_evidence(root: str | Path | None) -> dict[str, Any]:
    if not root:
        return {
            "available": False,
            "authoritative": False,
            "complete": False,
            "common_cases": 0,
            "blocking_counts": {},
        }
    path = Path(root)
    summary_path = path / "dual_policy_summary.json"
    if not summary_path.exists():
        return {
            "available": False,
            "authoritative": False,
            "complete": False,
            "common_cases": 0,
            "blocking_counts": {"missing_summary": 1},
        }
    summary = read_json(summary_path)
    blocking_counts = _dual_policy_blocking_counts(summary)
    authoritative = summary.get("authoritative") is True
    common_cases = int(summary.get("common_cases") or 0)
    complete = common_cases > 0 and not blocking_counts
    return {
        "available": authoritative and complete,
        "authoritative": authoritative,
        "complete": complete,
        "common_cases": common_cases,
        "blocking_counts": blocking_counts,
    }


def _dual_policy_blocking_counts(summary: dict[str, Any]) -> dict[str, int]:
    blockers = {
        "adjudication_required",
        "partial_business_match",
        "partial_or_mixed",
        "unjudged",
    }
    blocking: dict[str, int] = {}
    for group_name in ("semantic_counts", "strict_counts", "combined_counts"):
        counts = summary.get(group_name)
        if not isinstance(counts, dict):
            continue
        for label, count in counts.items():
            if label in blockers and int(count or 0) > 0:
                blocking[f"{group_name}.{label}"] = int(count)
    return blocking


def _config(artifact: dict[str, Any]) -> dict[str, Any]:
    summary = (
        artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    )
    config = summary.get("config")
    return config if isinstance(config, dict) else {}


def _benchmark_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    metrics = summary.get("metrics") if isinstance(summary.get("metrics"), dict) else {}
    reliability = (
        summary.get("reliability")
        if isinstance(summary.get("reliability"), dict)
        else {}
    )
    latency = summary.get("latency") if isinstance(summary.get("latency"), dict) else {}
    dataset = summary.get("dataset") if isinstance(summary.get("dataset"), dict) else {}
    return {
        "total_evaluated": dataset.get("total_evaluated"),
        "execution_accuracy": _metric_value(metrics, "execution_accuracy"),
        "valid_sql_rate": _metric_value(metrics, "valid_sql_rate"),
        "reliability_score": reliability.get("score"),
        "unsafe_sql": reliability.get("unsafe_sql"),
        "latency_mean_ms": latency.get("mean_ms"),
        "latency_median_ms": latency.get("median_ms"),
        "latency_p95_ms": latency.get("p95_ms"),
    }


def _metric_value(metrics: dict[str, Any], name: str) -> Any:
    metric = metrics.get(name)
    if isinstance(metric, dict):
        return metric.get("value")
    return None


def _metric_deltas(
    baseline: dict[str, Any], adaptive: dict[str, Any]
) -> dict[str, Any]:
    deltas: dict[str, Any] = {}
    for key, baseline_value in baseline.items():
        adaptive_value = adaptive.get(key)
        if isinstance(baseline_value, (int, float)) and isinstance(
            adaptive_value, (int, float)
        ):
            deltas[key] = round(float(adaptive_value) - float(baseline_value), 6)
    return deltas


def _execution_correct(row: dict[str, Any]) -> bool:
    return bool(
        row.get("execution_correct") or row.get("result_match") or row.get("ok")
    )


def _binary_change_label(before: bool, after: bool) -> str:
    if before and after:
        return "remained_correct"
    if not before and not after:
        return "remained_wrong"
    if before and not after:
        return "regressed_correct_to_wrong"
    return "improved_wrong_to_correct"


def _dual_policy_labels(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {"semantic_policy_label": None, "strict_policy_label": None}
    return {
        "semantic_policy_label": row.get("semantic_policy_label"),
        "strict_policy_label": row.get("strict_policy_label"),
    }


def _label_change(before: Any, after: Any) -> str:
    if before is None or after is None:
        return "unavailable"
    if before == after:
        return f"remained_{before}"
    if before == "correct" and after != "correct":
        return "regressed_correct_to_not_correct"
    if before != "correct" and after == "correct":
        return "improved_to_correct"
    return f"changed_{before}_to_{after}"


def _multi_candidate_activation(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    policy_counts: Counter[str] = Counter()
    trigger_counts: Counter[str] = Counter()
    candidate_count_distribution: Counter[str] = Counter()
    generated_candidate_count_distribution: Counter[str] = Counter()
    for record in predictions:
        policy = record.get("multi_candidate_policy")
        policy_dict = policy if isinstance(policy, dict) else {}
        enabled = bool(policy_dict.get("enabled"))
        policy_counts["enabled" if enabled else "disabled"] += 1
        candidate_count_distribution[str(policy_dict.get("candidate_count") or 0)] += 1
        generated_candidate_count_distribution[
            str(len(record.get("candidate_sqls") or []))
        ] += 1
        for trigger in policy_dict.get("triggers") or []:
            trigger_counts[str(trigger)] += 1
    total = len(predictions)
    return {
        "policy_counts": dict(policy_counts),
        "trigger_counts": dict(trigger_counts),
        "policy_candidate_count_distribution": dict(candidate_count_distribution),
        "generated_candidate_count_distribution": dict(
            generated_candidate_count_distribution
        ),
        "activation_rate": round(policy_counts.get("enabled", 0) / total, 6)
        if total
        else 0.0,
    }


def _selected_candidate_id(
    row: dict[str, Any], consistency: dict[str, Any]
) -> str | None:
    direct = row.get("selected_candidate_id")
    if direct:
        return str(direct)
    verification = row.get("candidate_verification")
    if isinstance(verification, dict) and verification.get("selected_candidate_id"):
        return str(verification["selected_candidate_id"])
    if consistency.get("selected_candidate_id"):
        return str(consistency["selected_candidate_id"])
    return None


def _candidate_diversity_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    enabled_counts: Counter[str] = Counter()
    policy_candidate_counts: Counter[str] = Counter()
    generated_candidate_counts: Counter[str] = Counter()
    selected_rank_counts: Counter[str] = Counter()
    consistency_counts: Counter[str] = Counter()
    trigger_counts: Counter[str] = Counter()
    issue_counts: Counter[str] = Counter()
    for row in cases:
        enabled_counts[
            "enabled" if row["adaptive_multi_candidate_enabled"] else "disabled"
        ] += 1
        policy_candidate_counts[
            str(row.get("adaptive_multi_candidate_candidate_count") or 0)
        ] += 1
        generated_candidate_counts[
            str(row.get("adaptive_candidate_sql_count") or 0)
        ] += 1
        selected_rank_counts[
            _candidate_rank_label(row.get("adaptive_selected_candidate_id"))
        ] += 1
        consistency_counts[
            _consistency_label(row.get("adaptive_candidate_consistency_passed"))
        ] += 1
        for trigger in row.get("adaptive_multi_candidate_triggers") or []:
            trigger_counts[str(trigger)] += 1
        for issue in row.get("adaptive_candidate_consistency_issue_codes") or []:
            issue_counts[str(issue)] += 1
    return {
        "total_common_cases": len(cases),
        "adaptive_multi_candidate_policy_counts": dict(enabled_counts),
        "adaptive_policy_candidate_count_distribution": dict(policy_candidate_counts),
        "adaptive_generated_candidate_count_distribution": dict(
            generated_candidate_counts
        ),
        "adaptive_selected_candidate_rank_counts": dict(selected_rank_counts),
        "adaptive_non_primary_selection_count": selected_rank_counts.get(
            "non_primary_candidate", 0
        ),
        "adaptive_candidate_consistency_counts": dict(consistency_counts),
        "adaptive_trigger_counts": dict(trigger_counts),
        "candidate_issue_counts": dict(issue_counts),
        "anti_tuning_policy": (
            "Aggregate diagnostic only. This summary excludes case IDs, gold SQL, "
            "generated SQL text, and strict or semantic correctness labels."
        ),
    }


def _candidate_issue_outcome_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, dict[str, Any]] = {}
    no_issue_cases = 0
    multi_issue_cases = 0
    for row in cases:
        issue_codes = [
            str(issue)
            for issue in (row.get("adaptive_candidate_consistency_issue_codes") or [])
            if issue
        ]
        if not issue_codes:
            no_issue_cases += 1
            issue_codes = ["no_candidate_issue"]
        elif len(issue_codes) > 1:
            multi_issue_cases += 1

        for issue_code in issue_codes:
            group = groups.setdefault(
                issue_code,
                {
                    "case_count": 0,
                    "execution_change_counts": Counter(),
                    "valid_sql_change_counts": Counter(),
                    "selected_candidate_rank_counts": Counter(),
                    "candidate_consistency_counts": Counter(),
                    "reliability_gate_action_counts": Counter(),
                },
            )
            group["case_count"] += 1
            group["execution_change_counts"][str(row.get("execution_change"))] += 1
            group["valid_sql_change_counts"][str(row.get("valid_sql_change"))] += 1
            group["selected_candidate_rank_counts"][
                _candidate_rank_label(row.get("adaptive_selected_candidate_id"))
            ] += 1
            group["candidate_consistency_counts"][
                _consistency_label(row.get("adaptive_candidate_consistency_passed"))
            ] += 1
            group["reliability_gate_action_counts"][
                _aggregate_key(row.get("adaptive_reliability_gate_action"))
            ] += 1

    normalized_groups: dict[str, dict[str, Any]] = {}
    for issue_code, group in sorted(groups.items()):
        normalized_groups[issue_code] = {
            "case_count": int(group["case_count"]),
            "execution_change_counts": dict(group["execution_change_counts"]),
            "valid_sql_change_counts": dict(group["valid_sql_change_counts"]),
            "selected_candidate_rank_counts": dict(
                group["selected_candidate_rank_counts"]
            ),
            "candidate_consistency_counts": dict(group["candidate_consistency_counts"]),
            "reliability_gate_action_counts": dict(
                group["reliability_gate_action_counts"]
            ),
        }

    return {
        "scope": "aggregate_candidate_issue_outcomes_only",
        "total_common_cases": len(cases),
        "no_candidate_issue_cases": no_issue_cases,
        "multi_issue_cases": multi_issue_cases,
        "issue_groups": normalized_groups,
        "counting_policy": (
            "Cases with multiple candidate issue codes contribute once to each "
            "issue-code group. The no_candidate_issue group contains cases with "
            "no adaptive candidate consistency issue code."
        ),
        "anti_tuning_policy": (
            "Aggregate diagnostic only. This summary excludes case IDs, gold SQL, "
            "generated SQL text, and strict or semantic correctness labels."
        ),
    }


def _candidate_rank_label(candidate_id: Any) -> str:
    if not candidate_id:
        return "none"
    text = str(candidate_id).strip().lower()
    prefix = "candidate_"
    if text.startswith(prefix):
        suffix = text[len(prefix) :]
        if suffix.isdigit():
            return "primary_candidate" if int(suffix) == 1 else "non_primary_candidate"
    return "other_candidate"


def _consistency_label(value: Any) -> str:
    if value is True:
        return "passed"
    if value is False:
        return "failed"
    return "unknown"


def _latency_diagnostics(
    cases: list[dict[str, Any]], *, high_latency_threshold_ms: float = 60000.0
) -> dict[str, Any]:
    baseline_latencies = [
        value
        for value in (_optional_number(row.get("baseline_latency_ms")) for row in cases)
        if value is not None
    ]
    adaptive_latencies = [
        value
        for value in (_optional_number(row.get("adaptive_latency_ms")) for row in cases)
        if value is not None
    ]
    deltas = [
        value
        for value in (_optional_number(row.get("latency_delta_ms")) for row in cases)
        if value is not None
    ]
    by_enabled: dict[str, dict[str, Any]] = {}
    for enabled_label in ("enabled", "disabled"):
        group = [
            row
            for row in cases
            if ("enabled" if row["adaptive_multi_candidate_enabled"] else "disabled")
            == enabled_label
        ]
        by_enabled[enabled_label] = _latency_group_summary(group)

    by_candidate_count: dict[str, dict[str, Any]] = {}
    for candidate_count in sorted(
        {str(row.get("adaptive_candidate_sql_count") or 0) for row in cases}
    ):
        group = [
            row
            for row in cases
            if str(row.get("adaptive_candidate_sql_count") or 0) == candidate_count
        ]
        by_candidate_count[candidate_count] = _latency_group_summary(group)

    by_reliability_action: dict[str, dict[str, Any]] = {}
    for action in sorted(
        {_aggregate_key(row.get("adaptive_reliability_gate_action")) for row in cases}
    ):
        group = [
            row
            for row in cases
            if _aggregate_key(row.get("adaptive_reliability_gate_action")) == action
        ]
        by_reliability_action[action] = _latency_group_summary(group)

    issue_codes = sorted(
        {
            str(issue)
            for row in cases
            for issue in (row.get("adaptive_candidate_consistency_issue_codes") or [])
        }
    )
    by_issue_code = {
        issue_code: _latency_group_summary(
            [
                row
                for row in cases
                if issue_code
                in (row.get("adaptive_candidate_consistency_issue_codes") or [])
            ]
        )
        for issue_code in issue_codes
    }

    adaptive_high_count = sum(
        1 for value in adaptive_latencies if value >= high_latency_threshold_ms
    )
    delta_high_count = sum(1 for value in deltas if value >= high_latency_threshold_ms)
    return {
        "scope": "aggregate_latency_only",
        "high_latency_threshold_ms": high_latency_threshold_ms,
        "overall": {
            "baseline_latency_ms": _latency_stats(baseline_latencies),
            "adaptive_latency_ms": _latency_stats(adaptive_latencies),
            "latency_delta_ms": _latency_stats(deltas),
            "adaptive_high_latency_count": adaptive_high_count,
            "latency_delta_high_count": delta_high_count,
        },
        "by_adaptive_multi_candidate_policy": by_enabled,
        "by_adaptive_candidate_sql_count": by_candidate_count,
        "by_adaptive_reliability_gate_action": by_reliability_action,
        "by_candidate_issue_code": by_issue_code,
        "anti_tuning_policy": (
            "Aggregate diagnostic only. This summary excludes case IDs, gold SQL, "
            "generated SQL text, and strict or semantic correctness labels."
        ),
    }


def _component_latency_record(row: dict[str, Any]) -> dict[str, float]:
    attempts = [item for item in row.get("attempts") or [] if isinstance(item, dict)]
    candidates = [
        item for item in row.get("candidate_sqls") or [] if isinstance(item, dict)
    ]
    candidate_verification = _payload_dict(row.get("candidate_verification"))
    reliability_gate = _payload_dict(row.get("reliability_gate"))
    reliability_decision = _payload_dict(row.get("reliability_decision"))
    components = {
        "total_pipeline_latency_ms": _optional_number(row.get("latency_ms")),
        "attempt_generation_latency_ms": _sum_numbers(
            attempt.get("generation_latency_ms") for attempt in attempts
        ),
        "attempt_execution_latency_ms": _sum_numbers(
            attempt.get("latency_ms") for attempt in attempts
        ),
        "candidate_execution_latency_ms": _sum_numbers(
            _candidate_execution_latency(candidate) for candidate in candidates
        ),
        "candidate_verification_latency_ms": _first_optional_number(
            row.get("candidate_verification_latency_ms"),
            candidate_verification.get("latency_ms"),
        ),
        "reliability_gate_latency_ms": _first_optional_number(
            row.get("reliability_gate_latency_ms"),
            reliability_gate.get("latency_ms"),
            row.get("graph_reliability_gate_latency_ms"),
            reliability_decision.get("latency_ms"),
        ),
    }
    return {key: value for key, value in components.items() if value is not None}


def _candidate_execution_latency(candidate: dict[str, Any]) -> Any:
    metadata = candidate.get("metadata")
    if not isinstance(metadata, dict):
        return None
    return metadata.get("execution_latency_ms")


def _sum_numbers(values: Iterable[Any]) -> float | None:
    numbers = [
        number
        for number in (_optional_number(value) for value in values)
        if number is not None
    ]
    return round(sum(numbers), 3) if numbers else None


def _component_latency_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    component_names = sorted(
        {
            component
            for row in cases
            for side in (
                "baseline_component_latency_ms",
                "adaptive_component_latency_ms",
            )
            for component in (row.get(side) or {})
        }
    )
    available_component_stats: dict[str, dict[str, Any]] = {}
    for component in component_names:
        baseline_values = _component_values(
            cases, "baseline_component_latency_ms", component
        )
        adaptive_values = _component_values(
            cases, "adaptive_component_latency_ms", component
        )
        deltas = _component_deltas(cases, component)
        available_component_stats[component] = {
            "baseline_ms": _latency_stats(baseline_values),
            "adaptive_ms": _latency_stats(adaptive_values),
            "delta_ms": _latency_stats(deltas),
            "observed_baseline_cases": len(baseline_values),
            "observed_adaptive_cases": len(adaptive_values),
            "observed_delta_cases": len(deltas),
        }
    unavailable_components = {
        component: "not_recorded_in_prediction_trace"
        for component in sorted(OPTIONAL_COMPONENT_LATENCIES - set(component_names))
    }
    return {
        "scope": "recorded_component_latency_only",
        "available_component_stats": available_component_stats,
        "unavailable_components": unavailable_components,
        "component_definitions": {
            "total_pipeline_latency_ms": "prediction row latency_ms",
            "attempt_generation_latency_ms": "sum of attempts[].generation_latency_ms",
            "attempt_execution_latency_ms": "sum of attempts[].latency_ms",
            "candidate_execution_latency_ms": (
                "sum of candidate_sqls[].metadata.execution_latency_ms"
            ),
            "candidate_verification_latency_ms": (
                "prediction row candidate_verification_latency_ms or "
                "candidate_verification.latency_ms"
            ),
            "reliability_gate_latency_ms": (
                "prediction row reliability_gate_latency_ms, reliability_gate.latency_ms, "
                "or graph reliability_decision.latency_ms"
            ),
        },
        "anti_tuning_policy": (
            "Aggregate diagnostic only. This summary excludes case IDs, gold SQL, "
            "generated SQL text, and strict or semantic correctness labels."
        ),
    }


def _latency_regression_summary(
    latency_diagnostics: dict[str, Any],
    component_latency_summary: dict[str, Any],
    *,
    p95_regression_threshold_ms: float = 0.0,
    mean_regression_threshold_ms: float = 0.0,
) -> dict[str, Any]:
    overall = (
        latency_diagnostics.get("overall")
        if isinstance(latency_diagnostics, dict)
        else {}
    )
    overall_delta = (
        overall.get("latency_delta_ms") if isinstance(overall, dict) else {}
    ) or {}
    p95_delta = _optional_number(overall_delta.get("p95_ms"))
    mean_delta = _optional_number(overall_delta.get("mean_ms"))
    signals: list[str] = []
    if p95_delta is not None and p95_delta > p95_regression_threshold_ms:
        signals.append("p95_latency_increased")
    if mean_delta is not None and mean_delta > mean_regression_threshold_ms:
        signals.append("mean_latency_increased")

    if p95_delta is None and mean_delta is None:
        status = "latency_data_unavailable"
    elif signals:
        status = "latency_regression_detected"
    else:
        status = "no_latency_regression_detected"

    return {
        "scope": "aggregate_latency_regression_triage_only",
        "status": status,
        "thresholds": {
            "p95_regression_threshold_ms": p95_regression_threshold_ms,
            "mean_regression_threshold_ms": mean_regression_threshold_ms,
        },
        "regression_signals": signals,
        "overall_latency_delta_ms": overall_delta,
        "top_latency_delta_groups": _top_latency_delta_groups(latency_diagnostics),
        "component_delta_contributors": _component_delta_contributors(
            component_latency_summary
        ),
        "unavailable_components": (
            component_latency_summary.get("unavailable_components", {})
            if isinstance(component_latency_summary, dict)
            else {}
        ),
        "anti_tuning_policy": (
            "Aggregate diagnostic only. This summary excludes case IDs, gold SQL, "
            "generated SQL text, and strict or semantic correctness labels."
        ),
    }


def _top_latency_delta_groups(
    latency_diagnostics: dict[str, Any],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    if not isinstance(latency_diagnostics, dict):
        return []
    groups: list[dict[str, Any]] = []
    dimensions = {
        "adaptive_multi_candidate_policy": "by_adaptive_multi_candidate_policy",
        "adaptive_candidate_sql_count": "by_adaptive_candidate_sql_count",
        "adaptive_reliability_gate_action": "by_adaptive_reliability_gate_action",
        "candidate_issue_code": "by_candidate_issue_code",
    }
    for dimension, key in dimensions.items():
        payload = latency_diagnostics.get(key)
        if not isinstance(payload, dict):
            continue
        for group_value, group_summary in payload.items():
            if not isinstance(group_summary, dict):
                continue
            delta_stats = group_summary.get("latency_delta_ms") or {}
            adaptive_stats = group_summary.get("adaptive_latency_ms") or {}
            p95_delta = _optional_number(delta_stats.get("p95_ms"))
            mean_delta = _optional_number(delta_stats.get("mean_ms"))
            if p95_delta is None and mean_delta is None:
                continue
            groups.append(
                {
                    "dimension": dimension,
                    "group": str(group_value),
                    "case_count": int(group_summary.get("case_count") or 0),
                    "p95_delta_ms": p95_delta,
                    "mean_delta_ms": mean_delta,
                    "p95_adaptive_latency_ms": _optional_number(
                        adaptive_stats.get("p95_ms")
                    ),
                }
            )
    return sorted(
        groups,
        key=lambda row: (
            row["p95_delta_ms"] if row["p95_delta_ms"] is not None else float("-inf"),
            row["mean_delta_ms"] if row["mean_delta_ms"] is not None else float("-inf"),
            row["dimension"],
            row["group"],
        ),
        reverse=True,
    )[:limit]


def _component_delta_contributors(
    component_latency_summary: dict[str, Any],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    if not isinstance(component_latency_summary, dict):
        return []
    available = component_latency_summary.get("available_component_stats")
    if not isinstance(available, dict):
        return []
    contributors: list[dict[str, Any]] = []
    for component, stats in available.items():
        if not isinstance(stats, dict):
            continue
        delta_stats = stats.get("delta_ms") or {}
        adaptive_stats = stats.get("adaptive_ms") or {}
        p95_delta = _optional_number(delta_stats.get("p95_ms"))
        mean_delta = _optional_number(delta_stats.get("mean_ms"))
        if p95_delta is None and mean_delta is None:
            continue
        contributors.append(
            {
                "component": str(component),
                "observed_delta_cases": int(stats.get("observed_delta_cases") or 0),
                "p95_delta_ms": p95_delta,
                "mean_delta_ms": mean_delta,
                "p95_adaptive_latency_ms": _optional_number(
                    adaptive_stats.get("p95_ms")
                ),
            }
        )
    return sorted(
        contributors,
        key=lambda row: (
            row["p95_delta_ms"] if row["p95_delta_ms"] is not None else float("-inf"),
            row["mean_delta_ms"] if row["mean_delta_ms"] is not None else float("-inf"),
            row["component"],
        ),
        reverse=True,
    )[:limit]


def _component_values(
    cases: list[dict[str, Any]], side: str, component: str
) -> list[float]:
    values = [
        _optional_number((row.get(side) or {}).get(component))
        for row in cases
        if isinstance(row.get(side), dict)
    ]
    return [value for value in values if value is not None]


def _component_deltas(cases: list[dict[str, Any]], component: str) -> list[float]:
    deltas: list[float] = []
    for row in cases:
        baseline = (
            _optional_number(
                (row.get("baseline_component_latency_ms") or {}).get(component)
            )
            if isinstance(row.get("baseline_component_latency_ms"), dict)
            else None
        )
        adaptive = (
            _optional_number(
                (row.get("adaptive_component_latency_ms") or {}).get(component)
            )
            if isinstance(row.get("adaptive_component_latency_ms"), dict)
            else None
        )
        if baseline is None or adaptive is None:
            continue
        deltas.append(round(adaptive - baseline, 3))
    return deltas


def _aggregate_key(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else "unknown"


def _latency_group_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    adaptive_latencies = [
        value
        for value in (_optional_number(row.get("adaptive_latency_ms")) for row in rows)
        if value is not None
    ]
    deltas = [
        value
        for value in (_optional_number(row.get("latency_delta_ms")) for row in rows)
        if value is not None
    ]
    return {
        "case_count": len(rows),
        "adaptive_latency_ms": _latency_stats(adaptive_latencies),
        "latency_delta_ms": _latency_stats(deltas),
    }


def _latency_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean_ms": None,
            "median_ms": None,
            "p95_ms": None,
            "min_ms": None,
            "max_ms": None,
        }
    ordered = sorted(values)
    p95_index = max(0, ceil(0.95 * len(ordered)) - 1)
    return {
        "count": len(ordered),
        "mean_ms": round(mean(ordered), 3),
        "median_ms": round(median(ordered), 3),
        "p95_ms": round(ordered[p95_index], 3),
        "min_ms": round(ordered[0], 3),
        "max_ms": round(ordered[-1], 3),
    }


def _acceptance_checks(
    baseline: dict[str, Any],
    adaptive: dict[str, Any],
    *,
    baseline_metrics: dict[str, Any],
    adaptive_metrics: dict[str, Any],
    cases: list[dict[str, Any]],
    baseline_dual_policy_dir: str | Path | None,
    adaptive_dual_policy_dir: str | Path | None,
    max_latency_p95_delta_ms: float | None,
    max_latency_mean_delta_ms: float | None,
) -> dict[str, Any]:
    same_selected = _config(baseline).get("selected_cases_hash") == _config(
        adaptive
    ).get("selected_cases_hash")
    unsafe_delta = _number_or_none(
        adaptive_metrics.get("unsafe_sql"), 0
    ) - _number_or_none(baseline_metrics.get("unsafe_sql"), 0)
    valid_sql_delta = _number_or_none(
        adaptive_metrics.get("valid_sql_rate"), 0
    ) - _number_or_none(baseline_metrics.get("valid_sql_rate"), 0)
    semantic_regressions = [
        row["case_id"]
        for row in cases
        if row["semantic_policy_change"] == "regressed_correct_to_not_correct"
    ]
    execution_regressions = [
        row["case_id"]
        for row in cases
        if row["execution_change"] == "regressed_correct_to_wrong"
    ]
    valid_sql_regressions = [
        row["case_id"]
        for row in cases
        if row["valid_sql_change"] == "regressed_correct_to_wrong"
    ]
    latency_p95_delta = _number_or_none(
        adaptive_metrics.get("latency_p95_ms"), 0
    ) - _number_or_none(baseline_metrics.get("latency_p95_ms"), 0)
    latency_mean_delta = _number_or_none(
        adaptive_metrics.get("latency_mean_ms"), 0
    ) - _number_or_none(baseline_metrics.get("latency_mean_ms"), 0)
    latency_budget = _latency_budget_checks(
        p95_delta_ms=latency_p95_delta,
        mean_delta_ms=latency_mean_delta,
        max_p95_delta_ms=max_latency_p95_delta_ms,
        max_mean_delta_ms=max_latency_mean_delta_ms,
    )
    baseline_evidence = _dual_policy_evidence(baseline_dual_policy_dir)
    adaptive_evidence = _dual_policy_evidence(adaptive_dual_policy_dir)
    semantic_evidence_available = bool(
        baseline_evidence["available"] and adaptive_evidence["available"]
    )
    checks = {
        "same_selected_cases_hash": same_selected,
        "unsafe_sql_not_increased": unsafe_delta <= 0,
        "unsafe_sql_delta": unsafe_delta,
        "valid_sql_rate_not_decreased": valid_sql_delta >= 0,
        "valid_sql_rate_delta": valid_sql_delta,
        "valid_sql_regression_case_ids": valid_sql_regressions,
        "semantic_evidence_available": semantic_evidence_available,
        "baseline_dual_policy_evidence": baseline_evidence,
        "adaptive_dual_policy_evidence": adaptive_evidence,
        "semantic_correctness_not_regressed": (
            None if not semantic_evidence_available else not semantic_regressions
        ),
        "semantic_regression_case_ids": semantic_regressions,
        "execution_regression_case_ids": execution_regressions,
        "latency_p95_delta_ms": latency_p95_delta,
        "latency_p95_increased": latency_p95_delta > 0,
        "latency_mean_delta_ms": latency_mean_delta,
        "latency_mean_increased": latency_mean_delta > 0,
        "latency_budget": latency_budget,
    }
    blocker_reasons: list[str] = []
    if not same_selected:
        blocker_reasons.append("selected_cases_hash_mismatch")
    if unsafe_delta > 0:
        blocker_reasons.append("unsafe_sql_increased")
    if valid_sql_delta < 0:
        blocker_reasons.append("valid_sql_rate_decreased")
    if latency_budget["exceeded"]:
        blocker_reasons.append("latency_budget_exceeded")
    if semantic_regressions:
        blocker_reasons.append("semantic_correctness_regressed")

    checks["blocker_reasons"] = blocker_reasons
    runtime_blockers = bool(blocker_reasons)
    if runtime_blockers:
        status = "blocked"
    elif not semantic_evidence_available:
        status = "insufficient_semantic_evidence"
    elif execution_regressions:
        status = "needs_review"
    else:
        status = "eligible_for_review"
    checks["status"] = status
    return checks


def _latency_budget_checks(
    *,
    p95_delta_ms: float,
    mean_delta_ms: float,
    max_p95_delta_ms: float | None,
    max_mean_delta_ms: float | None,
) -> dict[str, Any]:
    p95_within_budget = (
        None if max_p95_delta_ms is None else p95_delta_ms <= max_p95_delta_ms
    )
    mean_within_budget = (
        None if max_mean_delta_ms is None else mean_delta_ms <= max_mean_delta_ms
    )
    exceeded_dimensions: list[str] = []
    if p95_within_budget is False:
        exceeded_dimensions.append("p95")
    if mean_within_budget is False:
        exceeded_dimensions.append("mean")
    return {
        "configured": max_p95_delta_ms is not None or max_mean_delta_ms is not None,
        "max_p95_delta_ms": max_p95_delta_ms,
        "max_mean_delta_ms": max_mean_delta_ms,
        "p95_delta_ms": p95_delta_ms,
        "mean_delta_ms": mean_delta_ms,
        "p95_within_budget": p95_within_budget,
        "mean_within_budget": mean_within_budget,
        "exceeded": bool(exceeded_dimensions),
        "exceeded_dimensions": exceeded_dimensions,
        "scope": "aggregate_benchmark_latency_budget_only",
    }


def _number_or_none(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_optional_number(*values: Any) -> float | None:
    for value in values:
        parsed = _optional_number(value)
        if parsed is not None:
            return parsed
    return None


def _payload_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    return value if isinstance(value, dict) else {}


def _render_report(summary: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase 13 Multi-Candidate A/B Artifact Comparison",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Sources",
        "",
        f"- baseline: `{summary['baseline_artifact_dir']}`",
        f"- adaptive: `{summary['adaptive_artifact_dir']}`",
        f"- same_selected_cases_hash: `{summary['same_selected_cases_hash']}`",
        f"- same_dataset_hash: `{summary['same_dataset_hash']}`",
        f"- same_model: `{summary['same_model']}`",
        "",
        "## Summary",
        "",
        f"- common_cases: `{summary['common_cases']}`",
        f"- baseline_metrics: `{summary['baseline_metrics']}`",
        f"- adaptive_metrics: `{summary['adaptive_metrics']}`",
        f"- metric_deltas: `{summary['metric_deltas']}`",
        f"- execution_change_counts: `{summary['execution_change_counts']}`",
        f"- valid_sql_change_counts: `{summary['valid_sql_change_counts']}`",
        f"- semantic_policy_change_counts: `{summary['semantic_policy_change_counts']}`",
        f"- strict_policy_change_counts: `{summary['strict_policy_change_counts']}`",
        f"- multi_candidate_activation: `{summary['multi_candidate_activation']}`",
        f"- candidate_diversity_summary: `{summary['candidate_diversity_summary']}`",
        f"- candidate_issue_outcome_summary: `{summary['candidate_issue_outcome_summary']}`",
        f"- component_latency_summary: `{summary['component_latency_summary']}`",
        f"- latency_regression_summary: `{summary['latency_regression_summary']}`",
        f"- candidate_issue_counts: `{summary['candidate_issue_counts']}`",
        f"- latency_diagnostics: `{summary['latency_diagnostics']}`",
        f"- acceptance_checks: `{summary['acceptance_checks']}`",
        "",
        "## Aggregate Diagnostic Policy",
        "",
        "Use `candidate_diversity_summary`, `component_latency_summary`, "
        "`latency_regression_summary`, and `latency_diagnostics` for engineering review. "
        "They intentionally omit case IDs, SQL text, gold SQL, and strict or semantic correctness labels.",
        "",
        "## Anti-Fake Statement",
        "",
        summary["anti_fake_policy"],
        "",
        "## Cases",
        "",
        "| Case | EX Change | Valid SQL Change | Semantic Change | Strict Change | Adaptive MC | Candidate Issues | Latency Delta ms |",
        "|---|---|---|---|---|---:|---|---:|",
    ]
    for row in cases:
        lines.append(
            "| {case_id} | {execution_change} | {valid_sql_change} | {semantic_policy_change} | {strict_policy_change} | {adaptive_multi_candidate_enabled} | {adaptive_candidate_consistency_issue_codes} | {latency_delta_ms} |".format(
                **row
            )
        )
    lines.append("")
    return "\n".join(lines)
