from __future__ import annotations

import csv
import random
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl
from src.evaluation.human_agreement import cohens_kappa

REVIEWER_LABELS = ("correct", "incorrect", "partial_business_match")
SPOT_CHECK_CSV_COLUMNS = (
    "case_id",
    "question",
    "judge_verdict",
    "judge_semantic_business_correct",
    "judge_reason_truncated",
    "reviewer_semantic_business_label",
    "reviewer_notes",
)
REASON_TRUNCATION = 500
MIN_CLASS_SIZE = 10
DEFAULT_SAMPLE_SIZE = 40
DEFAULT_SEED = 187


def judge_semantic_label(value: Any) -> str:
    if value is True:
        return "correct"
    if value is False:
        return "incorrect"
    return "unjudged"


def select_spot_check(judgments: list[dict[str, Any]], n: int, seed: int) -> list[dict[str, Any]]:
    if n <= 0 or not judgments:
        return []
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in judgments:
        groups.setdefault(judge_semantic_label(row.get("semantic_business_correct")), []).append(
            row
        )
    for group in groups.values():
        group.sort(key=lambda row: str(row.get("case_id") or ""))
    available = {name: len(group) for name, group in groups.items()}
    target = min(n, len(judgments))
    quotas = _stratified_quotas(available, target)
    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    for name in sorted(groups):
        take = quotas[name]
        if take > 0:
            selected.extend(rng.sample(groups[name], take))
    selected.sort(key=lambda row: str(row.get("case_id") or ""))
    return selected


def _stratified_quotas(available: dict[str, int], target: int) -> dict[str, int]:
    quotas = {name: 0 for name in available}
    remaining = target
    for name in sorted(available, key=lambda item: (available[item], item)):
        take = min(MIN_CLASS_SIZE, available[name], remaining)
        quotas[name] = take
        remaining -= take
    capacity = {name: available[name] - quotas[name] for name in available}
    for name, extra in _proportional_allocation(capacity, remaining).items():
        quotas[name] += extra
    return quotas


