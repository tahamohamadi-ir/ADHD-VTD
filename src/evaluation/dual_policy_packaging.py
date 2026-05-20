from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json


def _first_file(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern!r} found in {root}")
    final_matches = [path for path in matches if "_partial_" not in path.name]
    return final_matches[0] if final_matches else matches[0]


def _metric_value(summary: dict[str, Any], metric: str) -> Any:
    return (summary.get("metrics") or {}).get(metric, {}).get("value")


def _safe_count(counts: dict[str, Any], key: str) -> int:
    value = counts.get(key, 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_dual_policy_evidence_package(
    *,
    benchmark_dir: str | Path,
    dual_policy_dir: str | Path,
    output_dir: str | Path,
    evidence_label: str = "small_dev_a4_slice",
) -> dict[str, Path]:
    """Create paper-facing tables from existing benchmark and dual-policy artifacts.

    This function is intentionally read-only with respect to the input artifacts. It does
    not call a model, compare SQL results, create new semantic labels, or reinterpret
    provider errors.
    """

    benchmark_root = Path(benchmark_dir)
    dual_root = Path(dual_policy_dir)
    benchmark_summary_path = _first_file(benchmark_root, "*_summary.json")
    predictions_path = _first_file(benchmark_root, "*_predictions.jsonl")
    dual_summary_path = dual_root / "dual_policy_summary.json"
    dual_cases_path = dual_root / "dual_policy_cases.jsonl"
    if not dual_summary_path.exists() or not dual_cases_path.exists():
        raise FileNotFoundError(
            f"{dual_root} must contain dual_policy_summary.json and dual_policy_cases.jsonl"
        )

    benchmark_summary = read_json(benchmark_summary_path)
    predictions = read_jsonl(predictions_path)
    dual_summary = read_json(dual_summary_path)
    dual_cases = read_jsonl(dual_cases_path)

    predictions_by_id = {str(row.get("id") or row.get("case_id")): row for row in predictions}
    case_rows: list[dict[str, Any]] = []
    for row in dual_cases:
        case_id = str(row.get("case_id"))
        prediction = predictions_by_id.get(case_id, {})
        case_rows.append(
            {
                "case_id": case_id,
                "difficulty": prediction.get("difficulty", "unknown"),
                "category": prediction.get("category", "unknown"),
                "benchmark_error": prediction.get("error") or "",
                "valid_sql": prediction.get("valid_sql"),
                "execution_correct": prediction.get("execution_correct"),
                "semantic_policy_label": row.get("semantic_policy_label"),
                "strict_policy_label": row.get("strict_policy_label"),
                "combined_label": row.get("combined_label"),
            }
        )

    semantic_counts = dual_summary.get("semantic_counts") or {}
    strict_counts = dual_summary.get("strict_counts") or {}
    combined_counts = dual_summary.get("combined_counts") or {}
    dataset = benchmark_summary.get("dataset") or {}
    reliability = benchmark_summary.get("reliability") or {}
    config = benchmark_summary.get("config") or {}
    package_summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "evidence_label": evidence_label,
        "benchmark_dir": str(benchmark_dir),
        "dual_policy_dir": str(dual_policy_dir),
        "benchmark_summary": str(benchmark_summary_path),
        "benchmark_predictions": str(predictions_path),
        "dual_policy_summary": str(dual_summary_path),
        "dual_policy_cases": str(dual_cases_path),
        "dataset": {
            "kind": dataset.get("kind"),
            "total_loaded": dataset.get("total_loaded"),
            "total_evaluated": dataset.get("total_evaluated"),
            "sql_positive": dataset.get("sql_positive"),
            "by_difficulty": dataset.get("by_difficulty"),
            "by_category": dataset.get("by_category"),
            "dataset_hash": config.get("dataset_hash"),
            "selected_cases_hash": config.get("selected_cases_hash"),
        },
        "benchmark_metrics": {
            "execution_accuracy": _metric_value(benchmark_summary, "execution_accuracy"),
            "valid_sql_rate": _metric_value(benchmark_summary, "valid_sql_rate"),
            "sql2nl_paraphrase_robustness": _metric_value(
                benchmark_summary, "sql2nl_paraphrase_robustness"
            ),
            "reliability_score": reliability.get("score"),
            "reliability_normalized": reliability.get("normalized_score"),
        },
        "dual_policy_metrics": {
            "common_cases": dual_summary.get("common_cases"),
            "semantic_correct": _safe_count(semantic_counts, "correct"),
            "semantic_incorrect": _safe_count(semantic_counts, "incorrect"),
            "semantic_adjudication_required": _safe_count(
                semantic_counts, "adjudication_required"
            ),
            "strict_correct": _safe_count(strict_counts, "correct"),
            "strict_incorrect": _safe_count(strict_counts, "incorrect"),
            "strict_adjudication_required": _safe_count(strict_counts, "adjudication_required"),
            "both_correct": _safe_count(combined_counts, "both_correct"),
            "both_incorrect": _safe_count(combined_counts, "both_incorrect"),
            "semantic_correct_strict_incorrect": _safe_count(
                combined_counts, "semantic_correct_strict_incorrect"
            ),
            "combined_adjudication_required": _safe_count(
                combined_counts, "adjudication_required"
            ),
        },
        "anti_fake_policy": (
            "This package reads existing benchmark and dual-policy artifacts only. "
            "It does not call a model, edit predictions, infer missing labels, or turn "
            "provider-error/unjudged rows into correctness claims."
        ),
        "limitations": [
            "This is a small dev/A4 slice unless the source benchmark summary states otherwise.",
            "Semantic user-question correctness and strict reference correctness must be reported separately.",
            "These case labels are evaluation evidence only and must not be used for case-specific prompt, validator, or retrieval tuning.",
        ],
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = write_json(output_root / "paper_evidence_summary.json", package_summary)
    cases_path = _write_case_csv(output_root / "paper_evidence_cases.csv", case_rows)
    report_path = output_root / "paper_evidence_table.md"
    report_path.write_text(_render_markdown(package_summary, case_rows), encoding="utf-8")
    return {"summary": summary_path, "cases_csv": cases_path, "report": report_path}


def _write_case_csv(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "difficulty",
        "category",
        "benchmark_error",
        "valid_sql",
        "execution_correct",
        "semantic_policy_label",
        "strict_policy_label",
        "combined_label",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _render_markdown(summary: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    dataset = summary["dataset"]
    benchmark = summary["benchmark_metrics"]
    dual = summary["dual_policy_metrics"]
    lines = [
        "# Phase 16 Dual-Policy Paper Evidence",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Scope",
        "",
        f"- evidence_label: `{summary['evidence_label']}`",
        f"- benchmark_dir: `{summary['benchmark_dir']}`",
        f"- dual_policy_dir: `{summary['dual_policy_dir']}`",
        f"- total_evaluated: `{dataset.get('total_evaluated')}`",
        f"- selected_cases_hash: `{dataset.get('selected_cases_hash')}`",
        "",
        "## Benchmark Slice",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| execution_accuracy | {benchmark.get('execution_accuracy')} |",
        f"| valid_sql_rate | {benchmark.get('valid_sql_rate')} |",
        f"| sql2nl_paraphrase_robustness | {benchmark.get('sql2nl_paraphrase_robustness')} |",
        f"| reliability_score | {benchmark.get('reliability_score')} |",
        f"| reliability_normalized | {benchmark.get('reliability_normalized')} |",
        "",
        "## Dual-Policy Metrics",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| common_cases | {dual.get('common_cases')} |",
        f"| semantic_correct | {dual.get('semantic_correct')} |",
        f"| semantic_incorrect | {dual.get('semantic_incorrect')} |",
        f"| strict_correct | {dual.get('strict_correct')} |",
        f"| strict_incorrect | {dual.get('strict_incorrect')} |",
        f"| both_correct | {dual.get('both_correct')} |",
        f"| both_incorrect | {dual.get('both_incorrect')} |",
        f"| semantic_correct_strict_incorrect | {dual.get('semantic_correct_strict_incorrect')} |",
        f"| combined_adjudication_required | {dual.get('combined_adjudication_required')} |",
        "",
        "## Case Table",
        "",
        "| Case | Difficulty | Category | EX | Valid SQL | Semantic | Strict | Combined |",
        "|---|---|---|---:|---:|---|---|---|",
    ]
    for row in cases:
        lines.append(
            "| {case_id} | {difficulty} | {category} | {execution_correct} | {valid_sql} | {semantic_policy_label} | {strict_policy_label} | {combined_label} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Anti-Fake Statement",
            "",
            summary["anti_fake_policy"],
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["limitations"])
    lines.append("")
    return "\n".join(lines)
