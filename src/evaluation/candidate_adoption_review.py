from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl

REVIEW_LABELS = ("correct", "incorrect", "needs_review")
PENDING_LABEL = ""
REVIEW_FORBIDDEN_LEAKAGE_FIELDS = {
    "gold_sql",
    "expected_sql",
    "gold_result_hash",
    "gold_result_preview",
    "expected_result_hash",
    "expected_result_preview",
    "execution_correct",
    "result_match",
    "ok",
    "error",
    "benchmark_error",
    "strict_policy_label",
    "semantic_policy_label",
    "combined_label",
    "semantic_business_correct",
    "judge_label",
}


@dataclass(frozen=True, slots=True)
class CandidateReviewPackageIssue:
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


@dataclass(frozen=True, slots=True)
class CandidateReviewPackageValidationReport:
    ok: bool
    issues: list[CandidateReviewPackageIssue] = field(default_factory=list)
    checked: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [issue.as_dict() for issue in self.issues],
            "checked": self.checked,
        }


def build_candidate_adoption_review_package(
    *,
    adaptive_artifact_dir: str | Path,
    output_dir: str | Path,
    reviewer_label: str = "human_review_pending",
) -> dict[str, Path]:
    """Write a post-run human review packet for adopted non-primary candidates.

    The packet is intentionally non-authoritative. It does not call a model,
    execute SQL, infer semantic labels, or edit benchmark predictions.
    """

    artifact = _load_benchmark_artifact(adaptive_artifact_dir)
    config = artifact["summary"].get("config") or {}
    predictions = artifact["predictions"]
    adopted = [
        record
        for record in predictions
        if record.get("selected_candidate_id")
        and str(record.get("selected_candidate_id")) != "candidate_1"
    ]

    rows = [_review_row(record) for record in adopted]
    summary = {
        "schema_version": "pars_sql_candidate_adoption_review_v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_artifact": str(adaptive_artifact_dir),
        "summary_path": str(artifact["summary_path"]),
        "predictions_path": str(artifact["predictions_path"]),
        "reviewer_label": reviewer_label,
        "authoritative": False,
        "paper_metric_allowed": False,
        "post_run_no_tuning": True,
        "review_label_choices": REVIEW_LABELS,
        "dataset_hash": config.get("dataset_hash"),
        "selected_cases_hash": config.get("selected_cases_hash"),
        "model_name": config.get("model_name"),
        "total_predictions": len(predictions),
        "adopted_non_primary_cases": len(rows),
        "valid_sql_cases": sum(1 for row in rows if row["valid_sql"] is True),
        "unsafe_sql_cases": sum(1 for row in rows if row["unsafe_sql"] is True),
        "single_viable_candidate_cases": sum(
            1 for row in rows if "SINGLE_VIABLE_CANDIDATE" in row["verifier_issue_codes"]
        ),
        "gold_reference_fields_redacted": True,
        "strict_reference_fields_included": False,
        "anti_fake_policy": (
            "This package prepares existing benchmark predictions for external review only. "
            "It does not create semantic correctness labels, run a model, execute SQL, edit "
            "predictions, expose gold SQL or strict correctness labels, or make paper-metric claims."
        ),
        "limitations": [
            "Reviewer label columns are intentionally blank until a real human or configured judge fills them.",
            "Gold SQL, benchmark execution-correct labels, and result-mismatch labels are redacted from this package.",
            "Strict reference review requires separately controlled reference material at the final review stage.",
            "Semantic user-question correctness and strict reference correctness must be reported separately.",
            "Rows must not be used for case-specific prompt, validator, or retrieval tuning.",
        ],
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = write_json(output_root / "candidate_adoption_review_summary.json", summary)
    rows_path = write_jsonl(output_root / "candidate_adoption_review_cases.jsonl", rows)
    csv_path = _write_review_csv(output_root / "candidate_adoption_review_cases.csv", rows)
    report_path = output_root / "candidate_adoption_review_report.md"
    report_path.write_text(_render_report(summary, rows), encoding="utf-8")
    instructions_path = output_root / "REVIEW_INSTRUCTIONS.md"
    instructions_path.write_text(_render_instructions(summary), encoding="utf-8")
    return {
        "summary": summary_path,
        "cases_jsonl": rows_path,
        "cases_csv": csv_path,
        "report": report_path,
        "instructions": instructions_path,
    }


def import_candidate_adoption_review_labels(
    *,
    review_csv: str | Path,
    output_dir: str | Path,
    reviewer_label: str = "human_review_pending",
    authoritative: bool = False,
) -> dict[str, Path]:
    """Convert completed candidate-adoption review CSV labels to dual-policy artifacts.

    Blank labels keep the import in pending state. Invalid labels are reported as
    invalid and no dual-policy artifact is written.
    """

    rows = _read_review_csv(Path(review_csv))
    invalid = _invalid_label_rows(rows)
    pending = _pending_label_rows(rows)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    status = "invalid_labels" if invalid else "pending_review" if pending else "complete"
    summary = {
        "schema_version": "pars_sql_candidate_adoption_review_import_v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "review_csv": str(review_csv),
        "reviewer_label": reviewer_label,
        "authoritative": bool(authoritative and status == "complete"),
        "paper_metric_allowed": False,
        "status": status,
        "total_rows": len(rows),
        "pending_rows": pending,
        "invalid_rows": invalid,
        "anti_fake_policy": (
            "This importer reads reviewer-provided labels only. It does not call a model, "
            "infer missing labels, edit benchmark predictions, execute SQL, or promote "
            "review labels to final paper metrics."
        ),
    }
    paths: dict[str, Path] = {
        "summary": write_json(
            output_root / "candidate_adoption_review_import_summary.json", summary
        )
    }

    if status != "complete":
        report_path = output_root / "candidate_adoption_review_import_report.md"
        report_path.write_text(_render_import_report(summary, []), encoding="utf-8")
        paths["report"] = report_path
        return paths

    dual_cases = [_dual_policy_case(row) for row in rows]
    semantic_counts = Counter(row["semantic_policy_label"] for row in dual_cases)
    strict_counts = Counter(row["strict_policy_label"] for row in dual_cases)
    combined_counts = Counter(row["combined_label"] for row in dual_cases)
    dual_summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_review_csv": str(review_csv),
        "reviewer_label": reviewer_label,
        "authoritative": bool(authoritative),
        "paper_metric_allowed": False,
        "common_cases": len(dual_cases),
        "semantic_counts": dict(semantic_counts),
        "strict_counts": dict(strict_counts),
        "combined_counts": dict(combined_counts),
        "anti_fake_policy": (
            "This dual-policy artifact is derived only from completed reviewer labels. "
            "It does not call a model, infer labels, edit predictions, or create final "
            "paper metrics."
        ),
    }
    dual_cases_path = write_jsonl(output_root / "dual_policy_cases.jsonl", dual_cases)
    dual_summary_path = write_json(output_root / "dual_policy_summary.json", dual_summary)
    report_path = output_root / "dual_policy_report.md"
    report_path.write_text(_render_import_report(dual_summary, dual_cases), encoding="utf-8")
    paths.update(
        {
            "dual_policy_summary": dual_summary_path,
            "dual_policy_cases": dual_cases_path,
            "report": report_path,
        }
    )
    return paths


