from __future__ import annotations

from pathlib import Path

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl
from src.evaluation.multi_candidate_ablation import compare_multi_candidate_ablation


def _write_benchmark_artifact(
    root: Path,
    *,
    selected_cases_hash: str = "same-hash",
    execution_accuracy: float,
    valid_sql_rate: float,
    reliability_score: float,
    unsafe_sql: int = 0,
    p95_ms: float = 1000.0,
    rows: list[dict],
) -> None:
    root.mkdir()
    write_json(
        root / "run_summary.json",
        {
            "config": {
                "dataset_hash": "dataset-hash",
                "selected_cases_hash": selected_cases_hash,
                "model_name": "qwen-local",
            },
            "dataset": {"total_evaluated": len(rows)},
            "metrics": {
                "execution_accuracy": {"value": execution_accuracy},
                "valid_sql_rate": {"value": valid_sql_rate},
            },
            "reliability": {"score": reliability_score, "unsafe_sql": unsafe_sql},
            "latency": {"mean_ms": 500.0, "median_ms": 400.0, "p95_ms": p95_ms},
        },
    )
    write_jsonl(root / "run_predictions.jsonl", rows)


def _write_dual_policy_report(root: Path, rows: list[dict]) -> None:
    root.mkdir()
    write_json(root / "dual_policy_summary.json", {"common_cases": len(rows)})
    write_jsonl(root / "dual_policy_cases.jsonl", rows)


def test_compare_multi_candidate_ablation_detects_execution_regression_without_semantic_claims(tmp_path):
    baseline = tmp_path / "baseline"
    adaptive = tmp_path / "adaptive"
    _write_benchmark_artifact(
        baseline,
        execution_accuracy=1.0,
        valid_sql_rate=1.0,
        reliability_score=2.0,
        p95_ms=1000.0,
        rows=[
            {
                "id": "case-1",
                "execution_correct": True,
                "valid_sql": True,
                "error": "",
                "latency_ms": 100,
            }
        ],
    )
    _write_benchmark_artifact(
        adaptive,
        execution_accuracy=0.0,
        valid_sql_rate=1.0,
        reliability_score=-1.0,
        p95_ms=2000.0,
        rows=[
            {
                "id": "case-1",
                "execution_correct": False,
                "valid_sql": True,
                "error": "RESULT_MISMATCH",
                "latency_ms": 250,
                "multi_candidate_policy": {
                    "enabled": True,
                    "candidate_count": 2,
                    "triggers": ["validation_failed"],
                },
                "candidate_sqls": [{"candidate_id": "a"}, {"candidate_id": "b"}],
                "candidate_consistency": {
                    "passed": False,
                    "issues": [{"code": "CANDIDATE_RESULT_HASH_DISAGREEMENT"}],
                },
            }
        ],
    )

    paths = compare_multi_candidate_ablation(baseline, adaptive, output_dir=tmp_path / "out")

    summary = read_json(paths["summary"])
    cases = read_jsonl(paths["cases"])
    report = Path(paths["report"]).read_text(encoding="utf-8")

    assert summary["same_selected_cases_hash"] is True
    assert summary["execution_change_counts"] == {"regressed_correct_to_wrong": 1}
    assert summary["candidate_issue_counts"] == {"CANDIDATE_RESULT_HASH_DISAGREEMENT": 1}
    assert summary["multi_candidate_activation"]["activation_rate"] == 1.0
    assert summary["acceptance_checks"]["status"] == "insufficient_semantic_evidence"
    assert summary["acceptance_checks"]["valid_sql_rate_not_decreased"] is True
    assert cases[0]["adaptive_candidate_sql_count"] == 2
    assert "does not run a model" in report


def test_compare_multi_candidate_ablation_uses_dual_policy_labels_without_inference(tmp_path):
    baseline = tmp_path / "baseline"
    adaptive = tmp_path / "adaptive"
    baseline_dual = tmp_path / "baseline_dual"
    adaptive_dual = tmp_path / "adaptive_dual"
    _write_benchmark_artifact(
        baseline,
        execution_accuracy=0.5,
        valid_sql_rate=1.0,
        reliability_score=0.0,
        rows=[{"id": "case-1", "execution_correct": True, "valid_sql": True, "latency_ms": 100}],
    )
    _write_benchmark_artifact(
        adaptive,
        execution_accuracy=0.5,
        valid_sql_rate=1.0,
        reliability_score=0.0,
        rows=[{"id": "case-1", "execution_correct": True, "valid_sql": True, "latency_ms": 120}],
    )
    _write_dual_policy_report(
        baseline_dual,
        [
            {
                "case_id": "case-1",
                "semantic_policy_label": "correct",
                "strict_policy_label": "correct",
            }
        ],
    )
    _write_dual_policy_report(
        adaptive_dual,
        [
            {
                "case_id": "case-1",
                "semantic_policy_label": "incorrect",
                "strict_policy_label": "incorrect",
            }
        ],
    )

    paths = compare_multi_candidate_ablation(
        baseline,
        adaptive,
        output_dir=tmp_path / "out",
        baseline_dual_policy_dir=baseline_dual,
        adaptive_dual_policy_dir=adaptive_dual,
    )

    summary = read_json(paths["summary"])
    cases = read_jsonl(paths["cases"])

    assert summary["semantic_policy_change_counts"] == {"regressed_correct_to_not_correct": 1}
    assert summary["strict_policy_change_counts"] == {"regressed_correct_to_not_correct": 1}
    assert summary["acceptance_checks"]["status"] == "blocked"
    assert summary["acceptance_checks"]["semantic_regression_case_ids"] == ["case-1"]
    assert cases[0]["semantic_policy_change"] == "regressed_correct_to_not_correct"


def test_compare_multi_candidate_ablation_blocks_valid_sql_rate_regression_even_without_judges(tmp_path):
    baseline = tmp_path / "baseline"
    adaptive = tmp_path / "adaptive"
    _write_benchmark_artifact(
        baseline,
        execution_accuracy=0.5,
        valid_sql_rate=1.0,
        reliability_score=0.0,
        rows=[{"id": "case-1", "execution_correct": False, "valid_sql": True, "latency_ms": 100}],
    )
    _write_benchmark_artifact(
        adaptive,
        execution_accuracy=0.5,
        valid_sql_rate=0.0,
        reliability_score=0.0,
        rows=[{"id": "case-1", "execution_correct": False, "valid_sql": False, "latency_ms": 120}],
    )

    paths = compare_multi_candidate_ablation(baseline, adaptive, output_dir=tmp_path / "out")

    summary = read_json(paths["summary"])

    assert summary["acceptance_checks"]["status"] == "blocked"
    assert summary["acceptance_checks"]["valid_sql_rate_not_decreased"] is False
    assert summary["acceptance_checks"]["valid_sql_regression_case_ids"] == ["case-1"]
