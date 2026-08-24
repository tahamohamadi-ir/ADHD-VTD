from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import read_jsonl, write_json, write_jsonl
from src.evaluation.reliability_gate import evaluate_reliability_gate


def _first_file(root: Path, pattern: str) -> Path:
    matches = sorted(path for path in root.glob(pattern) if "_partial_" not in path.name)
    if not matches:
        matches = sorted(root.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern!r} found in {root}")
    return matches[0]


def analyze_reliability_gate_artifact(
    artifact_dir: str | Path,
    *,
    output_dir: str | Path,
    recompute_gate: bool = False,
) -> dict[str, Path]:
    artifact_root = Path(artifact_dir)
    predictions_path = _first_file(artifact_root, "*_predictions.jsonl")
    predictions = read_jsonl(predictions_path)

    rows: list[dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    multi_candidate_counts: Counter[str] = Counter()
    multi_candidate_trigger_counts: Counter[str] = Counter()
    for record in predictions:
        gate = _gate_view(record, recompute_gate=recompute_gate)
        action = gate["action"]
        reason = gate["reason"]
        warnings = gate["warnings"]
        multi_candidate_policy = (
            record.get("multi_candidate_policy")
            if isinstance(record.get("multi_candidate_policy"), dict)
            else {}
        )
        multi_candidate_enabled = bool(multi_candidate_policy.get("enabled"))
        multi_candidate_counts["enabled" if multi_candidate_enabled else "disabled"] += 1
        for trigger in multi_candidate_policy.get("triggers") or []:
            multi_candidate_trigger_counts[str(trigger)] += 1
        execution_correct = bool(
            record.get("execution_correct") or record.get("result_match") or record.get("ok")
        )
        valid_sql = bool(record.get("valid_sql"))
        error = record.get("error") or ""
        action_counts[action] += 1
        reason_counts[reason] += 1
        for warning in warnings:
            warning_counts[warning] += 1
        risk_label = _risk_label(
            action, execution_correct=execution_correct, valid_sql=valid_sql, error=error
        )
        risk_counts[risk_label] += 1
        rows.append(
            {
                "case_id": record.get("id") or record.get("case_id"),
                "actual_action": record.get("actual_action"),
                "benchmark_error": error,
                "valid_sql": valid_sql,
                "execution_correct": execution_correct,
                "reliability_gate_action": action,
                "reliability_gate_reason": reason,
                "reliability_gate_warnings": warnings,
                "reliability_gate_source": gate["source"],
                "recomputed_gate_signals": gate.get("signals", {}),
                "multi_candidate_enabled": multi_candidate_enabled,
                "multi_candidate_candidate_count": multi_candidate_policy.get("candidate_count"),
                "multi_candidate_triggers": list(multi_candidate_policy.get("triggers") or []),
                "posthoc_gate_risk": risk_label,
            }
        )

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "artifact_dir": str(artifact_dir),
        "predictions_path": str(predictions_path),
        "analysis_mode": "recomputed_runtime_gate" if recompute_gate else "stored_gate_annotations",
        "total_predictions": len(predictions),
        "with_gate_annotations": sum(
            1 for row in rows if row["reliability_gate_action"] != "missing"
        ),
        "action_counts": dict(action_counts),
        "reason_counts": dict(reason_counts),
        "warning_counts": dict(warning_counts),
        "multi_candidate_counts": dict(multi_candidate_counts),
        "multi_candidate_trigger_counts": dict(multi_candidate_trigger_counts),
        "posthoc_risk_counts": dict(risk_counts),
        "anti_fake_policy": (
            "This report reads existing prediction artifacts only. Recomputed gate decisions, when enabled, are analysis labels; "
            "they do not alter benchmark outcomes, runtime routing, generated SQL, or semantic correctness."
        ),
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = write_json(output_root / "reliability_gate_summary.json", summary)
    cases_path = write_jsonl(output_root / "reliability_gate_cases.jsonl", rows)
    report_path = output_root / "reliability_gate_report.md"
    report_path.write_text(_render_report(summary, rows), encoding="utf-8")
    return {"summary": summary_path, "cases": cases_path, "report": report_path}


def _risk_label(action: str, *, execution_correct: bool, valid_sql: bool, error: str) -> str:
    if action == "missing":
        return "gate_missing"
    if action == "answer" and execution_correct:
        return "answer_on_correct"
    if action == "answer" and valid_sql and error == "RESULT_MISMATCH":
        return "answer_on_valid_result_mismatch"
    if action == "answer" and not execution_correct:
        return "answer_on_incorrect"
    if action in {"needs_review", "ask_clarification"} and execution_correct:
        return "review_or_clarify_on_correct"
    if action in {"needs_review", "ask_clarification"} and not execution_correct:
        return "review_or_clarify_on_incorrect"
    if action == "retry":
        return "retry_requested"
    if action == "refuse_unsafe":
        return "unsafe_refusal"
    return "other"


def _render_report(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase 13 Reliability Gate Artifact Analysis",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Source",
        "",
        f"- artifact_dir: `{summary['artifact_dir']}`",
        f"- predictions: `{summary['predictions_path']}`",
        f"- analysis_mode: `{summary['analysis_mode']}`",
        "",
        "## Summary",
        "",
        f"- total_predictions: `{summary['total_predictions']}`",
        f"- with_gate_annotations: `{summary['with_gate_annotations']}`",
        f"- action_counts: `{summary['action_counts']}`",
        f"- reason_counts: `{summary['reason_counts']}`",
        f"- warning_counts: `{summary['warning_counts']}`",
        f"- multi_candidate_counts: `{summary['multi_candidate_counts']}`",
        f"- multi_candidate_trigger_counts: `{summary['multi_candidate_trigger_counts']}`",
        f"- posthoc_risk_counts: `{summary['posthoc_risk_counts']}`",
        "",
        "## Anti-Fake Statement",
        "",
        summary["anti_fake_policy"],
        "",
        "## Cases",
        "",
        "| Case | Action | Reason | Warnings | MC Enabled | MC Triggers | EX | Valid SQL | Benchmark Error | Post-hoc Risk |",
        "|---|---|---|---|---:|---|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {case_id} | {reliability_gate_action} | {reliability_gate_reason} | {reliability_gate_warnings} | {multi_candidate_enabled} | {multi_candidate_triggers} | {execution_correct} | {valid_sql} | {benchmark_error} | {posthoc_gate_risk} |".format(
                **row
            )
        )
    lines.append("")
    return "\n".join(lines)


def _listish(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _gate_view(record: dict[str, Any], *, recompute_gate: bool) -> dict[str, Any]:
    if not recompute_gate:
        return {
            "action": str(record.get("reliability_gate_action") or "missing"),
            "reason": str(record.get("reliability_gate_reason") or "missing"),
            "warnings": [
                str(warning) for warning in _listish(record.get("reliability_gate_warnings"))
            ],
            "source": "stored",
        }

    decision = evaluate_reliability_gate(_record_for_recompute(record))
    return {
        "action": decision.action,
        "reason": decision.reason,
        "warnings": list(decision.warnings),
        "signals": decision.signals,
        "source": "recomputed",
    }


def _record_for_recompute(record: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(record)
    if "execution_result" not in enriched and enriched.get("result_hash"):
        enriched["execution_ok"] = True
    return enriched