def validate_candidate_adoption_review_package(
    review_dir: str | Path,
) -> CandidateReviewPackageValidationReport:
    """Validate a non-authoritative candidate adoption review package.

    This verifier is offline. It checks package structure and no-gold-leakage
    guards, but it does not run a model, execute SQL, infer review labels, or
    promote paper metrics.
    """

    root = Path(review_dir)
    paths = {
        "summary": root / "candidate_adoption_review_summary.json",
        "cases_jsonl": root / "candidate_adoption_review_cases.jsonl",
        "cases_csv": root / "candidate_adoption_review_cases.csv",
        "report": root / "candidate_adoption_review_report.md",
        "instructions": root / "REVIEW_INSTRUCTIONS.md",
    }
    checked: dict[str, Any] = {
        "review_dir": str(root),
        "required_files": {key: str(path) for key, path in paths.items()},
    }
    issues: list[CandidateReviewPackageIssue] = []

    missing = [key for key, path in paths.items() if not path.exists()]
    checked["missing_files"] = missing
    for key in missing:
        issues.append(
            CandidateReviewPackageIssue(
                code="CANDIDATE_REVIEW_FILE_MISSING",
                message=f"Required candidate review package file is missing: {key}",
                path=str(paths[key]),
            )
        )
    if issues:
        return CandidateReviewPackageValidationReport(False, issues, checked)

    summary = read_json(paths["summary"])
    cases = read_jsonl(paths["cases_jsonl"])
    csv_rows = _read_review_csv(paths["cases_csv"])
    checked["total_rows"] = len(cases)
    checked["csv_rows"] = len(csv_rows)
    checked["authoritative"] = summary.get("authoritative")
    checked["paper_metric_allowed"] = summary.get("paper_metric_allowed")
    checked["gold_reference_fields_redacted"] = summary.get("gold_reference_fields_redacted")
    checked["strict_reference_fields_included"] = summary.get("strict_reference_fields_included")

    if summary.get("authoritative") is not False:
        issues.append(
            CandidateReviewPackageIssue(
                code="CANDIDATE_REVIEW_MARKED_AUTHORITATIVE",
                message="Candidate adoption review packages must remain non-authoritative.",
                path=str(paths["summary"]),
            )
        )
    if summary.get("paper_metric_allowed") is not False:
        issues.append(
            CandidateReviewPackageIssue(
                code="CANDIDATE_REVIEW_PAPER_METRIC_ALLOWED",
                message="Candidate adoption review packages cannot allow paper metrics.",
                path=str(paths["summary"]),
            )
        )
    if summary.get("gold_reference_fields_redacted") is not True:
        issues.append(
            CandidateReviewPackageIssue(
                code="CANDIDATE_REVIEW_REDACTION_FLAG_MISSING",
                message="Review package must state that gold/reference fields were redacted.",
                path=str(paths["summary"]),
            )
        )
    if summary.get("strict_reference_fields_included") is not False:
        issues.append(
            CandidateReviewPackageIssue(
                code="CANDIDATE_REVIEW_STRICT_REFERENCE_INCLUDED",
                message="Review package must not include strict reference fields.",
                path=str(paths["summary"]),
            )
        )
    if len(cases) != len(csv_rows):
        issues.append(
            CandidateReviewPackageIssue(
                code="CANDIDATE_REVIEW_ROW_COUNT_MISMATCH",
                message="JSONL and CSV review row counts do not match.",
                path=str(root),
            )
        )

    _append_leakage_issues(issues, cases, paths["cases_jsonl"])
    _append_leakage_issues(issues, csv_rows, paths["cases_csv"])

    return CandidateReviewPackageValidationReport(not issues, issues, checked)


