from __future__ import annotations

from collections import Counter, defaultdict
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


def _is_partial_business_match(row: dict[str, Any]) -> bool:
    return str(row.get("verdict") or "") == "partial_business_match"


def _load_judgment_dir(root: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary_path, judgments_path = _judgment_paths(root)
    return read_json(summary_path), read_jsonl(judgments_path)


def build_judge_consensus(
    judgment_dirs: list[str | Path],
    *,
    output_dir: str | Path,
    min_agree: int = 2,
) -> dict[str, Path]:
    if len(judgment_dirs) < 2:
        raise ValueError("At least two judgment directories are required for consensus analysis.")
    if min_agree < 2:
        raise ValueError("min_agree must be at least 2 to avoid single-judge correctness claims.")

    loaded = [_load_judgment_dir(root) for root in judgment_dirs]
    summaries = [summary for summary, _rows in loaded]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, (summary, rows) in enumerate(loaded):
        for row in rows:
            case_id = str(row.get("case_id") or "")
            if not case_id:
                continue
            grouped[case_id].append(
                {
                    "judge_dir": str(judgment_dirs[index]),
                    "provider": summary.get("provider"),
                    "model": summary.get("model"),
                    "authoritative": bool(row.get("authoritative")),
                    "verdict": row.get("verdict"),
                    "semantic": _semantic_label(row.get("semantic_business_correct")),
                    "semantic_business_correct": row.get("semantic_business_correct"),
                    "needs_human_review": row.get("needs_human_review"),
                    "reason": row.get("reason"),
                }
            )

    cases: list[dict[str, Any]] = []
    final_counts: Counter[str] = Counter()
    for case_id in sorted(grouped):
        judgments = grouped[case_id]
        authoritative_semantics = [
            row["semantic"]
            for row in judgments
            if row["authoritative"] and row["semantic"] in {"correct", "incorrect"}
        ]
        authoritative_partial_count = sum(
            1 for row in judgments if row["authoritative"] and _is_partial_business_match(row)
        )
        counts = Counter(authoritative_semantics)
        if counts["correct"] >= min_agree and counts["incorrect"] == 0:
            final_label = "consensus_correct"
        elif counts["incorrect"] >= min_agree and counts["correct"] == 0:
            final_label = "consensus_incorrect"
        elif not counts and authoritative_partial_count >= min_agree:
            final_label = "consensus_partial_business_match"
        else:
            final_label = "adjudication_required"
        final_counts[final_label] += 1
        cases.append(
            {
                "case_id": case_id,
                "final_label": final_label,
                "semantic_counts": dict(counts),
                "authoritative_partial_count": authoritative_partial_count,
                "judgment_count": len(judgments),
                "authoritative_semantic_count": len(authoritative_semantics),
                "judgments": judgments,
            }
        )

    source_artifacts = [summary.get("source_artifact") for summary in summaries]
    prompt_versions = [summary.get("prompt_version") for summary in summaries]
    judge_policies = [summary.get("judge_policy") for summary in summaries]
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "judgment_dirs": [str(root) for root in judgment_dirs],
        "providers": [summary.get("provider") for summary in summaries],
        "models": [summary.get("model") for summary in summaries],
        "prompt_versions": prompt_versions,
        "same_prompt_version": len(set(prompt_versions)) == 1,
        "judge_policies": judge_policies,
        "same_judge_policy": len(set(judge_policies)) == 1,
        "source_artifacts": source_artifacts,
        "same_source_artifact": len(set(source_artifacts)) == 1,
        "min_agree": min_agree,
        "case_count": len(cases),
        "final_counts": dict(final_counts),
        "metric_policy_counts": {
            "semantic_correct": final_counts.get("consensus_correct", 0),
            "semantic_incorrect": final_counts.get("consensus_incorrect", 0),
            "partial_business_match": final_counts.get("consensus_partial_business_match", 0),
            "needs_human_review": final_counts.get("adjudication_required", 0),
        },
        "anti_fake_policy": (
            "Consensus labels require at least min_agree authoritative non-null semantic labels and no opposing "
            "authoritative semantic label. Partial business matches are reported separately only when at least "
            "min_agree authoritative partial votes exist and there are no non-null semantic votes. Single-judge, "
            "provider-error, and unjudged rows do not become correctness claims. Prompt versions are recorded so "
            "old and revised semantic rubrics are not silently mixed in paper claims. Judge policies are recorded "
            "so semantic-user-question and strict-reference judgments are reported as separate metrics."
        ),
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    cases_path = write_jsonl(output_root / "judge_consensus_cases.jsonl", cases)
    summary_path = write_json(output_root / "judge_consensus.json", summary)
    report_path = output_root / "judge_consensus.md"
    report_path.write_text(_render_consensus_report(summary, cases), encoding="utf-8")
    return {"summary": summary_path, "cases": cases_path, "report": report_path}


def _render_consensus_report(summary: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase 16 Judge Consensus Report",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Sources",
        "",
        f"- same_source_artifact: `{summary['same_source_artifact']}`",
        f"- same_prompt_version: `{summary['same_prompt_version']}`",
        f"- same_judge_policy: `{summary['same_judge_policy']}`",
        f"- min_agree: `{summary['min_agree']}`",
    ]
    for root, model in zip(summary["judgment_dirs"], summary["models"], strict=False):
        lines.append(f"- `{model}`: `{root}`")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- case_count: `{summary['case_count']}`",
            f"- final_counts: `{summary['final_counts']}`",
            f"- metric_policy_counts: `{summary['metric_policy_counts']}`",
            "",
            "## Anti-Fake Statement",
            "",
            summary["anti_fake_policy"],
            "",
            "## Cases",
            "",
            "| Case | Final Label | Correct Votes | Incorrect Votes | Partial Votes | Authoritative Semantic Votes |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in cases:
        counts = row.get("semantic_counts", {})
        lines.append(
            "| {case_id} | {final_label} | {correct} | {incorrect} | {partial} | {votes} |".format(
                case_id=row["case_id"],
                final_label=row["final_label"],
                correct=counts.get("correct", 0),
                incorrect=counts.get("incorrect", 0),
                partial=row.get("authoritative_partial_count", 0),
                votes=row["authoritative_semantic_count"],
            )
        )
    lines.append("")
    return "\n".join(lines)
