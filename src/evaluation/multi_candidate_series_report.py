from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import read_json, write_json, write_jsonl


def build_multi_candidate_series_report(
    comparison_dirs: list[str | Path],
    *,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Summarize existing multi-candidate A/B reports as cost-benefit evidence."""

    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    for index, comparison_dir in enumerate(comparison_dirs, start=1):
        summary_path = Path(comparison_dir) / "multi_candidate_ablation_summary.json"
        summary = read_json(summary_path)
        checks = (
            summary.get("acceptance_checks")
            if isinstance(summary.get("acceptance_checks"), dict)
            else {}
        )
        metrics = (
            summary.get("metric_deltas") if isinstance(summary.get("metric_deltas"), dict) else {}
        )
        activation = (
            summary.get("multi_candidate_activation")
            if isinstance(summary.get("multi_candidate_activation"), dict)
            else {}
        )
        status = str(checks.get("status") or "unknown")
        status_counts[status] += 1
        row = {
            "run_index": index,
            "comparison_dir": str(comparison_dir),
            "status": status,
            "same_selected_cases_hash": bool(summary.get("same_selected_cases_hash")),
            "execution_accuracy_delta": metrics.get("execution_accuracy"),
            "valid_sql_rate_delta": metrics.get("valid_sql_rate"),
            "reliability_score_delta": metrics.get("reliability_score"),
            "unsafe_sql_delta": metrics.get("unsafe_sql"),
            "latency_p95_delta_ms": metrics.get("latency_p95_ms"),
            "activation_rate": activation.get("activation_rate"),
            "generated_candidate_count_distribution": activation.get(
                "generated_candidate_count_distribution", {}
            ),
            "candidate_issue_counts": summary.get("candidate_issue_counts", {}),
            "semantic_evidence_available": checks.get("semantic_evidence_available"),
            "recommendation": _recommendation(summary),
        }
        rows.append(row)

    summary_out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "comparison_dirs": [str(path) for path in comparison_dirs],
        "run_count": len(rows),
        "status_counts": dict(status_counts),
        "best_available_recommendation": _best_available_recommendation(rows),
        "anti_fake_policy": (
            "This report summarizes existing multi-candidate A/B comparison artifacts only. "
            "It does not run a model, execute SQL, edit predictions, infer missing semantic labels, "
            "or convert negative/null findings into success claims."
        ),
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = write_json(output_root / "multi_candidate_series_summary.json", summary_out)
    rows_path = write_jsonl(output_root / "multi_candidate_series_cases.jsonl", rows)
    report_path = output_root / "multi_candidate_series_report.md"
    report_path.write_text(_render_report(summary_out, rows), encoding="utf-8")
    return {"summary": summary_path, "cases": rows_path, "report": report_path}


def _recommendation(summary: dict[str, Any]) -> str:
    checks = (
        summary.get("acceptance_checks")
        if isinstance(summary.get("acceptance_checks"), dict)
        else {}
    )
    metrics = summary.get("metric_deltas") if isinstance(summary.get("metric_deltas"), dict) else {}
    status = checks.get("status")
    if status == "blocked":
        return "do_not_adopt"
    if metrics.get("execution_accuracy", 0) <= 0 and metrics.get("latency_p95_ms", 0) > 0:
        return "shadow_or_disable_until_quality_gain"
    if status == "eligible_for_review":
        return "review_before_adoption"
    return "insufficient_evidence"


def _best_available_recommendation(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "no_evidence"
    recommendations = {row.get("recommendation") for row in rows}
    if "do_not_adopt" in recommendations:
        return "do_not_adopt_candidate_adoption"
    if "shadow_or_disable_until_quality_gain" in recommendations:
        return "shadow_only_until_larger_ablation_proves_value"
    if "review_before_adoption" in recommendations:
        return "manual_review_required_before_adoption"
    return "insufficient_evidence"


def _render_report(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase 13 Multi-Candidate Cost-Benefit Series Report",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Summary",
        "",
        f"- run_count: `{summary['run_count']}`",
        f"- status_counts: `{summary['status_counts']}`",
        f"- best_available_recommendation: `{summary['best_available_recommendation']}`",
        "",
        "## Anti-Fake Statement",
        "",
        summary["anti_fake_policy"],
        "",
        "## Runs",
        "",
        "| Run | Status | EX Delta | Valid SQL Delta | p95 Delta ms | Activation | Candidate Issues | Recommendation |",
        "|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {run_index} | {status} | {execution_accuracy_delta} | {valid_sql_rate_delta} | {latency_p95_delta_ms} | {activation_rate} | {candidate_issue_counts} | {recommendation} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Paper Interpretation",
            "",
            (
                "The current evidence supports reporting multi-candidate generation as an explored but not yet "
                "cost-effective reliability intervention on this smoke slice. Candidate adoption is blocked or "
                "unsupported because it did not improve execution accuracy, did not provide a reliable latency/value "
                "tradeoff, and in the dual-policy evidence can regress semantic-user-question correctness. Shadow-only "
                "candidate evidence is safer than adoption, but remains diagnostic/review infrastructure until a larger "
                "dev-set ablation proves semantic gain without valid-SQL, strict-reference, safety, or latency regressions."
            ),
            "",
        ]
    )
    return "\n".join(lines)
