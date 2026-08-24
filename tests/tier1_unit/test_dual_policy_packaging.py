from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.evaluation.dataset_loader import read_json, write_json, write_jsonl
from src.evaluation.dual_policy_packaging import build_dual_policy_evidence_package


def _write_benchmark_artifact(root: Path) -> None:
    root.mkdir()
    predictions = [
        {
            "id": "case-a",
            "difficulty": "easy",
            "category": "distribution",
            "expected_action": "generate_sql",
            "should_generate_sql": True,
            "ok": True,
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "error": "",
            "valid_sql": True,
            "execution_correct": True,
        },
        {
            "id": "case-b",
            "difficulty": "medium",
            "category": "rate",
            "expected_action": "generate_sql",
            "should_generate_sql": True,
            "ok": False,
            "generated_sql": "SELECT AVG(age) AS avg_age FROM student_depression",
            "error": "RESULT_MISMATCH",
            "valid_sql": True,
            "execution_correct": False,
        },
    ]
    config = {
        "config_id": "unit_dual_policy_packaging",
        "mode": "agent",
        "dataset_hash": "dataset-hash",
        "selected_cases_hash": "selected-hash",
        "module_flags": {"deterministic_templates": False},
    }
    paths = {
        "config": root / "run_config.json",
        "summary_json": root / "run_summary.json",
        "summary_md": root / "run_summary.md",
        "predictions": root / "run_predictions.jsonl",
        "failures": root / "run_failures.jsonl",
        "benchmark_results_csv": root / "run_benchmark_results.csv",
    }
    write_json(
        paths["summary_json"],
        {
            "config": config,
            "dataset": {
                "kind": "dev",
                "total_loaded": 60,
                "total_evaluated": 2,
                "sql_positive": 2,
                "by_difficulty": {"easy": 1, "medium": 1},
                "by_category": {"distribution": 1, "rate": 1},
            },
            "failures": 1,
            "metrics": {
                "execution_accuracy": {"numerator": 1, "denominator": 2, "value": 0.5},
                "valid_sql_rate": {"numerator": 2, "denominator": 2, "value": 1.0},
                "unsafe_sql_count": {"numerator": 0, "denominator": 2, "value": 0},
                "result_mismatch_count": {"numerator": 1, "denominator": 2, "value": 0.5},
                "sql2nl_paraphrase_robustness": {"value": 0.5},
            },
            "reliability": {"score": 0.25, "normalized_score": 0.125, "unsafe_sql": 0},
            "artifacts": {key: str(path) for key, path in paths.items()},
        },
    )
    write_json(paths["config"], config)
    paths["summary_md"].write_text("# Summary\n", encoding="utf-8")
    paths["benchmark_results_csv"].write_text(
        "id,ok\ncase-a,true\ncase-b,false\n", encoding="utf-8"
    )
    write_jsonl(paths["predictions"], predictions)
    write_jsonl(paths["failures"], [predictions[1]])
    write_json(
        root / "artifact_manifest.json",
        {"completed": {"unit_dual_policy_packaging": {"artifact_dir": str(root)}}},
    )
    write_jsonl(
        root / "run_partial_predictions.jsonl",
        [
            {
                "id": "case-b",
                "difficulty": "wrong",
                "category": "wrong",
                "error": "WRONG_PARTIAL_FILE",
                "valid_sql": False,
                "execution_correct": False,
            }
        ],
    )


def _write_dual_policy_artifact(
    root: Path,
    *,
    authoritative: bool = True,
    unresolved: bool = False,
) -> None:
    root.mkdir()
    cases = [
        {
            "case_id": "case-a",
            "semantic_policy_label": "correct",
            "strict_policy_label": "correct",
            "combined_label": "both_correct",
        },
        {
            "case_id": "case-b",
            "semantic_policy_label": "correct",
            "strict_policy_label": "incorrect",
            "combined_label": "semantic_correct_strict_incorrect",
        },
    ]
    if unresolved:
        cases[1] = {
            "case_id": "case-b",
            "semantic_policy_label": "partial_business_match",
            "strict_policy_label": "incorrect",
            "combined_label": "partial_or_mixed",
        }
    write_json(
        root / "dual_policy_summary.json",
        {
            "common_cases": 2,
            "authoritative": authoritative,
            "semantic_counts": (
                {"correct": 1, "partial_business_match": 1} if unresolved else {"correct": 2}
            ),
            "strict_counts": {"correct": 1, "incorrect": 1},
            "combined_counts": (
                {"both_correct": 1, "partial_or_mixed": 1}
                if unresolved
                else {
                    "both_correct": 1,
                    "semantic_correct_strict_incorrect": 1,
                }
            ),
            "anti_fake_policy": "existing rows only",
        },
    )
    write_jsonl(root / "dual_policy_cases.jsonl", cases)


