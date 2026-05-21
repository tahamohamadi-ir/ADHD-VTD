from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl


def _first_file(root: Path, pattern: str) -> Path:
    matches = sorted(path for path in root.glob(pattern) if "_partial_" not in path.name)
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

    baseline_by_id = {str(row.get("id") or row.get("case_id")): row for row in baseline["predictions"]}
    adaptive_by_id = {str(row.get("id") or row.get("case_id")): row for row in adaptive["predictions"]}
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
        consistency_dict = candidate_consistency if isinstance(candidate_consistency, dict) else {}
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
                "adaptive_multi_candidate_enabled": bool(policy_dict.get("enabled")),
                "adaptive_multi_candidate_candidate_count": policy_dict.get("candidate_count"),
                "adaptive_multi_candidate_triggers": list(policy_dict.get("triggers") or []),
                "adaptive_candidate_sql_count": len(adaptive_row.get("candidate_sqls") or []),
                "adaptive_selected_candidate_id": adaptive_row.get("selected_candidate_id"),
                "adaptive_candidate_consistency_passed": consistency_dict.get("passed"),
                "adaptive_candidate_consistency_issue_codes": issue_codes,
                "baseline_reliability_gate_action": baseline_row.get("reliability_gate_action"),
                "adaptive_reliability_gate_action": adaptive_row.get("reliability_gate_action"),
                "baseline_semantic_policy_label": baseline_policy_label.get("semantic_policy_label"),
                "adaptive_semantic_policy_label": adaptive_policy_label.get("semantic_policy_label"),
                "semantic_policy_change": semantic_change,
                "baseline_strict_policy_label": baseline_policy_label.get("strict_policy_label"),
                "adaptive_strict_policy_label": adaptive_policy_label.get("strict_policy_label"),
                "strict_policy_change": strict_change,
            }
        )

    baseline_metrics = _benchmark_metrics(baseline["summary"])
    adaptive_metrics = _benchmark_metrics(adaptive["summary"])
    metric_deltas = _metric_deltas(baseline_metrics, adaptive_metrics)
    activation = _multi_candidate_activation(adaptive["predictions"])
    acceptance = _acceptance_checks(
        baseline,
        adaptive,
        baseline_metrics=baseline_metrics,
        adaptive_metrics=adaptive_metrics,
        cases=cases,
        baseline_dual_policy_dir=baseline_dual_policy_dir,
        adaptive_dual_policy_dir=adaptive_dual_policy_dir,
    )

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "baseline_artifact_dir": str(baseline_artifact_dir),
        "adaptive_artifact_dir": str(adaptive_artifact_dir),
        "baseline_summary_path": str(baseline["summary_path"]),
        "adaptive_summary_path": str(adaptive["summary_path"]),
        "baseline_predictions_path": str(baseline["predictions_path"]),
        "adaptive_predictions_path": str(adaptive["predictions_path"]),
        "baseline_dual_policy_dir": str(baseline_dual_policy_dir) if baseline_dual_policy_dir else None,
        "adaptive_dual_policy_dir": str(adaptive_dual_policy_dir) if adaptive_dual_policy_dir else None,
        "same_dataset_hash": _config(baseline).get("dataset_hash") == _config(adaptive).get("dataset_hash"),
        "same_selected_cases_hash": _config(baseline).get("selected_cases_hash")
        == _config(adaptive).get("selected_cases_hash"),
        "baseline_selected_cases_hash": _config(baseline).get("selected_cases_hash"),
        "adaptive_selected_cases_hash": _config(adaptive).get("selected_cases_hash"),
        "same_model": _config(baseline).get("model_name") == _config(adaptive).get("model_name"),
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
        "candidate_issue_counts": dict(candidate_issue_counts),
        "acceptance_checks": acceptance,
        "anti_fake_policy": (
            "This report compares existing benchmark and optional dual-policy judgment artifacts only. "
            "It does not run a model, execute SQL, edit predictions, infer missing semantic labels, or "
            "use case IDs/gold SQL as tuning rules."
        ),
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    cases_path = write_jsonl(output_root / "multi_candidate_ablation_cases.jsonl", cases)
    summary_path = write_json(output_root / "multi_candidate_ablation_summary.json", summary)
    report_path = output_root / "multi_candidate_ablation_report.md"
    report_path.write_text(_render_report(summary, cases), encoding="utf-8")
    return {"summary": summary_path, "cases": cases_path, "report": report_path}


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
        raise FileNotFoundError(f"{path} does not contain dual_policy_cases.jsonl")
    return {str(row.get("case_id")): row for row in read_jsonl(cases_path)}


