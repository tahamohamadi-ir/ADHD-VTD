from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl

ADJUDICATED_LABEL_TO_FINAL = {
    "semantic_correct": "consensus_correct",
    "semantic_incorrect": "consensus_incorrect",
    "partial_business_match": "consensus_partial_business_match",
}
FINAL_LABEL_TO_METRIC_POLICY = {
    "consensus_correct": "semantic_correct",
    "consensus_incorrect": "semantic_incorrect",
    "consensus_partial_business_match": "partial_business_match",
    "adjudication_required": "needs_human_review",
}
ADJUDICATION_CSV_COLUMNS = (
    "case_id",
    "adjudicated_label",
    "adjudicator",
    "adjudicator_type",
    "reason",
)
DEFAULT_ADJUDICATOR = "human_review"
DEFAULT_ADJUDICATOR_TYPE = "human"


def parse_adjudication_csv(path: str | Path) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    seen: set[str] = set()
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            case_id = str(row.get("case_id") or "").strip()
            if not case_id:
                raise ValueError(f"Adjudication CSV row is missing case_id: {path}")
            label = str(row.get("adjudicated_label") or "").strip().lower()
            if label not in ADJUDICATED_LABEL_TO_FINAL:
                raise ValueError(
                    f"Invalid adjudicated_label {label!r} for case {case_id}; "
                    f"expected one of {sorted(ADJUDICATED_LABEL_TO_FINAL)}"
                )
            if case_id in seen:
                raise ValueError(f"Duplicate case_id in adjudication CSV: {case_id}")
            seen.add(case_id)
            decisions.append(
                {
                    "case_id": case_id,
                    "adjudicated_label": label,
                    "final_label": ADJUDICATED_LABEL_TO_FINAL[label],
                    "adjudicator": str(row.get("adjudicator") or "").strip() or DEFAULT_ADJUDICATOR,
                    "adjudicator_type": str(row.get("adjudicator_type") or "").strip()
                    or DEFAULT_ADJUDICATOR_TYPE,
                    "reason": str(row.get("reason") or "").strip(),
                    "source": f"csv:{path}",
                }
            )
    return decisions