def _load_benchmark_artifact(root: str | Path) -> dict[str, Any]:
    artifact_root = Path(root)
    summary_path = _first_file(artifact_root, "*_summary.json")
    predictions_path = _first_file(artifact_root, "*_predictions.jsonl")
    return {
        "summary_path": summary_path,
        "predictions_path": predictions_path,
        "summary": read_json(summary_path),
        "predictions": read_jsonl(predictions_path),
    }


def _first_file(root: Path, pattern: str) -> Path:
    matches = sorted(path for path in root.glob(pattern) if "_partial_" not in path.name)
    if not matches:
        matches = sorted(root.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern!r} found in {root}")
    return matches[0]


def _read_review_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _append_leakage_issues(
    issues: list[CandidateReviewPackageIssue],
    rows: list[dict[str, Any]],
    path: Path,
) -> None:
    leaked_fields: set[str] = set()
    for row in rows:
        leaked_fields.update(set(row) & REVIEW_FORBIDDEN_LEAKAGE_FIELDS)
    if leaked_fields:
        issues.append(
            CandidateReviewPackageIssue(
                code="CANDIDATE_REVIEW_GOLD_LEAKAGE_FIELD",
                message=(
                    "Candidate review package contains forbidden gold/label fields: "
                    + ", ".join(sorted(leaked_fields))
                ),
                path=str(path),
            )
        )


def _invalid_label_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    invalid: list[dict[str, Any]] = []
    for row in rows:
        semantic = _clean_review_label(row.get("reviewer_semantic_user_question_label"))
        strict = _clean_review_label(row.get("reviewer_strict_reference_label"))
        invalid_fields = []
        if semantic not in REVIEW_LABELS and semantic != PENDING_LABEL:
            invalid_fields.append("reviewer_semantic_user_question_label")
        if strict not in REVIEW_LABELS and strict != PENDING_LABEL:
            invalid_fields.append("reviewer_strict_reference_label")
        if invalid_fields:
            invalid.append(
                {
                    "case_id": row.get("case_id"),
                    "invalid_fields": invalid_fields,
                    "semantic_label": semantic,
                    "strict_label": strict,
                }
            )
    return invalid


def _pending_label_rows(rows: list[dict[str, Any]]) -> list[str]:
    pending: list[str] = []
    for row in rows:
        semantic = _clean_review_label(row.get("reviewer_semantic_user_question_label"))
        strict = _clean_review_label(row.get("reviewer_strict_reference_label"))
        if semantic == PENDING_LABEL or strict == PENDING_LABEL:
            pending.append(str(row.get("case_id") or ""))
    return pending