def _config(artifact: dict[str, Any]) -> dict[str, Any]:
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    config = summary.get("config")
    return config if isinstance(config, dict) else {}


def _benchmark_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    metrics = summary.get("metrics") if isinstance(summary.get("metrics"), dict) else {}
    reliability = summary.get("reliability") if isinstance(summary.get("reliability"), dict) else {}
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


def _metric_deltas(baseline: dict[str, Any], adaptive: dict[str, Any]) -> dict[str, Any]:
    deltas: dict[str, Any] = {}
    for key, baseline_value in baseline.items():
        adaptive_value = adaptive.get(key)
        if isinstance(baseline_value, (int, float)) and isinstance(adaptive_value, (int, float)):
            deltas[key] = round(float(adaptive_value) - float(baseline_value), 6)
    return deltas


def _execution_correct(row: dict[str, Any]) -> bool:
    return bool(row.get("execution_correct") or row.get("result_match") or row.get("ok"))


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
        generated_candidate_count_distribution[str(len(record.get("candidate_sqls") or []))] += 1
        for trigger in policy_dict.get("triggers") or []:
            trigger_counts[str(trigger)] += 1
    total = len(predictions)
    return {
        "policy_counts": dict(policy_counts),
        "trigger_counts": dict(trigger_counts),
        "policy_candidate_count_distribution": dict(candidate_count_distribution),
        "generated_candidate_count_distribution": dict(generated_candidate_count_distribution),
        "activation_rate": round(policy_counts.get("enabled", 0) / total, 6) if total else 0.0,
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
) -> dict[str, Any]:
    same_selected = _config(baseline).get("selected_cases_hash") == _config(adaptive).get("selected_cases_hash")
    unsafe_delta = _number_or_none(adaptive_metrics.get("unsafe_sql"), 0) - _number_or_none(
        baseline_metrics.get("unsafe_sql"), 0
    )
    valid_sql_delta = _number_or_none(adaptive_metrics.get("valid_sql_rate"), 0) - _number_or_none(
        baseline_metrics.get("valid_sql_rate"), 0
    )
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
    latency_p95_delta = _number_or_none(adaptive_metrics.get("latency_p95_ms"), 0) - _number_or_none(
        baseline_metrics.get("latency_p95_ms"), 0
    )
    semantic_evidence_available = bool(baseline_dual_policy_dir and adaptive_dual_policy_dir)
    checks = {
        "same_selected_cases_hash": same_selected,
        "unsafe_sql_not_increased": unsafe_delta <= 0,
        "unsafe_sql_delta": unsafe_delta,
        "valid_sql_rate_not_decreased": valid_sql_delta >= 0,
        "valid_sql_rate_delta": valid_sql_delta,
        "valid_sql_regression_case_ids": valid_sql_regressions,
        "semantic_evidence_available": semantic_evidence_available,
        "semantic_correctness_not_regressed": None if not semantic_evidence_available else not semantic_regressions,
        "semantic_regression_case_ids": semantic_regressions,
        "execution_regression_case_ids": execution_regressions,
        "latency_p95_delta_ms": latency_p95_delta,
        "latency_p95_increased": latency_p95_delta > 0,
    }
    runtime_blockers = (not same_selected) or unsafe_delta > 0 or valid_sql_delta < 0
    if runtime_blockers:
        status = "blocked"
    elif not semantic_evidence_available:
        status = "insufficient_semantic_evidence"
    elif semantic_regressions:
        status = "blocked"
    elif execution_regressions:
        status = "needs_review"
    else:
        status = "eligible_for_review"
    checks["status"] = status
    return checks


def _number_or_none(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
        f"- candidate_issue_counts: `{summary['candidate_issue_counts']}`",
        f"- acceptance_checks: `{summary['acceptance_checks']}`",
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
