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


class RaisingWorkflow(MockWorkflow):
    def invoke(self, state: dict) -> dict:
        if "overflow" in state.get("raw_question", ""):
            raise ValueError("Requested tokens (2214) exceed context window of 2048")
        return super().invoke(state)


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
            exclude_self=True,
            trace_level="full",
        )
    )

    config_path = next(output_dir.glob("*_config.json"))
    predictions_path = next(output_dir.glob("*_predictions.jsonl"))
    attempts_path = next(output_dir.glob("*_attempts.jsonl"))
    partial_predictions_path = next(output_dir.glob("*_partial_predictions.jsonl"))
    partial_attempts_path = next(output_dir.glob("*_partial_attempts.jsonl"))
    summary_json_path = next(output_dir.glob("*_summary.json"))
    summary_md_path = next(output_dir.glob("*_summary.md"))

    config = json.loads(config_path.read_text(encoding="utf-8"))
    predictions = _read_jsonl(predictions_path)
    attempts = _read_jsonl(attempts_path)
    partial_predictions = _read_jsonl(partial_predictions_path)
    partial_attempts = _read_jsonl(partial_attempts_path)
    summary = json.loads(summary_json_path.read_text(encoding="utf-8"))
    summary_md = summary_md_path.read_text(encoding="utf-8")

    assert config["model_slug"] == "mock_model"
    assert config["ablation_id"] == "A_trace"
    assert config["enabled_modules"] == ["nlu"]
    assert sorted(config["disabled_modules"]) == ["cag", "reflexion"]
    assert config["dataset_hash"]
    assert config["selected_cases_hash"]
    assert config["difficulty_counts"] == {"easy": 1}
    assert config["retrieval_backend"] == "bm25"
    assert config["max_retries"] >= 0
    assert config["prompt_template"]["generation"].endswith("sql_generation.j2")
    assert config["trace_level"] == "full"
    assert config["exclude_self"] is True
    assert config["retrieval_self_overlap_policy"]["enabled"] is True

    assert len(predictions) == 1
    assert predictions[0]["id"] == "MOCK-001"
    assert predictions[0]["generated_sql"] == "SELECT 1 AS n"
    assert predictions[0]["execution_correct"] is True
    assert predictions[0]["validation_issues"] == []
    assert predictions[0]["exclude_self_retrieval"] is True

    assert len(attempts) == 1
    assert attempts[0]["case_id"] == "MOCK-001"
    assert attempts[0]["prompt"] == "PROMPT: generate SELECT 1 AS n"
    assert attempts[0]["raw_model_response"] == '{"sql":"SELECT 1 AS n","explanation":"ok"}'
    assert attempts[0]["sql"] == "SELECT 1 AS n"
    assert partial_predictions == predictions
    assert partial_attempts == attempts

    assert summary["config"]["model_name"] == "mock-model"
    assert summary["dataset"]["total_evaluated"] == 1
    assert "execution_accuracy" in summary["metrics"]
    assert "mock_model" in summary_md


def test_agent_error_classification_distinguishes_sql_failures(monkeypatch):
    project_root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(project_root / "scripts"))

    import run_benchmark  # type: ignore

    assert run_benchmark.classify_agent_error(
        expected_action="generate_sql",
        actual_action="ask_clarification",
        generated_sql="SELECT ...",
        gold_sql="SELECT 1",
        valid_sql=False,
        execution_correct=False,
        final_state={},
    ) == "INVALID_SQL"

    assert run_benchmark.classify_agent_error(
        expected_action="generate_sql",
        actual_action="format_answer",
        generated_sql="SELECT COUNT(*) FROM student_depression",
        gold_sql="SELECT AVG(depression_flag) FROM student_depression",
        valid_sql=True,
        execution_correct=False,
        final_state={},
    ) == "RESULT_MISMATCH"

    assert run_benchmark.classify_agent_error(
        expected_action="safety_refusal",
        actual_action="format_answer",
        generated_sql="SELECT 1",
        gold_sql=None,
        valid_sql=True,
        execution_correct=False,
        final_state={},
    ) == "ACTION_MISMATCH"


def test_agent_benchmark_records_per_case_exception(tmp_path, monkeypatch):
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
                        "id": "MOCK-OK",
                        "question_fa": "ok case",
                        "difficulty": "easy",
                        "category": "smoke",
                        "sql": "SELECT 1 AS n",
                        "expected_action": "generate_sql",
                        "should_generate_sql": True,
                    },
                    {
                        "id": "MOCK-OVERFLOW",
                        "question_fa": "overflow case",
                        "difficulty": "hard",
                        "category": "smoke",
                        "sql": "SELECT 1 AS n",
                        "expected_action": "generate_sql",
                        "should_generate_sql": True,
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(workflow_module, "create_workflow", lambda: RaisingWorkflow())
    monkeypatch.setattr(run_benchmark, "git_commit", lambda: "testsha")
    monkeypatch.setattr(run_benchmark, "get_model_name", lambda: "mock-model")
    monkeypatch.setattr(run_benchmark, "get_model_slug", lambda: "mock_model")
    monkeypatch.setattr(run_benchmark, "get_model_path", lambda: "models/mock.gguf")

    output_dir = run_benchmark.run(
        Namespace(
            mode="agent",
            dataset="dev",
            path=str(dataset_path),
            sample=2,
            samples_per_level=None,
            top_k=3,
            use_vector=False,
            config_id="mock_agent_exception",
            ablation_id="A_exception",
            output_dir=str(tmp_path / "benchmark_out"),
            config=None,
            seed=123,
            bootstrap_iterations=20,
            ablation_config={"nlu": True},
            exclude_self=False,
            trace_level="full",
        )
    )

    predictions_path = next(output_dir.glob("*_predictions.jsonl"))
    partial_predictions_path = next(output_dir.glob("*_partial_predictions.jsonl"))
    taxonomy_path = next(output_dir.glob("*_error_taxonomy.csv"))
    predictions = _read_jsonl(predictions_path)
    partial_predictions = _read_jsonl(partial_predictions_path)
    taxonomy = taxonomy_path.read_text(encoding="utf-8")

    assert len(predictions) == 2
    assert partial_predictions == predictions
    overflow = next(row for row in predictions if row["id"] == "MOCK-OVERFLOW")
    assert overflow["error"] == "MODEL_CONTEXT_OVERFLOW"
    assert overflow["exception_type"] == "ValueError"
    assert overflow["actual_action"] == "fail_gracefully"
    assert "MODEL_CONTEXT_OVERFLOW,1" in taxonomy


def test_self_overlap_detection_uses_base_id_and_normalized_question():
    project_root = Path(__file__).resolve().parents[2]
    import sys

    sys.path.insert(0, str(project_root))

    from src.retrieval.self_overlap import is_self_overlap_record, normalize_overlap_question

    assert is_self_overlap_record(
        {"id": "fs_VTD-001", "question_fa": "یک سوال دیگر"},
        case_id="VTD-001",
        question="متن فعلی",
    )
    assert is_self_overlap_record(
        {"id": "OTHER", "question_fa": "درصد دانشجویان افسرده چقدر است؟"},
        case_id="VTD-999",
        question="درصد دانشجویان افسرده چقدر است؟",
    )
    assert normalize_overlap_question("كدام  دانشجويان؟") == normalize_overlap_question("کدام دانشجویان")