def _clean_review_label(value: Any) -> str:
    return str(value or "").strip().lower()


def _policy_label(review_label: str) -> str:
    if review_label in {"correct", "incorrect"}:
        return review_label
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
    return "adjudication_required"


def _dual_policy_case(row: dict[str, Any]) -> dict[str, Any]:
    semantic_review = _clean_review_label(row.get("reviewer_semantic_user_question_label"))
    strict_review = _clean_review_label(row.get("reviewer_strict_reference_label"))
    semantic_label = _policy_label(semantic_review)
    strict_label = _policy_label(strict_review)
    combined = _combined_label(semantic_label, strict_label)
    return {
        "case_id": row.get("case_id"),
        "semantic_review_label": semantic_review,
        "strict_review_label": strict_review,
        "semantic_policy_label": semantic_label,
        "strict_policy_label": strict_label,
        "combined_label": combined,
        "semantic_correct": semantic_label == "correct",
        "strict_correct": strict_label == "correct",
        "reviewer_required_followup": row.get("reviewer_required_followup") or "",
        "reviewer_notes": row.get("reviewer_notes") or "",
        "source_selected_candidate_id": row.get("selected_candidate_id"),
        "source_benchmark_error": row.get("benchmark_error") or "",
    }


def _review_row(record: dict[str, Any]) -> dict[str, Any]:
    selected_id = str(record.get("selected_candidate_id") or "")
    candidates = record.get("candidate_sqls") or []
    primary = _candidate_by_id(candidates, "candidate_1")
    selected = _candidate_by_id(candidates, selected_id)
    verification = record.get("candidate_verification")
    verification_dict = verification if isinstance(verification, dict) else {}
    issue_codes = [
        str(issue.get("code"))
        for issue in verification_dict.get("issues") or []
        if isinstance(issue, dict) and issue.get("code")
    ]
    return {
        "case_id": str(record.get("id") or record.get("case_id") or ""),
        "difficulty": record.get("difficulty") or "unknown",
        "category": record.get("category") or "unknown",
        "question": _question(record),
        "expected_action": record.get("expected_action"),
        "actual_action": record.get("actual_action"),
        "valid_sql": bool(record.get("valid_sql")),
        "unsafe_sql": bool(
            record.get("unsafe_sql")
            or record.get("unsafe_sql_generated")
            or record.get("safety_violation")
        ),
        "selected_candidate_id": selected_id,
        "verifier_action": verification_dict.get("action"),
        "verifier_selected_candidate_id": verification_dict.get("selected_candidate_id"),
        "verifier_reason": verification_dict.get("reason"),
        "verifier_issue_codes": issue_codes,
        "primary_valid_sql": bool(primary.get("valid_sql")) if primary else None,
        "primary_execution_passed": bool(primary.get("execution_passed")) if primary else None,
        "primary_score": _candidate_score(primary),
        "primary_prompt_variant": _candidate_prompt_variant(primary),
        "primary_sql": primary.get("sql") if primary else None,
        "selected_valid_sql": bool(selected.get("valid_sql")) if selected else None,
        "selected_execution_passed": (bool(selected.get("execution_passed")) if selected else None),
        "selected_score": _candidate_score(selected),
        "selected_prompt_variant": _candidate_prompt_variant(selected),
        "selected_sql": selected.get("sql") if selected else record.get("generated_sql"),
        "generated_sql": record.get("generated_sql"),
        "reviewer_semantic_user_question_label": "",
        "reviewer_strict_reference_label": "",
        "reviewer_required_followup": "",
        "reviewer_notes": "",
    }


def _question(record: dict[str, Any]) -> str:
    return str(
        record.get("question_fa") or record.get("question") or record.get("user_utterance_fa") or ""
    )


def _candidate_by_id(candidates: Any, candidate_id: str) -> dict[str, Any] | None:
    if not isinstance(candidates, list):
        return None
    for candidate in candidates:
        if isinstance(candidate, dict) and str(candidate.get("candidate_id")) == candidate_id:
            return candidate
    return None


def _candidate_score(candidate: dict[str, Any] | None) -> float | None:
    if not candidate:
        return None
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    score = (
        metadata.get("candidate_score") if isinstance(metadata.get("candidate_score"), dict) else {}
    )
    value = score.get("score")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _candidate_prompt_variant(candidate: dict[str, Any] | None) -> str | None:
    if not candidate:
        return None
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    value = metadata.get("prompt_variant")
    return str(value) if value else None


