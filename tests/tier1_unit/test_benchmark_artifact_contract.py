from __future__ import annotations

import sys
from pathlib import Path

from src.evaluation.dataset_loader import write_jsonl
from src.evaluation.export_utils import export_benchmark_csvs, generate_paper_tables
from src.evaluation.trace_adapter import validate_benchmark_trace_contract

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from scripts.run_benchmark import agent_prediction, build_artifact_manifest, exception_prediction


def test_prefixed_benchmark_csv_artifacts_are_written(tmp_path):
    records = [{"id": "VTD-1", "ok": True, "latency_ms": 12}]
    summary = {
        "config": {
            "model_name": "model-a",
            "model_slug": "model_a",
            "ablation_id": "A7",
            "enabled_modules": ["nlu"],
            "disabled_modules": ["reflexion"],
            "dataset": "dev",
            "dataset_hash": "dataset-hash",
            "selected_cases_hash": "selected-cases-hash",
            "selection_policy": "samples_per_level",
        },
        "artifacts": {
            "summary_json": str(tmp_path / "stamp_model_A7_summary.json"),
            "predictions": str(tmp_path / "stamp_model_A7_predictions.jsonl"),
        },
        "reliability": {"normalized_score": 1.0},
        "error_analysis": {"by_error": {}},
        "latency": {"median_ms": 12},
        "metrics": {"execution_accuracy": {"value": 1.0, "description": "EX"}},
    }

    export_benchmark_csvs(records, summary, tmp_path, prefix="stamp_model_A7")
    generate_paper_tables(summary, tmp_path / "stamp_model_A7_paper_tables.md")
    write_jsonl(tmp_path / "stamp_model_A7_attempts.jsonl", [])
    trace_contract = validate_benchmark_trace_contract(records, [], default_ablation_id="A7")

    assert (tmp_path / "stamp_model_A7_benchmark_results.csv").exists()
    assert (tmp_path / "stamp_model_A7_reliability_summary.csv").exists()
    assert (tmp_path / "stamp_model_A7_error_taxonomy.csv").exists()
    assert (tmp_path / "stamp_model_A7_attempts.jsonl").exists()
    assert (
        (tmp_path / "stamp_model_A7_error_taxonomy.csv")
        .read_text(encoding="utf-8-sig")
        .startswith("error_type,count")
    )
    paper_tables = (tmp_path / "stamp_model_A7_paper_tables.md").read_text(encoding="utf-8")
    assert "model_name" in paper_tables
    assert "A7" in paper_tables
    assert "dataset_hash" in paper_tables
    assert "selected-cases-hash" in paper_tables
    assert "Artifact Provenance" in paper_tables
    assert trace_contract == {"predictions": 1, "attempts": 0}


def test_benchmark_artifact_manifest_records_completed_run_identity(tmp_path):
    output_dir = tmp_path / "phase7_promptdiverse_adopt_spl5"
    summary = {
        "config": {
            "config_id": "phase7_promptdiverse_adopt_spl5",
            "ablation_id": "phase7_promptdiverse_adopt_spl5",
            "mode": "agent",
            "dataset": "positive400",
            "dataset_hash": "dataset-hash",
            "selected_cases_hash": "selected-cases-hash",
            "model_name": "qwen",
            "model_path": "models/generation/model.gguf",
            "model_slug": "qwen",
            "prompt_template": {"generation": "src/generation/prompts/sql_generation.j2"},
            "module_flags": {"deterministic_templates": False},
            "git_commit": "abc123",
            "started_at": "2026-06-27T00:00:00+00:00",
            "finished_at": "2026-06-27T00:01:00+00:00",
        },
        "metrics": {
            "execution_accuracy": {
                "value": 0.25,
                "numerator": 1,
                "denominator": 4,
            }
        },
    }
    artifact_paths = {
        "summary_json": output_dir / "run_summary.json",
        "predictions": output_dir / "run_predictions.jsonl",
        "manifest": output_dir / "run_artifact_manifest.json",
    }

    manifest = build_artifact_manifest(output_dir, summary, artifact_paths)
    entry = manifest["completed"]["phase7_promptdiverse_adopt_spl5"]

    assert manifest["schema_version"] == "pars_sql_benchmark_artifact_manifest_v1"
    assert entry["result_status"] == "completed"
    assert entry["artifact_dir"] == str(output_dir)
    assert entry["dataset_hash"] == "dataset-hash"
    assert entry["selected_cases_hash"] == "selected-cases-hash"
    assert entry["deterministic_templates"] is False
    assert entry["artifacts"]["predictions"] == str(output_dir / "run_predictions.jsonl")
    assert entry["metrics"]["execution_accuracy"] == {
        "value": 0.25,
        "numerator": 1,
        "denominator": 4,
    }


def test_exception_prediction_preserves_action_contract_fields():
    record = exception_prediction(
        {
            "id": "VTD-EVAL-099",
            "expected_action": "answer_with_sql_optional_explanation",
            "should_generate_sql": True,
        },
        RuntimeError("Requested tokens exceed context window"),
        latency_ms=12,
    )

    assert record["expected_action_normalized"] == "generate_sql"
    assert record["actual_action_normalized"] == "controlled_failure"
    assert record["action_correct"] is False
    assert record["error"] == "MODEL_CONTEXT_OVERFLOW"


def test_agent_prediction_exports_component_timing_traces():
    class _Workflow:
        def invoke(self, state: dict) -> dict:
            return {
                **state,
                "generated_sql": "SELECT 1 AS n",
                "validation_errors": [],
                "execution_error": None,
                "execution_result": [{"n": 1}],
                "final_answer": "analysis complete",
                "reliability_decision": {
                    "action": "answer",
                    "reason": "validated_executed_sql",
                    "confidence": 0.95,
                    "warnings": [],
                    "signals": {"generated_sql": True},
                    "latency_ms": 4,
                },
                "multi_candidate_generation_budget": {
                    "configured_budget_ms": 60000,
                    "requested_candidate_count": 2,
                    "generated_candidate_count": 1,
                    "budget_exhausted": True,
                },
                "attempts": [
                    {
                        "iteration": 0,
                        "sql": "SELECT 1 AS n",
                        "parsed": True,
                        "validation_passed": True,
                        "execution_passed": True,
                        "validation_errors": [],
                        "latency_ms": 1,
                    }
                ],
            }

    class _Executor:
        def compare_results(self, _generated_sql: str, _gold_sql: str) -> dict:
            return {"match": True, "generated_hash": "hash", "gold_hash": "hash"}

    record = agent_prediction(
        {
            "id": "VTD-TIMING-001",
            "question": "count",
            "sql": "SELECT 1 AS n",
            "expected_action": "generate_sql",
            "should_generate_sql": True,
        },
        _Workflow(),
        _Executor(),
        ablation_config={"reliability_gate": True},
    )

    assert record["graph_reliability_gate_latency_ms"] == 4
    assert record["reliability_decision"]["latency_ms"] == 4
    assert record["multi_candidate_generation_budget"] == {
        "configured_budget_ms": 60000,
        "requested_candidate_count": 2,
        "generated_candidate_count": 1,
        "budget_exhausted": True,
    }
    assert record["reliability_gate_latency_ms"] >= 0
    assert record["reliability_gate"]["latency_ms"] == record["reliability_gate_latency_ms"]
