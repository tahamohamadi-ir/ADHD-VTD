from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path


class MockWorkflow:
    def invoke(self, state: dict) -> dict:
        return {
            **state,
            "normalized_question": "تعداد نمونه را بده",
            "intent": "count_query",
            "qir": {"task_type": "count"},
            "linked_schema": {"tables": [], "columns": [], "confidence": 1.0},
            "retrieved_examples": [],
            "retrieval_diagnostics": [],
            "prompt": "PROMPT: generate SELECT 1 AS n",
            "raw_model_response": '{"sql":"SELECT 1 AS n","explanation":"ok"}',
            "parsed_payload": {"sql": "SELECT 1 AS n", "explanation": "ok"},
            "generated_sql": "SELECT 1 AS n",
            "validation_errors": [],
            "execution_error": None,
            "explanation": "ok",
            "final_answer": "تحلیل انجام شد. ok",
            "retry_count": 0,
            "attempts": [
                {
                    "iteration": 0,
                    "prompt": "PROMPT: generate SELECT 1 AS n",
                    "raw_model_response": '{"sql":"SELECT 1 AS n","explanation":"ok"}',
                    "parsed_payload": {"sql": "SELECT 1 AS n", "explanation": "ok"},
                    "sql": "SELECT 1 AS n",
                    "parsed": True,
                    "validation_passed": True,
                    "execution_passed": True,
                    "validation_errors": [],
                    "execution_result_preview": [{"n": 1}],
                    "execution_result_hash": "mock-hash",
                    "latency_ms": 1,
                }
            ],
        }


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_mocked_agent_benchmark_writes_trace_artifacts(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(project_root / "scripts"))

    import run_benchmark  # type: ignore
    import src.graph.workflow as workflow_module

    dataset_path = tmp_path / "mock_agent_dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "MOCK-001",
                        "question_fa": "تعداد نمونه را بده",
                        "difficulty": "easy",
                        "category": "smoke",
                        "sql": "SELECT 1 AS n",
                        "expected_action": "generate_sql",
                        "should_generate_sql": True,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(workflow_module, "create_workflow", lambda: MockWorkflow())
    monkeypatch.setattr(run_benchmark, "git_commit", lambda: "testsha")
    monkeypatch.setattr(run_benchmark, "get_model_name", lambda: "mock-model")
    monkeypatch.setattr(run_benchmark, "get_model_slug", lambda: "mock_model")
    monkeypatch.setattr(run_benchmark, "get_model_path", lambda: "models/mock.gguf")

    output_dir = run_benchmark.run(
        Namespace(
            mode="agent",
            dataset="dev",
            path=str(dataset_path),
            sample=1,
            samples_per_level=None,
            top_k=3,
            use_vector=False,
            config_id="mock_agent_trace",
            ablation_id="A_trace",
            output_dir=str(tmp_path / "benchmark_out"),
            config=None,
            seed=123,
            bootstrap_iterations=20,
            ablation_config={"nlu": True, "cag": False, "reflexion": False},
        )
    )

    config_path = next(output_dir.glob("*_config.json"))
    predictions_path = next(output_dir.glob("*_predictions.jsonl"))
    attempts_path = next(output_dir.glob("*_attempts.jsonl"))
    summary_json_path = next(output_dir.glob("*_summary.json"))
    summary_md_path = next(output_dir.glob("*_summary.md"))

    config = json.loads(config_path.read_text(encoding="utf-8"))
    predictions = _read_jsonl(predictions_path)
    attempts = _read_jsonl(attempts_path)
    summary = json.loads(summary_json_path.read_text(encoding="utf-8"))
    summary_md = summary_md_path.read_text(encoding="utf-8")

    assert config["model_slug"] == "mock_model"
    assert config["ablation_id"] == "A_trace"
    assert config["enabled_modules"] == ["nlu"]
    assert sorted(config["disabled_modules"]) == ["cag", "reflexion"]

    assert len(predictions) == 1
    assert predictions[0]["id"] == "MOCK-001"
    assert predictions[0]["generated_sql"] == "SELECT 1 AS n"
    assert predictions[0]["execution_correct"] is True

    assert len(attempts) == 1
    assert attempts[0]["case_id"] == "MOCK-001"
    assert attempts[0]["prompt"] == "PROMPT: generate SELECT 1 AS n"
    assert attempts[0]["raw_model_response"] == '{"sql":"SELECT 1 AS n","explanation":"ok"}'
    assert attempts[0]["sql"] == "SELECT 1 AS n"

    assert summary["config"]["model_name"] == "mock-model"
    assert summary["dataset"]["total_evaluated"] == 1
    assert "execution_accuracy" in summary["metrics"]
    assert "mock_model" in summary_md
