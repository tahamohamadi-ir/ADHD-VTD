from __future__ import annotations

import csv
from pathlib import Path

from src.evaluation.candidate_adoption_review import (
    build_candidate_adoption_review_package,
    import_candidate_adoption_review_labels,
    validate_candidate_adoption_review_package,
)
from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl


def _write_adaptive_artifact(root: Path) -> None:
    root.mkdir()
    write_json(
        root / "run_summary.json",
        {
            "config": {
                "dataset_hash": "dataset-hash",
                "selected_cases_hash": "selected-hash",
                "model_name": "model-a",
            },
            "dataset": {"total_evaluated": 2},
        },
    )
    write_jsonl(
        root / "run_predictions.jsonl",
        [
            {
                "id": "case-adopted",
                "question": "rate by group",
                "expected_action": "generate_sql",
                "actual_action": "format_answer",
                "difficulty": "medium",
                "category": "rate",
                "valid_sql": True,
                "execution_correct": False,
                "error": "RESULT_MISMATCH",
                "selected_candidate_id": "candidate_2",
                "generated_sql": "SELECT group_name, AVG(flag) FROM t GROUP BY group_name",
                "gold_sql": "SELECT group_name, COUNT(*) AS n, AVG(flag) FROM t GROUP BY group_name",
                "candidate_verification": {
                    "action": "select",
                    "selected_candidate_id": "candidate_2",
                    "reason": "best_runtime_candidate",
                    "issues": [{"code": "SINGLE_VIABLE_CANDIDATE"}],
                },
                "candidate_sqls": [
                    {
                        "candidate_id": "candidate_1",
                        "valid_sql": False,
                        "execution_passed": False,
                        "sql": "SELECT COUNT(*) FROM t",
                        "metadata": {
                            "prompt_variant": "primary",
                            "candidate_score": {"score": 0.5},
                        },
                    },
                    {
                        "candidate_id": "candidate_2",
                        "valid_sql": True,
                        "execution_passed": True,
                        "sql": "SELECT group_name, AVG(flag) FROM t GROUP BY group_name",
                        "metadata": {
                            "prompt_variant": "variant_2_independent_equivalent",
                            "candidate_score": {"score": 12.0},
                        },
                    },
                ],
            },
            {
                "id": "case-primary",
                "question": "count",
                "valid_sql": True,
                "execution_correct": True,
                "selected_candidate_id": "candidate_1",
                "candidate_sqls": [],
            },
        ],
    )


def test_build_candidate_adoption_review_package_writes_pending_review_rows(tmp_path):
    artifact = tmp_path / "adaptive"
    _write_adaptive_artifact(artifact)

    paths = build_candidate_adoption_review_package(
        adaptive_artifact_dir=artifact,
        output_dir=tmp_path / "review",
        reviewer_label="unit_review",
    )

    summary = read_json(paths["summary"])
    rows = read_jsonl(paths["cases_jsonl"])
    report = paths["report"].read_text(encoding="utf-8")
    instructions = paths["instructions"].read_text(encoding="utf-8")
    with paths["cases_csv"].open("r", encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))

    assert summary["reviewer_label"] == "unit_review"
    assert summary["authoritative"] is False
    assert summary["paper_metric_allowed"] is False
    assert summary["adopted_non_primary_cases"] == 1
    assert summary["selected_cases_hash"] == "selected-hash"
    assert summary["gold_reference_fields_redacted"] is True
    assert summary["strict_reference_fields_included"] is False
    assert rows[0]["case_id"] == "case-adopted"
    assert rows[0]["selected_candidate_id"] == "candidate_2"
    assert rows[0]["selected_score"] == 12.0
    assert rows[0]["primary_score"] == 0.5
    assert rows[0]["reviewer_semantic_user_question_label"] == ""
    assert "gold_sql" not in rows[0]
    assert "execution_correct" not in rows[0]
    assert "benchmark_error" not in rows[0]
    assert csv_rows[0]["reviewer_strict_reference_label"] == ""
    assert "gold_sql" not in csv_rows[0]
    assert "execution_correct" not in csv_rows[0]
    assert "benchmark_error" not in csv_rows[0]
    assert "does not create semantic correctness labels" in report
    assert "Gold SQL" in report
    assert "Keep semantic user-question correctness separate" in instructions
    assert validate_candidate_adoption_review_package(tmp_path / "review").ok


