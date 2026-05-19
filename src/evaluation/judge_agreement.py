from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl


def _judgment_paths(root: str | Path) -> tuple[Path, Path]:
    path = Path(root)
    return path / "judge_summary.json", path / "judgments.jsonl"


def _semantic_label(value: Any) -> str:
    if value is True:
        return "correct"
    if value is False:
        return "incorrect"
    return "unjudged"


def _requires_adjudication(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_semantic = left.get("semantic_business_correct")
    right_semantic = right.get("semantic_business_correct")
    left_verdict = str(left.get("verdict") or "")
    right_verdict = str(right.get("verdict") or "")
    review_verdicts = {
        "partial_business_match",
        "requires_semantic_review",
        "provider_error",
        "provider_parse_error",
        "provider_not_configured",
    }
    return (
        left_semantic is None
        or right_semantic is None
        or left_semantic != right_semantic
        or left_verdict in review_verdicts
        or right_verdict in review_verdicts
    )


def analyze_judge_agreement(
    left_dir: str | Path,
    right_dir: str | Path,
    *,
    output_dir: str | Path,
) -> dict[str, Path]:
    left_summary_path, left_judgments_path = _judgment_paths(left_dir)
    right_summary_path, right_judgments_path = _judgment_paths(right_dir)
    left_summary = read_json(left_summary_path)
    right_summary = read_json(right_summary_path)
    left_rows = read_jsonl(left_judgments_path)
    right_rows = read_jsonl(right_judgments_path)

    left_by_id = {str(row.get("case_id")): row for row in left_rows}
    right_by_id = {str(row.get("case_id")): row for row in right_rows}
    common_ids = sorted(set(left_by_id) & set(right_by_id))

    cases: list[dict[str, Any]] = []
    final_counts: Counter[str] = Counter()
    semantic_pair_counts: Counter[str] = Counter()
    verdict_pair_counts: Counter[str] = Counter()
    for case_id in common_ids:
        left = left_by_id[case_id]
        right = right_by_id[case_id]
        left_semantic = _semantic_label(left.get("semantic_business_correct"))
        right_semantic = _semantic_label(right.get("semantic_business_correct"))
        semantic_agrees = left_semantic == right_semantic
        verdict_agrees = left.get("verdict") == right.get("verdict")
        adjudication_required = _requires_adjudication(left, right)
        if adjudication_required:
            final_label = "adjudication_required"
        elif left.get("semantic_business_correct") is True and right.get("semantic_business_correct") is True:
            final_label = "agreed_correct"
        elif left.get("semantic_business_correct") is False and right.get("semantic_business_correct") is False:
            final_label = "agreed_incorrect"
        else:
            final_label = "adjudication_required"

        final_counts[final_label] += 1
        semantic_pair_counts[f"{left_semantic}|{right_semantic}"] += 1
        verdict_pair_counts[f"{left.get('verdict')}|{right.get('verdict')}"] += 1
        cases.append(
            {
                "case_id": case_id,
                "left_provider": left_summary.get("provider"),
                "left_model": left_summary.get("model"),
                "right_provider": right_summary.get("provider"),
                "right_model": right_summary.get("model"),
                "left_verdict": left.get("verdict"),
                "right_verdict": right.get("verdict"),
                "left_raw_provider_verdict": left.get("raw_provider_verdict"),
                "right_raw_provider_verdict": right.get("raw_provider_verdict"),
                "left_semantic": left_semantic,
                "right_semantic": right_semantic,
                "semantic_agrees": semantic_agrees,
                "verdict_agrees": verdict_agrees,
                "adjudication_required": adjudication_required,
                "final_label": final_label,
                "left_reason": left.get("reason"),
                "right_reason": right.get("reason"),
            }
        )

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "left_dir": str(left_dir),
        "right_dir": str(right_dir),
        "left_provider": left_summary.get("provider"),
        "left_model": left_summary.get("model"),
        "right_provider": right_summary.get("provider"),
        "right_model": right_summary.get("model"),
        "left_source_artifact": left_summary.get("source_artifact"),
        "right_source_artifact": right_summary.get("source_artifact"),
        "same_source_artifact": left_summary.get("source_artifact") == right_summary.get("source_artifact"),
        "left_total_judged": left_summary.get("total_judged"),
        "right_total_judged": right_summary.get("total_judged"),
        "common_cases": len(common_ids),
        "left_only_cases": sorted(set(left_by_id) - set(right_by_id)),
        "right_only_cases": sorted(set(right_by_id) - set(left_by_id)),
        "semantic_agreement_count": sum(1 for row in cases if row["semantic_agrees"]),
        "semantic_disagreement_count": sum(1 for row in cases if not row["semantic_agrees"]),
        "verdict_agreement_count": sum(1 for row in cases if row["verdict_agrees"]),
        "verdict_disagreement_count": sum(1 for row in cases if not row["verdict_agrees"]),
        "final_counts": dict(final_counts),
        "semantic_pair_counts": dict(semantic_pair_counts),
        "verdict_pair_counts": dict(verdict_pair_counts),
        "anti_fake_policy": (
            "This report compares existing judgment artifacts only. It does not call a model, "
            "change judgment rows, or turn partial/unjudged cases into correctness claims."
        ),
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    cases_path = write_jsonl(output_root / "judge_agreement_cases.jsonl", cases)
    summary_path = write_json(output_root / "judge_agreement.json", summary)
    report_path = output_root / "judge_agreement.md"
    report_path.write_text(_render_agreement_report(summary, cases), encoding="utf-8")
    return {"summary": summary_path, "cases": cases_path, "report": report_path}


def _render_agreement_report(summary: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase 16 Judge Agreement Report",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Sources",
        "",
        f"- left: `{summary['left_dir']}`",
        f"- right: `{summary['right_dir']}`",
        f"- same_source_artifact: `{summary['same_source_artifact']}`",
        "",
        "## Summary",
        "",
        f"- common_cases: `{summary['common_cases']}`",
        f"- semantic_agreement_count: `{summary['semantic_agreement_count']}`",
        f"- semantic_disagreement_count: `{summary['semantic_disagreement_count']}`",
        f"- verdict_agreement_count: `{summary['verdict_agreement_count']}`",
        f"- verdict_disagreement_count: `{summary['verdict_disagreement_count']}`",
        f"- final_counts: `{summary['final_counts']}`",
        "",
        "## Anti-Fake Statement",
        "",
        summary["anti_fake_policy"],
        "",
        "## Cases",
        "",
        "| Case | Left Verdict | Right Verdict | Left Semantic | Right Semantic | Final Label |",
        "|---|---|---|---|---|---|",
    ]
    for row in cases:
        lines.append(
            "| {case_id} | {left_verdict} | {right_verdict} | {left_semantic} | {right_semantic} | {final_label} |".format(
                **row
            )
        )
    lines.append("")
    return "\n".join(lines)