def test_package_dual_policy_evidence_writes_artifact_backed_tables(tmp_path):
    benchmark = tmp_path / "benchmark"
    dual = tmp_path / "dual"
    _write_benchmark_artifact(benchmark)
    _write_dual_policy_artifact(dual)

    paths = build_dual_policy_evidence_package(
        benchmark_dir=benchmark,
        dual_policy_dir=dual,
        output_dir=tmp_path / "package",
        evidence_label="unit_slice",
    )

    summary = read_json(paths["summary"])
    report = paths["report"].read_text(encoding="utf-8")
    with paths["cases_csv"].open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    assert summary["evidence_label"] == "unit_slice"
    assert summary["dataset"]["selected_cases_hash"] == "selected-hash"
    assert summary["source_verification"] == {
        "benchmark_artifact_verified": True,
        "dual_policy_authoritative": True,
        "dual_policy_complete": True,
    }
    assert summary["benchmark_metrics"]["execution_accuracy"] == 0.5
    assert summary["dual_policy_metrics"]["semantic_correct"] == 2
    assert summary["dual_policy_metrics"]["strict_incorrect"] == 1
    assert summary["dual_policy_metrics"]["semantic_correct_strict_incorrect"] == 1
    assert rows[1]["case_id"] == "case-b"
    assert rows[1]["difficulty"] == "medium"
    assert rows[1]["benchmark_error"] == "RESULT_MISMATCH"
    assert rows[1]["combined_label"] == "semantic_correct_strict_incorrect"
    assert "does not call a model" in report
    assert "Semantic user-question correctness and strict reference correctness" in report


def test_package_dual_policy_evidence_rejects_non_authoritative_labels(tmp_path):
    benchmark = tmp_path / "benchmark"
    dual = tmp_path / "dual"
    _write_benchmark_artifact(benchmark)
    _write_dual_policy_artifact(dual, authoritative=False)

    with pytest.raises(ValueError, match="authoritative"):
        build_dual_policy_evidence_package(
            benchmark_dir=benchmark,
            dual_policy_dir=dual,
            output_dir=tmp_path / "package",
            evidence_label="unit_slice",
        )


def test_package_dual_policy_evidence_rejects_unverified_benchmark_artifact(tmp_path):
    benchmark = tmp_path / "benchmark"
    dual = tmp_path / "dual"
    benchmark.mkdir()
    write_json(
        benchmark / "run_summary.json",
        {
            "config": {
                "dataset_hash": "dataset-hash",
                "selected_cases_hash": "selected-hash",
                "module_flags": {"deterministic_templates": False},
            },
            "dataset": {"total_evaluated": 0},
            "metrics": {},
        },
    )
    write_jsonl(benchmark / "run_predictions.jsonl", [])
    _write_dual_policy_artifact(dual)

    with pytest.raises(ValueError, match="Artifact verification failed"):
        build_dual_policy_evidence_package(
            benchmark_dir=benchmark,
            dual_policy_dir=dual,
            output_dir=tmp_path / "package",
            evidence_label="unit_slice",
        )


def test_package_dual_policy_evidence_rejects_unresolved_labels(tmp_path):
    benchmark = tmp_path / "benchmark"
    dual = tmp_path / "dual"
    _write_benchmark_artifact(benchmark)
    _write_dual_policy_artifact(dual, unresolved=True)

    with pytest.raises(ValueError, match="unresolved labels"):
        build_dual_policy_evidence_package(
            benchmark_dir=benchmark,
            dual_policy_dir=dual,
            output_dir=tmp_path / "package",
            evidence_label="unit_slice",
        )