def test_validate_candidate_adoption_review_package_rejects_gold_leakage(tmp_path):
    artifact = tmp_path / "adaptive"
    _write_adaptive_artifact(artifact)
    paths = build_candidate_adoption_review_package(
        adaptive_artifact_dir=artifact,
        output_dir=tmp_path / "review",
    )

    rows = read_jsonl(paths["cases_jsonl"])
    rows[0]["gold_sql"] = "SELECT secret_gold FROM t"
    write_jsonl(paths["cases_jsonl"], rows)

    report = validate_candidate_adoption_review_package(tmp_path / "review")

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"CANDIDATE_REVIEW_GOLD_LEAKAGE_FIELD"}


def test_import_candidate_adoption_review_labels_stays_pending_for_blank_labels(tmp_path):
    artifact = tmp_path / "adaptive"
    _write_adaptive_artifact(artifact)
    package_paths = build_candidate_adoption_review_package(
        adaptive_artifact_dir=artifact,
        output_dir=tmp_path / "review",
    )

    paths = import_candidate_adoption_review_labels(
        review_csv=package_paths["cases_csv"],
        output_dir=tmp_path / "imported",
        reviewer_label="unit_review",
        authoritative=True,
    )

    summary = read_json(paths["summary"])

    assert summary["status"] == "pending_review"
    assert summary["authoritative"] is False
    assert summary["pending_rows"] == ["case-adopted"]
    assert "dual_policy_cases" not in paths


def test_import_candidate_adoption_review_labels_writes_dual_policy_artifact(tmp_path):
    artifact = tmp_path / "adaptive"
    _write_adaptive_artifact(artifact)
    package_paths = build_candidate_adoption_review_package(
        adaptive_artifact_dir=artifact,
        output_dir=tmp_path / "review",
    )
    _fill_review_labels(
        package_paths["cases_csv"],
        semantic_label="correct",
        strict_label="incorrect",
        notes="Core answer is acceptable, strict gold support columns are missing.",
    )

    paths = import_candidate_adoption_review_labels(
        review_csv=package_paths["cases_csv"],
        output_dir=tmp_path / "imported",
        reviewer_label="unit_review",
        authoritative=True,
    )

    import_summary = read_json(paths["summary"])
    dual_summary = read_json(paths["dual_policy_summary"])
    dual_cases = read_jsonl(paths["dual_policy_cases"])

    assert import_summary["status"] == "complete"
    assert import_summary["authoritative"] is True
    assert dual_summary["authoritative"] is True
    assert dual_summary["paper_metric_allowed"] is False
    assert dual_summary["semantic_counts"] == {"correct": 1}
    assert dual_summary["strict_counts"] == {"incorrect": 1}
    assert dual_summary["combined_counts"] == {"semantic_correct_strict_incorrect": 1}
    assert dual_cases[0]["case_id"] == "case-adopted"
    assert dual_cases[0]["semantic_policy_label"] == "correct"
    assert dual_cases[0]["strict_policy_label"] == "incorrect"
    assert dual_cases[0]["combined_label"] == "semantic_correct_strict_incorrect"


def _fill_review_labels(
    path: Path,
    *,
    semantic_label: str,
    strict_label: str,
    notes: str,
) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    rows[0]["reviewer_semantic_user_question_label"] = semantic_label
    rows[0]["reviewer_strict_reference_label"] = strict_label
    rows[0]["reviewer_notes"] = notes
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
