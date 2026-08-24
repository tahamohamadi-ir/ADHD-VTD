from __future__ import annotations

import csv
from pathlib import Path

from src.evaluation.dataset_loader import read_json, write_json, write_jsonl
from src.evaluation.dual_policy_packaging import build_dual_policy_evidence_package


def _write_benchmark_artifact(root: Path) -> None:
    root.mkdir()
    write_json(
        root / "run_summary.json",
        {
            "config": {
                "dataset_hash": "dataset-hash",
                "selected_cases_hash": "selected-hash",
            },
            "dataset": {
                "kind": "dev",
                "total_loaded": 60,
                "total_evaluated": 2,
                "sql_positive": 2,
                "by_difficulty": {"easy": 1, "medium": 1},
                "by_category": {"distribution": 1, "rate": 1},
            },
            "metrics": {
                "execution_accuracy": {"value": 0.5},
                "valid_sql_rate": {"value": 1.0},
                "sql2nl_paraphrase_robustness": {"value": 0.5},
            },
            "reliability": {"score": 0.25, "normalized_score": 0.125},
        },
    )
    write_jsonl(
        root / "run_predictions.jsonl",
        [
            {
                "id": "case-a",
                "difficulty": "easy",
                "category": "distribution",
                "error": "",
                "valid_sql": True,
                "execution_correct": True,
            },
            {
                "id": "case-b",
                "difficulty": "medium",
                "category": "rate",
                "error": "RESULT_MISMATCH",
                "valid_sql": True,
                "execution_correct": False,
            },
        ],
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


def _write_dual_policy_artifact(root: Path) -> None:
    root.mkdir()
    write_json(
        root / "dual_policy_summary.json",
        {
            "common_cases": 2,
            "semantic_counts": {"correct": 2},
            "strict_counts": {"correct": 1, "incorrect": 1},
            "combined_counts": {
                "both_correct": 1,
                "semantic_correct_strict_incorrect": 1,
            },
            "anti_fake_policy": "existing rows only",
        },
    )
    write_jsonl(
        root / "dual_policy_cases.jsonl",
        [
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
        ],
    )


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