def _proportional_allocation(capacity: dict[str, int], slots: int) -> dict[str, int]:
    allocation = {name: 0 for name in capacity}
    total_capacity = sum(capacity.values())
    if slots <= 0 or total_capacity <= 0:
        return allocation
    if slots >= total_capacity:
        return dict(capacity)
    floors = {name: slots * cap // total_capacity for name, cap in capacity.items()}
    remainder = slots - sum(floors.values())
    order = sorted(
        capacity,
        key=lambda name: (-(slots * capacity[name] % total_capacity), name),
    )
    for name in order[:remainder]:
        floors[name] += 1
    return floors


def build_spot_check_package(
    judgment_dir: str | Path,
    *,
    n: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
    output_dir: str | Path,
    predictions_file: Path | None = None,
) -> dict[str, Path]:
    root = Path(judgment_dir)
    summary = read_json(root / "judge_summary.json")
    if summary.get("authoritative") is not True:
        raise ValueError(
            f"Judge artifact is not authoritative; refusing spot-check package: {root}"
        )
    judgments = read_jsonl(root / "judgments.jsonl")
    selected = select_spot_check(judgments, n, seed)
    rows = [_package_row(judgment) for judgment in selected]
    questions_enriched = 0
    if predictions_file is not None:
        questions_enriched = _enrich_rows_with_questions(rows, Path(predictions_file))
    population_strata = Counter(
        judge_semantic_label(row.get("semantic_business_correct")) for row in judgments
    )
    sampled_strata = Counter(
        judge_semantic_label(row.get("semantic_business_correct")) for row in selected
    )
    package_summary = {
        "schema_version": "pars_sql_judge_spot_check_package_v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(root),
        "source_authoritative": True,
        "sampled": len(selected),
        "requested_sample_size": n,
        "seed": seed,
        "population_total": len(judgments),
        "strata_counts": {key: population_strata[key] for key in sorted(population_strata)},
        "sampled_strata_counts": {key: sampled_strata[key] for key in sorted(sampled_strata)},
        "redacted": True,
        "paper_metric_allowed": False,
        "reviewer_label_choices": list(REVIEWER_LABELS),
        "anti_fake_policy": (
            "This package samples existing authoritative judge rows for human spot review only. "
            "It redacts SQL and gold fields, never infers reviewer labels, and is not a paper metric "
            "until labels are imported by an authorized reviewer."
        ),
    }
    if predictions_file is not None:
        package_summary["questions_enriched"] = questions_enriched
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = _write_csv(output_root / "judge_spot_check_package.csv", rows)
    instructions_path = output_root / "REVIEW_INSTRUCTIONS.md"
    instructions_path.write_text(_render_instructions(package_summary), encoding="utf-8")
    summary_path = write_json(output_root / "package_summary.json", package_summary)
    return {"csv": csv_path, "instructions": instructions_path, "summary": summary_path}


def import_spot_check_labels(
    review_csv: str | Path,
    source_package_summary_path: str | Path,
    *,
    output_dir: str | Path,
    authoritative: bool = False,
) -> dict[str, Path]:
    package_summary_path = Path(source_package_summary_path)
    package_summary = read_json(package_summary_path)
    if package_summary.get("source_authoritative") is not True:
        raise ValueError(
            f"Spot-check package was not sourced from an authoritative artifact: {package_summary_path}"
        )
    rows = _read_csv(Path(review_csv))
    invalid: list[dict[str, Any]] = []
    cleaned: list[tuple[dict[str, Any], str]] = []
    for row in rows:
        case_id = str(row.get("case_id") or "")
        reviewer = str(row.get("reviewer_semantic_business_label") or "").strip().lower()
        if reviewer not in REVIEWER_LABELS:
            invalid.append({"case_id": case_id, "label": reviewer})
            continue
        cleaned.append((row, reviewer))

    comparisons: list[dict[str, Any]] = []
    judge_labels: list[str] = []
    reviewer_labels: list[str] = []
    agreeing = 0
    disagreeing = 0
    excluded_unjudged = 0
    if not invalid:
        for row, reviewer in cleaned:
            case_id = str(row.get("case_id") or "")
            judge = _parse_judge_cell(row.get("judge_semantic_business_correct"))
            comparable = judge in {"correct", "incorrect"}
            agree = comparable and reviewer == judge
            if comparable:
                if agree:
                    agreeing += 1
                else:
                    disagreeing += 1
                judge_labels.append(judge)
                reviewer_labels.append(reviewer)
            else:
                excluded_unjudged += 1
            comparisons.append(
                {
                    "case_id": case_id,
                    "judge_label": judge,
                    "reviewer_label": reviewer,
                    "agree": agree,
                    "comparable": comparable,
                }
            )

    status = "invalid_labels" if invalid else "complete"
    is_authoritative = bool(authoritative and status == "complete")
    denominator = len(judge_labels)
    agreement_rate = round(agreeing / denominator, 4) if denominator else None
    kappa = cohens_kappa(judge_labels, reviewer_labels) if denominator else None
    reason = (
        None
        if status == "complete"
        else (
            "Reviewer labels must be non-blank values from "
            f"{list(REVIEWER_LABELS)}; blank or invalid labels block an authoritative import."
        )
    )
    summary_out = {
        "schema_version": "pars_sql_judge_spot_check_import_v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "review_csv": str(review_csv),
        "source_package_summary": str(package_summary_path),
        "status": status,
        "labeled": len(rows),
        "invalid_rows": invalid,
        "agreement_rate": agreement_rate,
        "cohens_kappa": kappa,
        "agreeing": agreeing,
        "disagreeing": disagreeing,
        "agreement_denominator": denominator,
        "excluded_unjudged_judge_rows": excluded_unjudged,
        "authoritative": is_authoritative,
        "paper_metric_allowed": is_authoritative,
        "reason": reason,
        "anti_fake_policy": (
            "This importer reads reviewer-provided labels only. It does not call a model, infer missing "
            "labels, edit judgments, or promote spot-check agreement into paper metrics without an "
            "explicit authorized authoritative import."
        ),
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {
        "summary": write_json(output_root / "judge_spot_check_summary.json", summary_out)
    }
    if status == "complete":
        paths["cases"] = write_jsonl(output_root / "judge_spot_check_cases.jsonl", comparisons)
    paths["report"] = _write_import_report(
        output_root / "judge_spot_check_report.md", summary_out, comparisons
    )
    return paths


def _enrich_rows_with_questions(rows: list[dict[str, Any]], predictions_file: Path) -> int:
    questions = _load_prediction_questions(predictions_file)
    enriched = 0
    for row in rows:
        question = questions.get(row["case_id"], "")
        if not question:
            continue
        row["question"] = question
        enriched += 1
    return enriched


def _load_prediction_questions(predictions_file: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for record in read_jsonl(predictions_file):
        case_id = str(record.get("case_id") or "")
        if not case_id:
            continue
        question = str(record.get("question") or record.get("question_fa") or "")
        if question:
            mapping[case_id] = question
    return mapping


def _package_row(judgment: dict[str, Any]) -> dict[str, Any]:
    semantic = judgment.get("semantic_business_correct")
    reason = str(judgment.get("reason") or "")
    return {
        "case_id": str(judgment.get("case_id") or ""),
        "question": str(judgment.get("question") or judgment.get("question_fa") or ""),
        "judge_verdict": str(judgment.get("verdict") or ""),
        "judge_semantic_business_correct": "" if semantic is None else str(bool(semantic)),
        "judge_reason_truncated": reason[:REASON_TRUNCATION],
        "reviewer_semantic_business_label": "",
        "reviewer_notes": "",
    }


def _parse_judge_cell(value: Any) -> str:
    cell = str(value or "").strip().lower()
    if cell in {"true", "correct"}:
        return "correct"
    if cell in {"false", "incorrect"}:
        return "incorrect"
    return "unjudged"


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SPOT_CHECK_CSV_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _render_instructions(summary: dict[str, Any]) -> str:
    labels = ", ".join(f"`{label}`" for label in summary["reviewer_label_choices"])
    return "\n".join(
        [
            "# Spot-Check Review Instructions",
            "",
            "Fill only the reviewer columns in `judge_spot_check_package.csv`.",
            "",
            "Required label:",
            "",
            f"- `reviewer_semantic_business_label`: one of {labels}",
            "- `reviewer_notes`: brief rationale, optional",
            "",
            "Rules:",
            "",
            "- Judge columns (`judge_*`) are read-only context; do not edit them.",
            "- Judge the SQL answer against the user question only; this is the semantic/business policy.",
            "- Use `partial_business_match` only when part of the requested business answer is correct.",
            "- Every sampled row needs a non-blank label before the import can be authoritative.",
            "- This package is redacted and is not a paper metric until reviewed and signed off.",
            "",
        ]
    )


def _write_import_report(
    path: Path,
    summary: dict[str, Any],
    comparisons: list[dict[str, Any]],
) -> Path:
    lines = [
        "# Judge Spot-Check Import Report",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Summary",
        "",
        f"- status: `{summary['status']}`",
        f"- authoritative: `{summary['authoritative']}`",
        f"- paper_metric_allowed: `{summary['paper_metric_allowed']}`",
        f"- labeled: `{summary['labeled']}`",
        f"- agreement_rate: `{summary['agreement_rate']}`",
        f"- cohens_kappa: `{summary['cohens_kappa']}`",
        f"- agreeing: `{summary['agreeing']}`",
        f"- disagreeing: `{summary['disagreeing']}`",
        f"- excluded_unjudged_judge_rows: `{summary['excluded_unjudged_judge_rows']}`",
        f"- invalid_rows: `{summary['invalid_rows']}`",
    ]
    if summary.get("reason"):
        lines.extend(["", f"Reason: {summary['reason']}"])
    if comparisons:
        lines.extend(
            [
                "",
                "## Comparisons",
                "",
                "| Case | Judge Label | Reviewer Label | Agree |",
                "|---|---|---|---|",
            ]
        )
        for row in comparisons:
            lines.append("| {case_id} | {judge_label} | {reviewer_label} | {agree} |".format(**row))
    lines.extend(["", "## Anti-Fake Statement", "", summary["anti_fake_policy"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