def _write_review_csv(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "difficulty",
        "category",
        "question",
        "expected_action",
        "actual_action",
        "valid_sql",
        "unsafe_sql",
        "selected_candidate_id",
        "verifier_action",
        "verifier_selected_candidate_id",
        "verifier_reason",
        "verifier_issue_codes",
        "primary_valid_sql",
        "primary_execution_passed",
        "primary_score",
        "primary_prompt_variant",
        "primary_sql",
        "selected_valid_sql",
        "selected_execution_passed",
        "selected_score",
        "selected_prompt_variant",
        "selected_sql",
        "generated_sql",
        "reviewer_semantic_user_question_label",
        "reviewer_strict_reference_label",
        "reviewer_required_followup",
        "reviewer_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _render_report(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Candidate Adoption Human Review Package",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Scope",
        "",
        f"- source_artifact: `{summary['source_artifact']}`",
        f"- selected_cases_hash: `{summary.get('selected_cases_hash')}`",
        f"- adopted_non_primary_cases: `{summary['adopted_non_primary_cases']}`",
        f"- authoritative: `{summary['authoritative']}`",
        f"- paper_metric_allowed: `{summary['paper_metric_allowed']}`",
        "",
        "## Summary",
        "",
        f"- valid_sql_cases: `{summary['valid_sql_cases']}`",
        f"- unsafe_sql_cases: `{summary['unsafe_sql_cases']}`",
        f"- single_viable_candidate_cases: `{summary['single_viable_candidate_cases']}`",
        f"- gold_reference_fields_redacted: `{summary['gold_reference_fields_redacted']}`",
        f"- strict_reference_fields_included: `{summary['strict_reference_fields_included']}`",
        "",
        "## Cases",
        "",
        "| Case | Selected | Valid | Unsafe | Verifier Issues | Semantic Label | Strict Label |",
        "|---|---|---:|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {case_id} | {selected_candidate_id} | {valid_sql} | {unsafe_sql} | {issues} |  |  |".format(
                case_id=row["case_id"],
                selected_candidate_id=row["selected_candidate_id"],
                valid_sql=row["valid_sql"],
                unsafe_sql=row["unsafe_sql"],
                issues=", ".join(row["verifier_issue_codes"]),
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


def _render_instructions(summary: dict[str, Any]) -> str:
    labels = ", ".join(f"`{label}`" for label in summary["review_label_choices"])
    return "\n".join(
        [
            "# Review Instructions",
            "",
            "Fill only the reviewer columns in `candidate_adoption_review_cases.csv`.",
            "",
            "Required labels:",
            "",
            f"- `reviewer_semantic_user_question_label`: one of {labels}",
            f"- `reviewer_strict_reference_label`: one of {labels}",
            "- `reviewer_required_followup`: short action, or blank",
            "- `reviewer_notes`: brief rationale",
            "",
            "Rules:",
            "",
            "- Keep semantic user-question correctness separate from strict reference correctness.",
            "- Use separately controlled reference material for strict reference review; this package redacts gold SQL and strict benchmark labels.",
            "- Do not edit benchmark predictions, SQL, hashes, or source artifact files.",
            "- Do not use these rows for case-specific prompt, validator, or retrieval tuning.",
            "- This package is not a paper metric until reviewed and signed off by a real reviewer.",
            "",
        ]
    )


def _render_import_report(summary: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    lines = [
        "# Candidate Adoption Review Import",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Summary",
        "",
        f"- status: `{summary.get('status', 'complete')}`",
        f"- authoritative: `{summary.get('authoritative')}`",
        f"- paper_metric_allowed: `{summary.get('paper_metric_allowed')}`",
        f"- common_cases: `{summary.get('common_cases', 0)}`",
        f"- pending_rows: `{summary.get('pending_rows', [])}`",
        f"- invalid_rows: `{summary.get('invalid_rows', [])}`",
        "",
        "## Anti-Fake Statement",
        "",
        summary["anti_fake_policy"],
        "",
    ]
    if cases:
        lines.extend(
            [
                "## Cases",
                "",
                "| Case | Semantic | Strict | Combined |",
                "|---|---|---|---|",
            ]
        )
        for row in cases:
            lines.append(
                "| {case_id} | {semantic_policy_label} | {strict_policy_label} | {combined_label} |".format(
                    **row
                )
            )
        lines.append("")
    return "\n".join(lines)
