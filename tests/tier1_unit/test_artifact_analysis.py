from __future__ import annotations

from pathlib import Path

from src.evaluation.artifact_analysis import (
    analyze_benchmark_artifact,
    classify_docs06_error,
    classify_research_error,
    locate_benchmark_artifact,
    requires_semantic_review,
)
from src.evaluation.dataset_loader import write_json, write_jsonl


def _write_artifact(root: Path) -> None:
    prefix = "20260517_test"
    summary = {
        "config": {
            "model_name": "mock-model",
            "model_path": "models/mock.gguf",
            "model_slug": "mock",
            "ablation_id": "unit",
            "enabled_modules": ["nlu"],
            "disabled_modules": [],
            "dataset_hash": "dataset-hash",
            "selected_cases_hash": "cases-hash",
            "git_commit": "abc123",
        },
        "dataset": {
            "total_loaded": 2,
            "total_evaluated": 2,
            "sql_positive": 2,
            "non_sql_or_behavioral": 0,
        },
        "metrics": {
            "execution_accuracy": {
                "value": 0.5,
                "numerator": 1,
                "denominator": 2,
                "description": "Correct execution result / SQL-positive cases",
            }
        },
        "reliability": {"score": 0.5, "unsafe_sql": 0},
        "latency": {"count": 2, "mean_ms": 10.0},
    }
    predictions = [
        {"id": "ok", "ok": True, "execution_correct": True, "semantic_business_correct": None},
        {
            "id": "fail",
            "ok": False,
            "execution_correct": False,
            "valid_sql": True,
            "error": "RESULT_MISMATCH",
            "difficulty": "hard",
            "category": "analysis",
            "intent": "aggregation_query",
            "expected_action": "generate_sql",
            "actual_action": "format_answer",
            "question": "question",
            "generated_sql": "SELECT 1",
            "gold_sql": "SELECT 2",
            "semantic_business_correct": None,
        },
    ]
    attempts = [{"case_id": "fail", "sql": "SELECT 1"}]
    failures = [predictions[1]]
    write_json(root / f"{prefix}_summary.json", summary)
    write_jsonl(root / f"{prefix}_predictions.jsonl", predictions)
    write_jsonl(root / f"{prefix}_attempts.jsonl", attempts)
    write_jsonl(root / f"{prefix}_failures.jsonl", failures)


def test_classify_research_error_marks_semantic_review_required_for_valid_mismatch():
    record = {
        "error": "RESULT_MISMATCH",
        "valid_sql": True,
        "semantic_business_correct": None,
    }

    assert classify_research_error(record) == "SEMANTIC_REVIEW_REQUIRED"
    assert classify_docs06_error(record) is None
    assert requires_semantic_review(record) is True


def test_docs06_classifier_maps_false_abstention_to_clarification_failure():
    assert (
        classify_docs06_error(
            {
                "error": "INVALID_SQL",
                "expected_action": "generate_sql",
                "actual_action": "ask_clarification",
            }
        )
        == "CLARIFICATION_FAILURE"
    )


def test_docs06_classifier_maps_shape_contract_to_docs06_categories():
    assert (
        classify_docs06_error(
            {
                "error": "INVALID_SQL",
                "expected_action": "generate_sql",
                "actual_action": "format_answer",
                "validation_issues": [
                    {
                        "code": "ANALYTICAL_SHAPE_MISSING_RISK_AVERAGE_FILTERS",
                    }
                ],
            }
        )
        == "FILTER_ERROR"
    )

    assert (
        classify_docs06_error(
            {
                "error": "INVALID_SQL",
                "expected_action": "generate_sql",
                "actual_action": "format_answer",
                "validation_issues": [
                    {
                        "code": "ANALYTICAL_SHAPE_MISSING_RISK_GROUPING",
                    }
                ],
            }
        )
        == "AGGREGATION_ERROR"
    )


def test_analyze_benchmark_artifact_writes_report_from_real_files(tmp_path):
    artifact = tmp_path / "benchmark_run"
    artifact.mkdir()
    output = tmp_path / "analysis"
    _write_artifact(artifact)

    paths = analyze_benchmark_artifact(artifact, output_dir=output)

    assert paths["report"].exists()
    assert paths["failure_cases"].exists()
    assert paths["summary"].exists()
    report = paths["report"].read_text(encoding="utf-8")
    assert "Phase 11 Artifact-Backed Error Analysis" in report
    assert "SEMANTIC_REVIEW_REQUIRED" in report
    assert "Docs 06 Taxonomy Alignment" in report
    assert "pending_semantic_review" in report
    assert "does not run a model" in report


def test_locate_benchmark_artifact_prefers_final_files_over_partial(tmp_path):
    artifact = tmp_path / "benchmark_run"
    artifact.mkdir()
    _write_artifact(artifact)
    write_jsonl(artifact / "20260517_test_partial_predictions.jsonl", [{"id": "partial"}])

    located = locate_benchmark_artifact(artifact)

    assert "_partial_" not in located.predictions_path.name