def parse_third_judge_decisions(
    judgment_dir: str | Path,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    root = Path(judgment_dir)
    summary = read_json(root / "judge_summary.json")
    rows = read_jsonl(root / "judgments.jsonl")
    default_model = str(summary.get("model") or "")
    decisions: list[dict[str, Any]] = []
    skipped: Counter[str] = Counter()
    seen: set[str] = set()
    for row in rows:
        case_id = str(row.get("case_id") or "").strip()
        if not case_id:
            skipped["missing_case_id"] += 1
            continue
        if case_id in seen:
            skipped["duplicate_case_id"] += 1
            continue
        if not bool(row.get("authoritative")):
            skipped["non_authoritative"] += 1
            continue
        semantic = row.get("semantic_business_correct")
        if semantic is True:
            label = "semantic_correct"
        elif semantic is False:
            label = "semantic_incorrect"
        elif str(row.get("verdict") or "") == "partial_business_match":
            skipped["partial_business_match"] += 1
            continue
        elif bool(row.get("needs_human_review")):
            skipped["needs_human_review"] += 1
            continue
        else:
            skipped["unjudged_or_provider_error"] += 1
            continue
        seen.add(case_id)
        decisions.append(
            {
                "case_id": case_id,
                "adjudicated_label": label,
                "final_label": ADJUDICATED_LABEL_TO_FINAL[label],
                "adjudicator": str(row.get("model") or "") or default_model,
                "adjudicator_type": "third_judge",
                "reason": str(row.get("reason") or ""),
                "source": f"judgments:{root}",
            }
        )
    return decisions, dict(sorted(skipped.items()))


def apply_adjudications(
    cases: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_case = {str(case.get("case_id") or ""): case for case in cases}
    decided: dict[str, dict[str, Any]] = {}
    for decision in decisions:
        case_id = str(decision.get("case_id") or "")
        if case_id not in by_case:
            raise ValueError(f"Unknown case_id in adjudication decisions: {case_id}")
        if case_id in decided:
            raise ValueError(f"Duplicate adjudication decision for case_id: {case_id}")
        case = dict(by_case[case_id])
        case["prior_final_label"] = case.get("final_label")
        case["final_label"] = decision["final_label"]
        case["adjudication"] = {
            "adjudicated_label": str(decision.get("adjudicated_label") or ""),
            "adjudicator": str(decision.get("adjudicator") or "") or DEFAULT_ADJUDICATOR,
            "adjudicator_type": str(decision.get("adjudicator_type") or "")
            or DEFAULT_ADJUDICATOR_TYPE,
            "reason": str(decision.get("reason") or ""),
            "source": str(decision.get("source") or ""),
        }
        decided[case_id] = case
    return [decided.get(str(case.get("case_id") or ""), case) for case in cases]


def adjudicate_consensus(
    consensus_dir: str | Path,
    *,
    output_dir: str | Path,
    decisions_csv: str | Path | None = None,
    third_judge_dirs: list[str | Path] | tuple[str | Path, ...] = (),
    fail_on_unresolved: bool = False,
) -> dict[str, Path]:
    root = Path(consensus_dir)
    summary_path = root / "judge_consensus.json"
    cases_path = root / "judge_consensus_cases.jsonl"
    if not summary_path.exists() or not cases_path.exists():
        raise FileNotFoundError(
            f"Consensus artifacts not found in {root}: "
            "expected judge_consensus.json and judge_consensus_cases.jsonl"
        )
    summary = read_json(summary_path)
    cases = read_jsonl(cases_path)

    decisions: list[dict[str, Any]] = []
    skipped: Counter[str] = Counter()
    if decisions_csv is not None:
        decisions.extend(parse_adjudication_csv(decisions_csv))
    for judge_dir in third_judge_dirs:
        third_decisions, third_skipped = parse_third_judge_decisions(judge_dir)
        decisions.extend(third_decisions)
        skipped.update(third_skipped)

    updated_cases = apply_adjudications(cases, decisions)
    final_counts: Counter[str] = Counter(
        str(case.get("final_label") or "") for case in updated_cases
    )
    metric_policy_counts = {
        policy: final_counts.get(final_label, 0)
        for final_label, policy in FINAL_LABEL_TO_METRIC_POLICY.items()
    }
    remaining = final_counts.get("adjudication_required", 0)
    if fail_on_unresolved and remaining:
        raise RuntimeError(
            f"{remaining} case(s) still require adjudication after applying {len(decisions)} decision(s)."
        )

    updated_summary = {
        **summary,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "final_counts": {key: final_counts[key] for key in sorted(final_counts)},
        "metric_policy_counts": metric_policy_counts,
        "adjudication": {
            "consensus_source": str(root),
            "decisions_csv": str(decisions_csv) if decisions_csv is not None else None,
            "third_judge_dirs": [str(judge_dir) for judge_dir in third_judge_dirs],
            "decision_count": len(decisions),
            "skipped_counts": dict(sorted(skipped.items())),
            "remaining_adjudication_required": remaining,
            "fail_on_unresolved": bool(fail_on_unresolved),
        },
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    return {
        "summary": write_json(output_root / "judge_consensus_adjudicated.json", updated_summary),
        "cases": write_jsonl(
            output_root / "judge_consensus_adjudicated_cases.jsonl", updated_cases
        ),
        "report": _write_report(
            output_root / "judge_consensus_adjudicated.md",
            updated_summary,
            updated_cases,
        ),
    }


def _write_report(
    path: Path,
    summary: dict[str, Any],
    cases: list[dict[str, Any]],
) -> Path:
    adjudication = summary.get("adjudication") or {}
    lines = [
        "# Judge Consensus Adjudication Report",
        "",
        f"Generated at: {summary.get('generated_at')}",
        "",
        "## Sources",
        "",
        f"- consensus_source: `{adjudication.get('consensus_source')}`",
        f"- decisions_csv: `{adjudication.get('decisions_csv')}`",
        "- third_judge_dirs: "
        + ", ".join(f"`{item}`" for item in adjudication.get("third_judge_dirs") or [])
        or "- third_judge_dirs: (none)",
        "",
        "## Summary",
        "",
        f"- decisions_applied: `{adjudication.get('decision_count')}`",
        f"- skipped_counts: `{adjudication.get('skipped_counts')}`",
        f"- remaining_adjudication_required: `{adjudication.get('remaining_adjudication_required')}`",
        f"- final_counts: `{summary.get('final_counts')}`",
        f"- metric_policy_counts: `{summary.get('metric_policy_counts')}`",
        "",
        "## Adjudicated Cases",
        "",
        "| Case | Prior Label | Final Label | Adjudicator | Type | Reason |",
        "|---|---|---|---|---|---|",
    ]
    adjudicated = [case for case in cases if case.get("adjudication")]
    for case in adjudicated:
        detail = case["adjudication"]
        lines.append(
            "| {case_id} | {prior} | {final} | {adjudicator} | {kind} | {reason} |".format(
                case_id=case.get("case_id"),
                prior=case.get("prior_final_label"),
                final=case.get("final_label"),
                adjudicator=detail.get("adjudicator"),
                kind=detail.get("adjudicator_type"),
                reason=str(detail.get("reason") or "").replace("|", "/"),
            )
        )
    if not adjudicated:
        lines.append("| (none) |  |  |  |  |  |")
    lines.extend(
        [
            "",
            "## Anti-Fake Statement",
            "",
            "Adjudication decisions are recorded verbatim with their source. Labels are only overridden "
            "for case IDs present in the consensus artifact; counts are recomputed from the resulting "
            "labels. Remaining adjudication-required cases are never silently promoted to correctness claims.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
