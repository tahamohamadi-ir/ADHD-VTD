from __future__ import annotations

from pathlib import Path

from src.evaluation.dataset_loader import read_json, read_jsonl, write_jsonl
from src.evaluation.reliability_gate_analysis import analyze_reliability_gate_artifact


def test_analyze_reliability_gate_artifact_reports_posthoc_risk_without_relabeling(tmp_path):
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    write_jsonl(
        artifact / "run_predictions.jsonl",
        [
            {
                "id": "ok",
                "actual_action": "format_answer",
                "execution_correct": True,
                "valid_sql": True,
                "error": "",
                "reliability_gate_action": "answer",
                "reliability_gate_reason": "validated_executed_sql",
                "multi_candidate_policy": {
                    "enabled": False,
                    "candidate_count": 1,
                    "triggers": [],
                },
            },
            {
                "id": "mismatch",
                "actual_action": "format_answer",
                "execution_correct": False,
                "valid_sql": True,
                "error": "RESULT_MISMATCH",
                "reliability_gate_action": "answer",
                "reliability_gate_reason": "validated_executed_sql",
                "reliability_gate_warnings": ["strict_reference_mismatch"],
                "multi_candidate_policy": {
                    "enabled": True,
                    "candidate_count": 2,
                    "triggers": ["retry_in_progress", "validation_failed"],
                },
            },
            {
                "id": "invalid",
                "actual_action": "ask_clarification",
                "execution_correct": False,
                "valid_sql": False,
                "error": "INVALID_SQL",
                "reliability_gate_action": "needs_review",
                "reliability_gate_reason": "validation_failed_exhausted",
            },
        ],
    )

    paths = analyze_reliability_gate_artifact(artifact, output_dir=tmp_path / "analysis")

    summary = read_json(paths["summary"])
    cases = {row["case_id"]: row for row in read_jsonl(paths["cases"])}
    report = Path(paths["report"]).read_text(encoding="utf-8")

    assert summary["action_counts"] == {"answer": 2, "needs_review": 1}
    assert summary["multi_candidate_counts"] == {"disabled": 2, "enabled": 1}
    assert summary["multi_candidate_trigger_counts"] == {
        "retry_in_progress": 1,
        "validation_failed": 1,
    }
    assert summary["warning_counts"] == {"strict_reference_mismatch": 1}
    assert summary["posthoc_risk_counts"] == {
        "answer_on_correct": 1,
        "answer_on_valid_result_mismatch": 1,
        "review_or_clarify_on_incorrect": 1,
    }
    assert cases["mismatch"]["posthoc_gate_risk"] == "answer_on_valid_result_mismatch"
    assert cases["mismatch"]["reliability_gate_warnings"] == ["strict_reference_mismatch"]
    assert cases["mismatch"]["multi_candidate_enabled"] is True
    assert "do not alter benchmark outcomes" in report


def test_analyze_reliability_gate_artifact_can_recompute_gate_without_relabeling(tmp_path):
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    write_jsonl(
        artifact / "run_predictions.jsonl",
        [
            {
                "id": "risk-summary-missing-context",
                "question": "Show risks for people with stress above average and sleep below average.",
                "generated_sql": "SELECT mental_health_risk, COUNT(*) AS n "
                "FROM mental_health_general "
                "WHERE stress_level > (SELECT AVG(stress_level) FROM mental_health_general) "
                "AND sleep_hours < (SELECT AVG(sleep_hours) FROM mental_health_general) "
                "GROUP BY mental_health_risk",
                "result_hash": "runtime-result-hash",
                "execution_correct": False,
                "valid_sql": True,
                "error": "RESULT_MISMATCH",
                "retry_count": 3,
                "max_retries": 3,
                "reliability_gate_action": "answer",
                "reliability_gate_reason": "validated_executed_sql",
            }
        ],
    )

    paths = analyze_reliability_gate_artifact(
        artifact,
        output_dir=tmp_path / "analysis",
        recompute_gate=True,
    )

    summary = read_json(paths["summary"])
    cases = {row["case_id"]: row for row in read_jsonl(paths["cases"])}

    assert summary["analysis_mode"] == "recomputed_runtime_gate"
    assert summary["action_counts"] == {"needs_review": 1}
    assert cases["risk-summary-missing-context"]["reliability_gate_source"] == "recomputed"
    assert (
        cases["risk-summary-missing-context"]["reliability_gate_reason"]
        == "consistency_failed_exhausted"
    )
    assert (
        cases["risk-summary-missing-context"]["posthoc_gate_risk"]
        == "review_or_clarify_on_incorrect"
    )
