from __future__ import annotations

import json
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
    mean_ms: float = 500.0,
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
            "latency": {"mean_ms": mean_ms, "median_ms": 400.0, "p95_ms": p95_ms},
        },
    )
    write_jsonl(root / "run_predictions.jsonl", rows)


def _write_dual_policy_report(
    root: Path,
    rows: list[dict],
    *,
    authoritative: bool = True,
    semantic_counts: dict | None = None,
    strict_counts: dict | None = None,
    combined_counts: dict | None = None,
) -> None:
    root.mkdir()
    write_json(
        root / "dual_policy_summary.json",
        {
            "common_cases": len(rows),
            "authoritative": authoritative,
            "semantic_counts": semantic_counts or {"correct": len(rows)},
            "strict_counts": strict_counts or {"correct": len(rows)},
            "combined_counts": combined_counts or {"both_correct": len(rows)},
        },
    )
    write_jsonl(root / "dual_policy_cases.jsonl", rows)


def test_compare_multi_candidate_ablation_detects_execution_regression_without_semantic_claims(
    tmp_path,
):
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
                "reliability_gate_action": "answer",
                "reliability_gate_latency_ms": 2,
                "attempts": [{"generation_latency_ms": 80, "latency_ms": 5}],
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
                "reliability_gate_action": "needs_review",
                "reliability_gate_latency_ms": 5,
                "attempts": [{"generation_latency_ms": 200, "latency_ms": 10}],
                "multi_candidate_policy": {
                    "enabled": True,
                    "candidate_count": 2,
                    "triggers": ["validation_failed"],
                },
                "candidate_sqls": [
                    {
                        "candidate_id": "a",
                        "metadata": {"execution_latency_ms": 3},
                    },
                    {
                        "candidate_id": "b",
                        "metadata": {"execution_latency_ms": 4},
                    },
                ],
                "candidate_verification": {
                    "selected_candidate_id": "candidate_2",
                    "latency_ms": 8,
                },
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
    issue_outcome = summary["candidate_issue_outcome_summary"]["issue_groups"][
        "CANDIDATE_RESULT_HASH_DISAGREEMENT"
    ]
    assert issue_outcome["case_count"] == 1
    assert issue_outcome["execution_change_counts"] == {"regressed_correct_to_wrong": 1}
    assert issue_outcome["valid_sql_change_counts"] == {"remained_correct": 1}
    assert issue_outcome["selected_candidate_rank_counts"] == {"non_primary_candidate": 1}
    assert issue_outcome["candidate_consistency_counts"] == {"failed": 1}
    assert issue_outcome["reliability_gate_action_counts"] == {"needs_review": 1}
    assert summary["multi_candidate_activation"]["activation_rate"] == 1.0
    assert summary["candidate_diversity_summary"]["adaptive_non_primary_selection_count"] == 1
    assert summary["candidate_diversity_summary"]["adaptive_selected_candidate_rank_counts"] == {
        "non_primary_candidate": 1
    }
    assert summary["candidate_diversity_summary"]["adaptive_candidate_consistency_counts"] == {
        "failed": 1
    }
    assert (
        summary["component_latency_summary"]["available_component_stats"][
            "attempt_generation_latency_ms"
        ]["adaptive_ms"]["mean_ms"]
        == 200.0
    )
    assert (
        summary["component_latency_summary"]["available_component_stats"][
            "candidate_execution_latency_ms"
        ]["adaptive_ms"]["mean_ms"]
        == 7.0
    )
    assert (
        summary["component_latency_summary"]["available_component_stats"][
            "candidate_verification_latency_ms"
        ]["adaptive_ms"]["mean_ms"]
        == 8.0
    )
    assert (
        summary["component_latency_summary"]["available_component_stats"][
            "reliability_gate_latency_ms"
        ]["delta_ms"]["mean_ms"]
        == 3.0
    )
    assert (
        "candidate_verification_latency_ms"
        not in summary["component_latency_summary"]["unavailable_components"]
    )
    assert (
        "reliability_gate_latency_ms"
        not in summary["component_latency_summary"]["unavailable_components"]
    )
    assert summary["latency_diagnostics"]["scope"] == "aggregate_latency_only"
    assert summary["latency_diagnostics"]["overall"]["latency_delta_ms"]["mean_ms"] == 150.0
    assert (
        summary["latency_diagnostics"]["by_adaptive_multi_candidate_policy"]["enabled"][
            "case_count"
        ]
        == 1
    )
    assert (
        summary["latency_diagnostics"]["by_adaptive_reliability_gate_action"]["needs_review"][
            "case_count"
        ]
        == 1
    )
    latency_regression = summary["latency_regression_summary"]
    assert latency_regression["scope"] == "aggregate_latency_regression_triage_only"
    assert latency_regression["status"] == "latency_regression_detected"
    assert latency_regression["regression_signals"] == [
        "p95_latency_increased",
        "mean_latency_increased",
    ]
    assert latency_regression["overall_latency_delta_ms"]["p95_ms"] == 150.0
    assert any(
        group["dimension"] == "adaptive_reliability_gate_action"
        and group["group"] == "needs_review"
        and group["p95_delta_ms"] == 150.0
        for group in latency_regression["top_latency_delta_groups"]
    )
    assert latency_regression["component_delta_contributors"][0] == {
        "component": "total_pipeline_latency_ms",
        "observed_delta_cases": 1,
        "p95_delta_ms": 150.0,
        "mean_delta_ms": 150.0,
        "p95_adaptive_latency_ms": 250.0,
    }
    aggregate_payload = json.dumps(
        {
            "candidate_diversity_summary": summary["candidate_diversity_summary"],
            "candidate_issue_outcome_summary": summary["candidate_issue_outcome_summary"],
            "component_latency_summary": summary["component_latency_summary"],
            "latency_regression_summary": summary["latency_regression_summary"],
            "latency_diagnostics": summary["latency_diagnostics"],
        },
        sort_keys=True,
    )
    assert "case-1" not in aggregate_payload
    assert "gold_sql" not in aggregate_payload
    assert "execution_correct" not in aggregate_payload
    assert summary["acceptance_checks"]["status"] == "insufficient_semantic_evidence"
    assert summary["acceptance_checks"]["latency_budget"]["configured"] is False
    assert summary["acceptance_checks"]["valid_sql_rate_not_decreased"] is True
    assert cases[0]["adaptive_candidate_sql_count"] == 2
    assert cases[0]["adaptive_selected_candidate_id"] == "candidate_2"
    assert "does not run a model" in report
    assert "Aggregate Diagnostic Policy" in report


