from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl


def _load_policy_report(
    root: str | Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    path = Path(root)
    consensus_summary = path / "judge_consensus.json"
    consensus_cases = path / "judge_consensus_cases.jsonl"
    if consensus_summary.exists() and consensus_cases.exists():
        return read_json(consensus_summary), read_jsonl(consensus_cases), "consensus"

    agreement_summary = path / "judge_agreement.json"
    agreement_cases = path / "judge_agreement_cases.jsonl"
    if agreement_summary.exists() and agreement_cases.exists():
        return read_json(agreement_summary), read_jsonl(agreement_cases), "agreement"

    raise FileNotFoundError(
        f"{path} does not contain judge_consensus.* or judge_agreement.* artifacts."
    )


def _policy_label(final_label: str | None) -> str:
    label = str(final_label or "")
    if label in {"agreed_correct", "consensus_correct"}:
        return "correct"
    if label in {"agreed_incorrect", "consensus_incorrect"}:
        return "incorrect"
    if label == "consensus_partial_business_match":
        return "partial_business_match"
    return "adjudication_required"


def _combined_label(semantic_label: str, strict_label: str) -> str:
    if semantic_label == "correct" and strict_label == "correct":
        return "both_correct"
    if semantic_label == "incorrect" and strict_label == "incorrect":
        return "both_incorrect"
    if semantic_label == "correct" and strict_label == "incorrect":
        return "semantic_correct_strict_incorrect"
    if semantic_label == "incorrect" and strict_label == "correct":
        return "semantic_incorrect_strict_correct"
    if semantic_label == "partial_business_match" or strict_label == "partial_business_match":
        return "partial_or_mixed"
    return "adjudication_required"


def _source_authoritative(summary: dict[str, Any], artifact_kind: str) -> bool:
    if summary.get("authoritative") is True:
        return True
    return artifact_kind == "consensus"


def _complete_policy_labels(
    semantic_counts: Counter[str],
    strict_counts: Counter[str],
    combined_counts: Counter[str],
) -> bool:
    blocking_labels = {
        "adjudication_required",
        "partial_business_match",
        "partial_or_mixed",
        "unjudged",
    }
    for counts in (semantic_counts, strict_counts, combined_counts):
        if any(counts.get(label, 0) > 0 for label in blocking_labels):
            return False
    return True


def build_dual_policy_report(
    semantic_dir: str | Path,
    strict_dir: str | Path,
    *,
    output_dir: str | Path,
) -> dict[str, Path]:
    semantic_summary, semantic_cases, semantic_kind = _load_policy_report(semantic_dir)
    strict_summary, strict_cases, strict_kind = _load_policy_report(strict_dir)

    semantic_by_id = {str(row.get("case_id")): row for row in semantic_cases}
    strict_by_id = {str(row.get("case_id")): row for row in strict_cases}
    common_ids = sorted(set(semantic_by_id) & set(strict_by_id))

    cases: list[dict[str, Any]] = []
    combined_counts: Counter[str] = Counter()
    semantic_counts: Counter[str] = Counter()
    strict_counts: Counter[str] = Counter()
    for case_id in common_ids:
        semantic_case = semantic_by_id[case_id]
        strict_case = strict_by_id[case_id]
        semantic_label = _policy_label(semantic_case.get("final_label"))
        strict_label = _policy_label(strict_case.get("final_label"))
        combined = _combined_label(semantic_label, strict_label)
        semantic_counts[semantic_label] += 1
        strict_counts[strict_label] += 1
        combined_counts[combined] += 1
        cases.append(
            {
                "case_id": case_id,
                "semantic_final_label": semantic_case.get("final_label"),
                "strict_final_label": strict_case.get("final_label"),
                "semantic_policy_label": semantic_label,
                "strict_policy_label": strict_label,
                "combined_label": combined,
                "semantic_correct": semantic_label == "correct",
                "strict_correct": strict_label == "correct",
            }
        )

    source_artifacts = [
        semantic_summary.get("left_source_artifact")
        or semantic_summary.get("source_artifacts", [None])[0],
        strict_summary.get("left_source_artifact")
        or strict_summary.get("source_artifacts", [None])[0],
    ]
    semantic_authoritative = _source_authoritative(semantic_summary, semantic_kind)
    strict_authoritative = _source_authoritative(strict_summary, strict_kind)
    complete_policy_labels = _complete_policy_labels(
        semantic_counts,
        strict_counts,
        combined_counts,
    )
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "semantic_dir": str(semantic_dir),
        "strict_dir": str(strict_dir),
        "semantic_artifact_kind": semantic_kind,
        "strict_artifact_kind": strict_kind,
        "semantic_prompt_versions": _summary_prompt_versions(semantic_summary),
        "strict_prompt_versions": _summary_prompt_versions(strict_summary),
        "semantic_judge_policies": _summary_judge_policies(semantic_summary),
        "strict_judge_policies": _summary_judge_policies(strict_summary),
        "source_artifacts": source_artifacts,
        "same_source_artifact": len(set(source for source in source_artifacts if source)) == 1,
        "common_cases": len(common_ids),
        "authoritative": semantic_authoritative and strict_authoritative,
        "semantic_source_authoritative": semantic_authoritative,
        "strict_source_authoritative": strict_authoritative,
        "complete_policy_labels": complete_policy_labels,
        "semantic_only_cases": sorted(set(semantic_by_id) - set(strict_by_id)),
        "strict_only_cases": sorted(set(strict_by_id) - set(semantic_by_id)),
        "semantic_counts": dict(semantic_counts),
        "strict_counts": dict(strict_counts),
        "combined_counts": dict(combined_counts),
        "anti_fake_policy": (
            "This report merges existing semantic-policy and strict-policy judgment reports only. "
            "It does not call a model, edit judgments, or convert unjudged/provider-error rows into correctness claims."
        ),
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    cases_path = write_jsonl(output_root / "dual_policy_cases.jsonl", cases)
    summary_path = write_json(output_root / "dual_policy_summary.json", summary)
    report_path = output_root / "dual_policy_report.md"
    report_path.write_text(_render_report(summary, cases), encoding="utf-8")
    return {"summary": summary_path, "cases": cases_path, "report": report_path}


def _summary_prompt_versions(summary: dict[str, Any]) -> list[Any]:
    if "prompt_versions" in summary:
        return list(summary.get("prompt_versions") or [])
    return [summary.get("left_prompt_version"), summary.get("right_prompt_version")]


def _summary_judge_policies(summary: dict[str, Any]) -> list[Any]:
    if "judge_policies" in summary:
        return list(summary.get("judge_policies") or [])
    return [summary.get("left_judge_policy"), summary.get("right_judge_policy")]


def _render_report(summary: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase 16 Dual-Policy Judge Report",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Sources",
        "",
        f"- semantic_dir: `{summary['semantic_dir']}`",
        f"- strict_dir: `{summary['strict_dir']}`",
        f"- same_source_artifact: `{summary['same_source_artifact']}`",
        f"- authoritative: `{summary['authoritative']}`",
        f"- complete_policy_labels: `{summary['complete_policy_labels']}`",
        "",
        "## Summary",
        "",
        f"- common_cases: `{summary['common_cases']}`",
        f"- semantic_counts: `{summary['semantic_counts']}`",
        f"- strict_counts: `{summary['strict_counts']}`",
        f"- combined_counts: `{summary['combined_counts']}`",
        "",
        "## Anti-Fake Statement",
        "",
        summary["anti_fake_policy"],
        "",
        "## Cases",
        "",
        "| Case | Semantic Label | Strict Label | Combined Label |",
        "|---|---|---|---|",
    ]
    for row in cases:
        lines.append(
            "| {case_id} | {semantic_policy_label} | {strict_policy_label} | {combined_label} |".format(
                **row
            )
        )
    lines.append("")
    return "\n".join(lines)
