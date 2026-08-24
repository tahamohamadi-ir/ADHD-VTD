from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import scripts.check_release_readiness as readiness
from scripts.check_release_readiness import (
    check_release_readiness,
    parse_dual_policy_pair,
)
from src.evaluation.judge_ablation_plan import build_dual_policy_judge_ablation_plan


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _build_verified_artifact(tmp_path: Path, name: str = "run") -> Path:
    root = tmp_path / name
    root.mkdir()
    predictions = [
        {
            "id": "case-1",
            "expected_action": "generate_sql",
            "should_generate_sql": True,
            "ok": True,
            "valid_sql": True,
            "execution_correct": True,
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
        },
        {
            "id": "case-2",
            "expected_action": "generate_sql",
            "should_generate_sql": True,
            "ok": False,
            "valid_sql": False,
            "execution_correct": False,
            "generated_sql": "SELECT missing_col FROM student_depression",
        },
    ]
    config = {
        "config_id": "unit_release_ready",
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
    summary = {
        "config": config,
        "dataset": {"total_evaluated": 2},
        "failures": 1,
        "metrics": {
            "execution_accuracy": {"numerator": 1, "denominator": 2, "value": 0.5},
            "valid_sql_rate": {"numerator": 1, "denominator": 2, "value": 0.5},
            "unsafe_sql_count": {"numerator": 0, "denominator": 2, "value": 0},
        },
        "reliability": {"unsafe_sql": 0},
        "artifacts": {key: str(path) for key, path in paths.items()},
    }
    _write_json(paths["config"], config)
    _write_json(paths["summary_json"], summary)
    paths["summary_md"].write_text("# Summary\n", encoding="utf-8")
    paths["benchmark_results_csv"].write_text("id,ok\ncase-1,true\n", encoding="utf-8")
    _write_jsonl(paths["predictions"], predictions)
    _write_jsonl(paths["failures"], [predictions[1]])
    _write_json(
        root / "artifact_manifest.json",
        {"completed": {"unit": {"artifact_dir": str(root)}}},
    )
    return root


def _build_authoritative_judge_artifact(tmp_path: Path) -> Path:
    root = tmp_path / "judge"
    root.mkdir()
    judgments = [
        {
            "case_id": "case-1",
            "provider": "openrouter",
            "model": "qwen/qwen3.6-plus",
            "prompt_version": "phase16_sql_business_logic_v1",
            "judge_policy": "semantic_user_question",
            "verdict": "business_correct",
            "semantic_business_correct": True,
            "authoritative": True,
            "redacted": True,
        }
    ]
    _write_jsonl(root / "judgments.jsonl", judgments)
    _write_json(
        root / "judge_summary.json",
        {
            "generated_at": "2026-06-28T00:00:00",
            "provider": "openrouter",
            "model": "qwen/qwen3.6-plus",
            "prompt_version": "phase16_sql_business_logic_v1",
            "judge_policy": "semantic_user_question",
            "authoritative": True,
            "authoritative_judgments": 1,
            "non_authoritative_judgments": 0,
            "total_predictions": 1,
            "total_judged": 1,
            "verdict_counts": {"business_correct": 1},
            "semantic_business_counts": {
                "correct": 1,
                "incorrect": 0,
                "unjudged": 0,
                "provider_error": 0,
                "provider_parse_error": 0,
            },
            "redaction_policy": {
                "redaction_applied": True,
                "raw_rows_sent": False,
                "result_previews_sent": False,
                "prompt_response_trace_sent": False,
            },
            "anti_fake_policy": "Live judge artifact. No judgments are inferred or rewritten.",
        },
    )
    _write_json(
        root / "judge_costs.json",
        {
            "provider": "openrouter",
            "model": "qwen/qwen3.6-plus",
            "judge_policy": "semantic_user_question",
            "input_tokens": 10,
            "output_tokens": 5,
            "reasoning_tokens": 0,
            "estimated_cost_usd": 0.01,
            "cost_authoritative": True,
        },
    )
    (root / "semantic_business_summary.csv").write_text(
        "prompt_version,judge_policy,authoritative,total_judged,semantic_correct\n"
        "phase16_sql_business_logic_v1,semantic_user_question,true,1,1\n",
        encoding="utf-8",
    )
    (root / "judge_reasoning.md").write_text("# Judge Reasoning\n", encoding="utf-8")
    return root


def _build_candidate_review_package(tmp_path: Path) -> Path:
    root = tmp_path / "candidate_review"
    root.mkdir()
    _write_json(
        root / "candidate_adoption_review_summary.json",
        {
            "schema_version": "pars_sql_candidate_adoption_review_v1",
            "authoritative": False,
            "paper_metric_allowed": False,
            "gold_reference_fields_redacted": True,
            "strict_reference_fields_included": False,
        },
    )
    rows = [
        {
            "case_id": "case-1",
            "question": "count",
            "valid_sql": True,
            "unsafe_sql": False,
            "selected_candidate_id": "candidate_2",
            "reviewer_semantic_user_question_label": "",
            "reviewer_strict_reference_label": "",
        }
    ]
    _write_jsonl(root / "candidate_adoption_review_cases.jsonl", rows)
    (root / "candidate_adoption_review_cases.csv").write_text(
        "case_id,question,valid_sql,unsafe_sql,selected_candidate_id,"
        "reviewer_semantic_user_question_label,reviewer_strict_reference_label\n"
        "case-1,count,True,False,candidate_2,,\n",
        encoding="utf-8",
    )
    (root / "candidate_adoption_review_report.md").write_text("# Review\n", encoding="utf-8")
    (root / "REVIEW_INSTRUCTIONS.md").write_text("# Instructions\n", encoding="utf-8")
    return root


def _build_comparison_artifact(tmp_path: Path) -> Path:
    root = tmp_path / "comparison"
    root.mkdir()
    _write_json(
        root / "multi_candidate_ablation_summary.json",
        {
            "common_cases": 1,
            "candidate_diversity_summary": {
                "total_common_cases": 1,
                "adaptive_non_primary_selection_count": 1,
                "anti_tuning_policy": (
                    "Aggregate diagnostic only. This summary excludes case IDs, "
                    "gold SQL, generated SQL text, and strict or semantic "
                    "correctness labels."
                ),
            },
            "component_latency_summary": {
                "scope": "recorded_component_latency_only",
                "available_component_stats": {
                    "total_pipeline_latency_ms": {
                        "baseline_ms": {"count": 1},
                        "adaptive_ms": {"count": 1},
                        "delta_ms": {"count": 1},
                    }
                },
                "unavailable_components": {
                    "candidate_verification_latency_ms": ("not_recorded_in_prediction_trace"),
                    "reliability_gate_latency_ms": "not_recorded_in_prediction_trace",
                },
                "anti_tuning_policy": (
                    "Aggregate diagnostic only. This summary excludes case IDs, "
                    "gold SQL, generated SQL text, and strict or semantic "
                    "correctness labels."
                ),
            },
            "latency_diagnostics": {
                "scope": "aggregate_latency_only",
                "overall": {
                    "latency_delta_ms": {
                        "count": 1,
                        "mean_ms": 10.0,
                        "median_ms": 10.0,
                        "p95_ms": 10.0,
                        "min_ms": 10.0,
                        "max_ms": 10.0,
                    }
                },
                "by_adaptive_multi_candidate_policy": {"enabled": {"case_count": 1}},
                "by_adaptive_candidate_sql_count": {"2": {"case_count": 1}},
                "by_adaptive_reliability_gate_action": {"needs_review": {"case_count": 1}},
                "by_candidate_issue_code": {},
                "anti_tuning_policy": (
                    "Aggregate diagnostic only. This summary excludes case IDs, "
                    "gold SQL, generated SQL text, and strict or semantic "
                    "correctness labels."
                ),
            },
            "latency_regression_summary": {
                "scope": "aggregate_latency_regression_triage_only",
                "status": "latency_regression_detected",
                "thresholds": {
                    "p95_regression_threshold_ms": 0.0,
                    "mean_regression_threshold_ms": 0.0,
                },
                "regression_signals": [
                    "p95_latency_increased",
                    "mean_latency_increased",
                ],
                "overall_latency_delta_ms": {
                    "count": 1,
                    "mean_ms": 10.0,
                    "median_ms": 10.0,
                    "p95_ms": 10.0,
                    "min_ms": 10.0,
                    "max_ms": 10.0,
                },
                "top_latency_delta_groups": [
                    {
                        "dimension": "adaptive_reliability_gate_action",
                        "group": "needs_review",
                        "case_count": 1,
                        "p95_delta_ms": 10.0,
                        "mean_delta_ms": 10.0,
                        "p95_adaptive_latency_ms": 20.0,
                    }
                ],
                "component_delta_contributors": [
                    {
                        "component": "total_pipeline_latency_ms",
                        "observed_delta_cases": 1,
                        "p95_delta_ms": 10.0,
                        "mean_delta_ms": 10.0,
                        "p95_adaptive_latency_ms": 20.0,
                    }
                ],
                "unavailable_components": {},
                "anti_tuning_policy": (
                    "Aggregate diagnostic only. This summary excludes case IDs, "
                    "gold SQL, generated SQL text, and strict or semantic "
                    "correctness labels."
                ),
            },
            "acceptance_checks": {
                "status": "insufficient_semantic_evidence",
                "semantic_evidence_available": False,
            },
            "anti_fake_policy": (
                "This report compares existing benchmark artifacts only. It "
                "does not run a model, execute SQL, edit predictions, infer "
                "missing semantic labels, or use case IDs/gold SQL as tuning "
                "rules."
            ),
        },
    )
    _write_jsonl(
        root / "multi_candidate_ablation_cases.jsonl",
        [
            {
                "case_id": "case-1",
                "execution_change": "remained_wrong",
                "valid_sql_change": "remained_correct",
            }
        ],
    )
    (root / "multi_candidate_ablation_report.md").write_text(
        "# Report\n\n## Aggregate Diagnostic Policy\n",
        encoding="utf-8",
    )
    return root


def _write_promotion_doc(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Promotion Registry",
        "",
        "| Scope | Artifact Type | Artifact Path | Evidence Family | Status | Paper Metric Allowed |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {scope} | {artifact_type} | {artifact_path} | {evidence_family} | "
            "{status} | {paper_metric_allowed} |".format(**row)
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_check_release_readiness_accepts_verified_artifact_and_clean_docs(tmp_path):
    artifact = _build_verified_artifact(tmp_path)
    clean_doc = tmp_path / "clean.md"
    clean_doc.write_text("# Clean\nNo stale references.\n", encoding="utf-8")

    report = check_release_readiness(
        benchmark_artifact_dirs=[artifact],
        reference_paths=[clean_doc],
        required_paths=[clean_doc],
        risks_path=None,
    )

    assert report.ok
    assert report.checked["benchmark_artifacts"][0]["ok"] is True
    assert report.checked["stale_reference_issues"] == 0


def test_check_release_readiness_rejects_pending_dual_policy_evidence(tmp_path):
    artifact = _build_verified_artifact(tmp_path)
    pending = tmp_path / "pending_dual"
    pending.mkdir()
    _write_json(
        pending / "candidate_adoption_review_import_summary.json",
        {"status": "pending_review", "pending_rows": ["case-1"]},
    )

    report = check_release_readiness(
        dual_policy_pairs=[(artifact, pending)],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    codes = {issue.code for issue in report.issues}
    assert not report.ok
    assert "DUAL_POLICY_PENDING_REVIEW" in codes
    assert "DUAL_POLICY_SUMMARY_MISSING" in codes


def test_check_release_readiness_accepts_authoritative_judge_artifact(tmp_path):
    judge = _build_authoritative_judge_artifact(tmp_path)

    report = check_release_readiness(
        judge_artifact_dirs=[judge],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert report.ok
    assert report.checked["judge_artifacts"][0]["checked"]["authoritative"] is True


def test_check_release_readiness_accepts_candidate_review_package(tmp_path):
    review = _build_candidate_review_package(tmp_path)

    report = check_release_readiness(
        candidate_review_dirs=[review],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert report.ok
    assert report.checked["candidate_review_packages"][0]["ok"] is True


def test_check_release_readiness_accepts_comparison_artifact(tmp_path):
    comparison = _build_comparison_artifact(tmp_path)

    report = check_release_readiness(
        comparison_artifact_dirs=[comparison],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert report.ok
    checked = report.checked["comparison_artifacts"][0]["checked"]
    assert checked["common_cases"] == 1
    assert checked["case_rows"] == 1
    assert checked["aggregate_summary_keys_present"] is True
    assert checked["component_latency_required_keys_present"] is True
    assert checked["latency_diagnostics_required_keys_present"] is True
    assert checked["acceptance_status"] == "insufficient_semantic_evidence"
    assert checked["semantic_evidence_available"] is False
    assert checked["acceptance_blockers"] == []
    assert checked["latency_budget_configured"] is False
    assert checked["latency_budget_exceeded"] is False
    assert checked["promotion_eligible"] is False
    assert checked["promotion_status"] == "blocked_until_authoritative_semantic_evidence"
    assert checked["promotion_blockers"] == [
        "acceptance_status_insufficient_semantic_evidence",
        "semantic_evidence_unavailable",
    ]


def test_check_release_readiness_reports_latency_budget_blocker(tmp_path):
    comparison = _build_comparison_artifact(tmp_path)
    summary_path = comparison / "multi_candidate_ablation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["acceptance_checks"].update(
        {
            "status": "blocked",
            "blocker_reasons": ["latency_budget_exceeded"],
            "latency_budget": {
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
            },
        }
    )
    _write_json(summary_path, summary)

    report = check_release_readiness(
        comparison_artifact_dirs=[comparison],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert report.ok
    checked = report.checked["comparison_artifacts"][0]["checked"]
    assert checked["acceptance_status"] == "blocked"
    assert checked["acceptance_blockers"] == ["latency_budget_exceeded"]
    assert checked["latency_budget_configured"] is True
    assert checked["latency_budget_exceeded"] is True
    assert checked["promotion_blockers"] == [
        "acceptance_status_blocked",
        "latency_budget_exceeded",
        "semantic_evidence_unavailable",
    ]


def test_check_release_readiness_rejects_unknown_comparison_acceptance_status(
    tmp_path,
):
    comparison = _build_comparison_artifact(tmp_path)
    summary_path = comparison / "multi_candidate_ablation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["acceptance_checks"]["status"] = "paper_ready"
    _write_json(summary_path, summary)

    report = check_release_readiness(
        comparison_artifact_dirs=[comparison],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert "COMPARISON_ACCEPTANCE_STATUS_INVALID" in {issue.code for issue in report.issues}


def test_check_release_readiness_rejects_invalid_comparison_acceptance_blockers(
    tmp_path,
):
    comparison = _build_comparison_artifact(tmp_path)
    summary_path = comparison / "multi_candidate_ablation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["acceptance_checks"]["blocker_reasons"] = "latency_budget_exceeded"
    _write_json(summary_path, summary)

    report = check_release_readiness(
        comparison_artifact_dirs=[comparison],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert "COMPARISON_ACCEPTANCE_BLOCKERS_INVALID" in {issue.code for issue in report.issues}


def test_check_release_readiness_rejects_leaky_comparison_aggregate(tmp_path):
    comparison = _build_comparison_artifact(tmp_path)
    summary_path = comparison / "multi_candidate_ablation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["candidate_diversity_summary"]["case_id"] = "case-1"
    _write_json(summary_path, summary)

    report = check_release_readiness(
        comparison_artifact_dirs=[comparison],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"COMPARISON_AGGREGATE_LEAKAGE_FIELD"}


def test_check_release_readiness_rejects_leaky_optional_comparison_aggregate(tmp_path):
    comparison = _build_comparison_artifact(tmp_path)
    summary_path = comparison / "multi_candidate_ablation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["candidate_issue_outcome_summary"] = {
        "scope": "aggregate_candidate_issue_outcomes_only",
        "case_id": "case-1",
        "anti_tuning_policy": (
            "Aggregate diagnostic only. This summary excludes case IDs, "
            "gold SQL, generated SQL text, and strict or semantic correctness labels."
        ),
    }
    _write_json(summary_path, summary)

    report = check_release_readiness(
        comparison_artifact_dirs=[comparison],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"COMPARISON_AGGREGATE_LEAKAGE_FIELD"}


def test_check_release_readiness_rejects_leaky_latency_regression_summary(tmp_path):
    comparison = _build_comparison_artifact(tmp_path)
    summary_path = comparison / "multi_candidate_ablation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["latency_regression_summary"]["generated_sql"] = "SELECT secret FROM t"
    _write_json(summary_path, summary)

    report = check_release_readiness(
        comparison_artifact_dirs=[comparison],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"COMPARISON_AGGREGATE_LEAKAGE_FIELD"}


def test_check_release_readiness_rejects_comparison_missing_latency_group(tmp_path):
    comparison = _build_comparison_artifact(tmp_path)
    summary_path = comparison / "multi_candidate_ablation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    del summary["latency_diagnostics"]["by_adaptive_reliability_gate_action"]
    _write_json(summary_path, summary)

    report = check_release_readiness(
        comparison_artifact_dirs=[comparison],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"COMPARISON_LATENCY_DIAGNOSTIC_KEY_MISSING"}


def test_check_release_readiness_rejects_comparison_missing_component_latency_summary(
    tmp_path,
):
    comparison = _build_comparison_artifact(tmp_path)
    summary_path = comparison / "multi_candidate_ablation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    del summary["component_latency_summary"]
    _write_json(summary_path, summary)

    report = check_release_readiness(
        comparison_artifact_dirs=[comparison],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"COMPARISON_AGGREGATE_SUMMARY_MISSING"}


def test_check_release_readiness_rejects_leaky_candidate_review_package(tmp_path):
    review = _build_candidate_review_package(tmp_path)
    (review / "candidate_adoption_review_cases.csv").write_text(
        "case_id,gold_sql,reviewer_semantic_user_question_label,reviewer_strict_reference_label\n"
        "case-1,SELECT secret_gold FROM t,,\n",
        encoding="utf-8",
    )

    report = check_release_readiness(
        candidate_review_dirs=[review],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"CANDIDATE_REVIEW_GOLD_LEAKAGE_FIELD"}


def test_check_release_readiness_accepts_paper_final_benchmark_promotion(tmp_path):
    artifact = _build_verified_artifact(tmp_path)
    promotion_doc = tmp_path / "promotion.md"
    _write_promotion_doc(
        promotion_doc,
        [
            {
                "scope": "main_sql_positive",
                "artifact_type": "benchmark",
                "artifact_path": str(artifact),
                "evidence_family": "sql_positive",
                "status": "paper_final",
                "paper_metric_allowed": "true",
            }
        ],
    )

    report = check_release_readiness(
        promotion_docs=[promotion_doc],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert report.ok
    assert report.checked["promotion_registry_rows"] == 1
    assert report.checked["promotion_registry_issues"] == 0


def test_check_release_readiness_accepts_paper_final_judge_promotion(tmp_path):
    judge = _build_authoritative_judge_artifact(tmp_path)
    promotion_doc = tmp_path / "promotion.md"
    _write_promotion_doc(
        promotion_doc,
        [
            {
                "scope": "semantic_business",
                "artifact_type": "judge",
                "artifact_path": str(judge),
                "evidence_family": "semantic_business",
                "status": "paper_final",
                "paper_metric_allowed": "true",
            }
        ],
    )

    report = check_release_readiness(
        promotion_docs=[promotion_doc],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert report.ok
    assert report.checked["promotion_registry_rows"] == 1


def test_check_release_readiness_allows_final_split_judge_path(tmp_path):
    judge_root = tmp_path / "paper1_main_semantic_openrouter_s400_split"
    judge_root.mkdir()
    judge = _build_authoritative_judge_artifact(judge_root)
    promotion_doc = tmp_path / "promotion.md"
    _write_promotion_doc(
        promotion_doc,
        [
            {
                "scope": "semantic_business",
                "artifact_type": "judge",
                "artifact_path": str(judge),
                "evidence_family": "semantic_business",
                "status": "paper_final",
                "paper_metric_allowed": "true",
            }
        ],
    )

    report = check_release_readiness(
        promotion_docs=[promotion_doc],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert report.ok


def test_check_release_readiness_rejects_missing_promotion_registry(tmp_path):
    promotion_doc = tmp_path / "promotion.md"
    promotion_doc.write_text("# Promotion\nNo table yet.\n", encoding="utf-8")

    report = check_release_readiness(
        promotion_docs=[promotion_doc],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"PROMOTION_REGISTRY_MISSING"}


def test_check_release_readiness_rejects_nonfinal_metric_promotion(tmp_path):
    promotion_doc = tmp_path / "promotion.md"
    _write_promotion_doc(
        promotion_doc,
        [
            {
                "scope": "phase7_spl10",
                "artifact_type": "benchmark",
                "artifact_path": "results/benchmark/phase7_promptdiverse_adopt_spl10",
                "evidence_family": "sql_positive",
                "status": "diagnostic_only",
                "paper_metric_allowed": "true",
            }
        ],
    )

    report = check_release_readiness(
        promotion_docs=[promotion_doc],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"PROMOTION_NONFINAL_METRIC_ALLOWED"}


def test_check_release_readiness_rejects_final_smoke_promotion(tmp_path):
    artifact = _build_verified_artifact(tmp_path, "smoke_run")
    promotion_doc = tmp_path / "promotion.md"
    _write_promotion_doc(
        promotion_doc,
        [
            {
                "scope": "main_smoke",
                "artifact_type": "benchmark",
                "artifact_path": str(artifact),
                "evidence_family": "sql_positive",
                "status": "paper_final",
                "paper_metric_allowed": "true",
            }
        ],
    )

    report = check_release_readiness(
        promotion_docs=[promotion_doc],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert "PROMOTION_FORBIDDEN_FINAL_ARTIFACT" in {issue.code for issue in report.issues}


def test_check_release_readiness_rejects_non_authoritative_judge_artifact(tmp_path):
    judge = _build_authoritative_judge_artifact(tmp_path)
    summary_path = judge / "judge_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["authoritative"] = False
    _write_json(summary_path, summary)

    report = check_release_readiness(
        judge_artifact_dirs=[judge],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"JUDGE_ARTIFACT_NOT_AUTHORITATIVE"}


def test_check_release_readiness_accepts_verified_judge_ablation_plan(tmp_path):
    baseline = _build_verified_artifact(tmp_path, "baseline")
    adaptive = _build_verified_artifact(tmp_path, "adaptive")
    paths = build_dual_policy_judge_ablation_plan(
        baseline,
        adaptive,
        output_dir=tmp_path / "judge_plan",
        judge_models=["qwen/qwen3.6-plus", "deepseek/deepseek-v4-flash"],
    )

    report = check_release_readiness(
        judge_ablation_plan_dirs=[paths["manifest"].parent],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert report.ok
    plan = report.checked["judge_ablation_plans"][0]
    assert plan["ok"] is True
    assert plan["checked"]["judge_policy_counts"] == {"semantic": 4, "strict": 4}
    assert plan["input_artifacts"]["baseline_artifact_dir"]["ok"] is True
    assert plan["input_artifacts"]["adaptive_artifact_dir"]["ok"] is True


def test_check_release_readiness_rejects_invalid_judge_ablation_plan(tmp_path):
    baseline = _build_verified_artifact(tmp_path, "baseline")
    adaptive = _build_verified_artifact(tmp_path, "adaptive")
    paths = build_dual_policy_judge_ablation_plan(
        baseline,
        adaptive,
        output_dir=tmp_path / "judge_plan",
        judge_models=["qwen/qwen3.6-plus", "deepseek/deepseek-v4-flash"],
    )
    manifest_path = paths["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["anti_fake_policy"] = "This is a final semantic result."
    _write_json(manifest_path, manifest)

    report = check_release_readiness(
        judge_ablation_plan_dirs=[paths["manifest"].parent],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {
        "JUDGE_ABLATION_PLAN_ANTI_FAKE_POLICY_INCOMPLETE"
    }


def test_check_release_readiness_rejects_stale_doc_references(tmp_path):
    stale_doc = tmp_path / "stale.md"
    stale_doc.write_text("Read docs/context-hub/BENCHMARK_PROTOCOL.md\n", encoding="utf-8")

    report = check_release_readiness(
        reference_paths=[stale_doc],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"STALE_REFERENCE"}


def test_check_release_readiness_rejects_noncanonical_context_hub_paths(tmp_path):
    stale_doc = tmp_path / "stale_context.md"
    stale_doc.write_text(
        "Read docs/context-hub/query-shape-contracts.md\n"
        "Read docs/context-hub/failure-patterns.md\n",
        encoding="utf-8",
    )

    report = check_release_readiness(
        reference_paths=[stale_doc],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert [issue.code for issue in report.issues] == [
        "STALE_REFERENCE",
        "STALE_REFERENCE",
    ]
    assert report.checked["stale_reference_issues"] == 2


def test_default_reference_scan_includes_prompt_library_and_aiassistant_rules(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(readiness, "PROJECT_ROOT", tmp_path)
    prompt_library = tmp_path / "CODEX_PROMPTS.md"
    prompt_library.write_text("Read docs/context-hub/BENCHMARK_PROTOCOL.md\n", encoding="utf-8")
    rules_dir = tmp_path / ".aiassistant" / "rules"
    rules_dir.mkdir(parents=True)
    rule_doc = rules_dir / "rule.md"
    rule_doc.write_text("Use DATASET_CARD_DRAFT.md for this task.\n", encoding="utf-8")

    report = readiness.check_release_readiness(
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    stale_issue_paths = {Path(str(issue.path)).name for issue in report.issues}
    assert "CODEX_PROMPTS.md" in stale_issue_paths
    assert "rule.md" in stale_issue_paths
    assert report.checked["stale_reference_issues"] == 2


def test_default_reference_scan_includes_all_agent_skill_docs(tmp_path, monkeypatch):
    monkeypatch.setattr(readiness, "PROJECT_ROOT", tmp_path)
    skill_dir = tmp_path / ".agents" / "skills" / "custom-skill"
    skill_dir.mkdir(parents=True)
    skill_doc = skill_dir / "SKILL.md"
    skill_doc.write_text("Read docs/context-hub/BENCHMARK_PROTOCOL.md\n", encoding="utf-8")

    report = readiness.check_release_readiness(
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {Path(str(issue.path)).name for issue in report.issues} == {"SKILL.md"}
    assert report.checked["stale_reference_issues"] == 1


def test_check_release_readiness_rejects_forbidden_paper_claims(tmp_path):
    paper_doc = tmp_path / "paper.md"
    paper_doc.write_text("This is a state-of-the-art diagnostic system.\n", encoding="utf-8")

    report = check_release_readiness(
        paper_docs=[paper_doc],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    codes = [issue.code for issue in report.issues]
    assert not report.ok
    assert codes == ["FORBIDDEN_PAPER_CLAIM", "FORBIDDEN_PAPER_CLAIM"]


def test_check_release_readiness_rejects_mixed_metric_family_claims(tmp_path):
    paper_doc = tmp_path / "paper.md"
    paper_doc.write_text(
        "Overall accuracy combines strict EX, semantic/business correctness, "
        "and behavioral expected-action accuracy.\n",
        encoding="utf-8",
    )

    report = check_release_readiness(
        paper_docs=[paper_doc],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"MIXED_METRIC_FAMILIES"}
    assert report.checked["paper_metric_family_issues"] == 1


def test_check_release_readiness_allows_explicit_metric_family_separation(tmp_path):
    paper_doc = tmp_path / "paper.md"
    paper_doc.write_text(
        "Strict EX and semantic/business correctness are reported separately "
        "with different denominators.\n",
        encoding="utf-8",
    )

    report = check_release_readiness(
        paper_docs=[paper_doc],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert report.ok
    assert report.checked["paper_metric_family_issues"] == 0


def test_check_release_readiness_can_include_standard_paper_docs(tmp_path, monkeypatch):
    standard_doc = tmp_path / "standard.md"
    standard_doc.write_text("# Standard\nNo paper claim issues.\n", encoding="utf-8")
    rule_dir = tmp_path / "rules"
    rule_dir.mkdir()
    rule_doc = rule_dir / "rule.md"
    rule_doc.write_text(
        "Strict EX and semantic/business correctness are reported separately "
        "with different denominators.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(readiness, "STANDARD_PAPER_DOC_PATHS", (standard_doc,))
    monkeypatch.setattr(readiness, "STANDARD_PAPER_DOC_GLOBS", (rule_dir / "*.md",))

    report = readiness.check_release_readiness(
        paper_docs=[standard_doc],
        include_standard_paper_docs=True,
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert report.ok
    assert report.checked["standard_paper_docs_included"] is True
    assert report.checked["paper_docs"].count(str(standard_doc)) == 1
    assert str(rule_doc) in report.checked["paper_docs"]


def test_check_release_readiness_classifies_open_risks(tmp_path):
    risks_doc = tmp_path / "Risks.md"
    risks_doc.write_text(
        "# Risks\n\n"
        "## R1. Human review blocker\n\n"
        "- Status: Open\n"
        "- Blocker category: blocked_human_review\n"
        "- Current guard: Candidate package is non-authoritative.\n"
        "- Next action: Complete final human review.\n"
        "- Close condition: Authoritative labels are imported and verified.\n\n"
        "## R2. Local guard task\n\n"
        "- Status: Open\n"
        "- Blocker category: actionable_nonhuman\n"
        "- Current guard: Release gate validates aggregate artifacts.\n"
        "- Guard command: .\\.venv\\Scripts\\python.exe scripts\\check_release_readiness.py\n"
        "- Next action: Run the local guard and fix failures.\n"
        "- Close condition: Guard passes with no actionable risk failures.\n",
        encoding="utf-8",
    )

    report = check_release_readiness(
        reference_paths=[],
        required_paths=[],
        risks_path=risks_doc,
    )

    assert report.ok
    assert report.checked["open_risks"] == 2
    assert report.checked["actionable_open_risks"] == 1
    assert report.checked["open_risk_categories"]["blocked_human_review"] == 1
    assert report.checked["open_risk_categories"]["actionable_nonhuman"] == 1
    assert report.checked["risk_schema_issues"] == 0


def test_check_release_readiness_can_fail_on_actionable_open_risks(tmp_path):
    risks_doc = tmp_path / "Risks.md"
    risks_doc.write_text(
        "# Risks\n\n"
        "## R1. Local guard task\n\n"
        "- Status: Open\n"
        "- Blocker category: actionable_nonhuman\n"
        "- Current guard: Release gate validates aggregate artifacts.\n"
        "- Guard command: .\\.venv\\Scripts\\python.exe scripts\\check_release_readiness.py\n"
        "- Next action: Run the local guard and fix failures.\n"
        "- Close condition: Guard passes with no actionable risk failures.\n",
        encoding="utf-8",
    )

    report = check_release_readiness(
        reference_paths=[],
        required_paths=[],
        risks_path=risks_doc,
        fail_on_actionable_risks=True,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"ACTIONABLE_OPEN_RISKS_PRESENT"}
    assert report.checked["actionable_open_risks"] == 1


def test_check_release_readiness_rejects_open_risk_without_close_condition(tmp_path):
    risks_doc = tmp_path / "Risks.md"
    risks_doc.write_text(
        "# Risks\n\n"
        "## R1. Missing close condition\n\n"
        "- Status: Open\n"
        "- Blocker category: blocked_human_review\n"
        "- Current guard: Candidate package is non-authoritative.\n"
        "- Next action: Complete final human review.\n",
        encoding="utf-8",
    )

    report = check_release_readiness(
        reference_paths=[],
        required_paths=[],
        risks_path=risks_doc,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"RISK_FIELD_MISSING"}
    assert report.checked["risk_schema_issues"] == 1


def test_check_release_readiness_rejects_paper_table_without_provenance(tmp_path):
    paper_table = tmp_path / "run_paper_tables.md"
    paper_table.write_text(
        "# Paper Tables (Auto-generated)\n\n"
        "## Table 1: End-to-End Performance\n\n"
        "| Metric | Value |\n|---|---:|\n| execution_accuracy | 0.5 |\n",
        encoding="utf-8",
    )

    report = check_release_readiness(
        paper_docs=[paper_table],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"PAPER_TABLE_PROVENANCE_MISSING"}
    assert report.checked["paper_table_provenance_issues"] == 1


def test_check_release_readiness_accepts_paper_table_with_provenance(tmp_path):
    paper_table = tmp_path / "run_paper_tables.md"
    paper_table.write_text(
        "# Paper Tables (Auto-generated)\n\n"
        "## Configuration\n\n"
        "| Field | Value |\n|---|---|\n"
        "| dataset_hash | dataset-hash |\n"
        "| selected_cases_hash | selected-hash |\n\n"
        "## Artifact Provenance\n\n"
        "| Artifact | Path |\n|---|---|\n"
        "| summary_json | results/run/summary.json |\n"
        "| predictions | results/run/predictions.jsonl |\n",
        encoding="utf-8",
    )

    report = check_release_readiness(
        paper_docs=[paper_table],
        reference_paths=[],
        required_paths=[],
        risks_path=None,
    )

    assert report.ok
    assert report.checked["paper_table_provenance_issues"] == 0


def test_check_release_readiness_rejects_direct_sql_execution_paths(tmp_path):
    bad_path = tmp_path / "bad_sql.py"
    bad_path.write_text(
        "import sqlite3\nconn = sqlite3.connect('db.sqlite')\nconn.execute('SELECT 1')\n",
        encoding="utf-8",
    )

    report = check_release_readiness(
        reference_paths=[],
        required_paths=[],
        risks_path=None,
        sql_execution_paths=[bad_path],
    )

    assert not report.ok
    assert {issue.code for issue in report.issues} == {
        "DIRECT_SQLITE_CONNECTION",
        "DIRECT_SQL_EXECUTE",
    }
    assert report.checked["sql_execution_path_issues"] == 2


def test_parse_dual_policy_pair_requires_explicit_mapping():
    benchmark, dual = parse_dual_policy_pair("results/run=results/dual")

    assert benchmark == Path("results/run")
    assert dual == Path("results/dual")