def test_compare_multi_candidate_ablation_blocks_explicit_latency_budget(tmp_path):
    baseline = tmp_path / "baseline"
    adaptive = tmp_path / "adaptive"
    _write_benchmark_artifact(
        baseline,
        execution_accuracy=0.5,
        valid_sql_rate=1.0,
        reliability_score=0.0,
        mean_ms=500.0,
        p95_ms=1000.0,
        rows=[{"id": "case-1", "execution_correct": False, "valid_sql": True}],
    )
    _write_benchmark_artifact(
        adaptive,
        execution_accuracy=0.5,
        valid_sql_rate=1.0,
        reliability_score=0.0,
        mean_ms=900.0,
        p95_ms=1700.0,
        rows=[{"id": "case-1", "execution_correct": False, "valid_sql": True}],
    )

    paths = compare_multi_candidate_ablation(
        baseline,
        adaptive,
        output_dir=tmp_path / "out",
        max_latency_p95_delta_ms=500.0,
        max_latency_mean_delta_ms=500.0,
    )

    summary = read_json(paths["summary"])
    acceptance = summary["acceptance_checks"]

    assert acceptance["status"] == "blocked"
    assert acceptance["blocker_reasons"] == ["latency_budget_exceeded"]
    assert acceptance["semantic_evidence_available"] is False
    assert acceptance["latency_p95_delta_ms"] == 700.0
    assert acceptance["latency_mean_delta_ms"] == 400.0
    assert acceptance["latency_budget"] == {
        "configured": True,
        "max_p95_delta_ms": 500.0,
        "max_mean_delta_ms": 500.0,
        "p95_delta_ms": 700.0,
        "mean_delta_ms": 400.0,
        "p95_within_budget": False,
        "mean_within_budget": True,
        "exceeded": True,
        "exceeded_dimensions": ["p95"],
        "scope": "aggregate_benchmark_latency_budget_only",
    }


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
        semantic_counts={"incorrect": 1},
        strict_counts={"incorrect": 1},
        combined_counts={"both_incorrect": 1},
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
    assert summary["acceptance_checks"]["semantic_evidence_available"] is True
    assert cases[0]["semantic_policy_change"] == "regressed_correct_to_not_correct"


def test_compare_multi_candidate_ablation_rejects_non_authoritative_dual_policy_as_semantic_evidence(
    tmp_path,
):
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
    rows = [
        {
            "case_id": "case-1",
            "semantic_policy_label": "correct",
            "strict_policy_label": "correct",
        }
    ]
    _write_dual_policy_report(baseline_dual, rows, authoritative=False)
    _write_dual_policy_report(adaptive_dual, rows, authoritative=False)

    paths = compare_multi_candidate_ablation(
        baseline,
        adaptive,
        output_dir=tmp_path / "out",
        baseline_dual_policy_dir=baseline_dual,
        adaptive_dual_policy_dir=adaptive_dual,
    )

    summary = read_json(paths["summary"])

    assert summary["semantic_policy_change_counts"] == {"remained_correct": 1}
    assert summary["acceptance_checks"]["semantic_evidence_available"] is False
    assert summary["acceptance_checks"]["baseline_dual_policy_evidence"]["authoritative"] is False
    assert summary["acceptance_checks"]["status"] == "insufficient_semantic_evidence"


def test_compare_multi_candidate_ablation_treats_pending_import_dir_as_missing_semantic_evidence(
    tmp_path,
):
    baseline = tmp_path / "baseline"
    adaptive = tmp_path / "adaptive"
    pending_dual = tmp_path / "pending_dual"
    pending_dual.mkdir()
    write_json(
        pending_dual / "candidate_adoption_review_import_summary.json",
        {"status": "pending_review", "pending_rows": ["case-1"]},
    )
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

    paths = compare_multi_candidate_ablation(
        baseline,
        adaptive,
        output_dir=tmp_path / "out",
        baseline_dual_policy_dir=pending_dual,
        adaptive_dual_policy_dir=pending_dual,
    )

    summary = read_json(paths["summary"])
    cases = read_jsonl(paths["cases"])

    assert summary["semantic_policy_change_counts"] == {"unavailable": 1}
    assert summary["acceptance_checks"]["semantic_evidence_available"] is False
    assert summary["acceptance_checks"]["baseline_dual_policy_evidence"]["blocking_counts"] == {
        "missing_summary": 1
    }
    assert cases[0]["semantic_policy_change"] == "unavailable"


def test_compare_multi_candidate_ablation_blocks_valid_sql_rate_regression_even_without_judges(
    tmp_path,
):
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
