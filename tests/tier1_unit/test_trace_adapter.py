from __future__ import annotations

from src.evaluation.trace_adapter import (
    attempt_trace_from_benchmark,
    prediction_record_from_benchmark,
    validate_benchmark_trace_contract,
)


def test_prediction_record_from_agent_benchmark_record_validates():
    record = {
        "id": "VTD-1",
        "question_fa": "تعداد دانشجوها را بده",
        "actual_action": "format_answer",
        "normalized_question": "تعداد دانشجوها را بده",
        "qir": {"task_type": "count"},
        "linked_schema": {"tables": ["student_depression"], "columns": []},
        "value_links": {},
        "retrieved_examples": [{"id": "fs_1"}],
        "retrieval_diagnostics": [{"stage": "bm25"}],
        "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
        "gold_sql": "SELECT COUNT(*) AS n FROM student_depression",
        "execution_correct": True,
        "valid_sql": True,
        "latency_ms": 12,
        "reliability_gate": {
            "action": "answer",
            "reason": "validated_executed_sql",
            "confidence": 0.9,
            "warnings": [],
            "signals": {"valid_sql": True},
        },
    }

    parsed = prediction_record_from_benchmark(record)

    assert parsed.item_id == "VTD-1"
    assert parsed.final_action == "format_answer"
    assert parsed.retrieval is not None
    assert parsed.retrieval.retrieved_ids == ["fs_1"]
    assert parsed.reliability is not None
    assert parsed.reliability.action == "answer"


def test_attempt_trace_from_flattened_attempt_validates_sql_field():
    attempt = {
        "case_id": "VTD-1",
        "attempt_index": 0,
        "prompt": "PROMPT",
        "raw_model_response": '{"sql":"SELECT 1"}',
        "parsed_payload": {"sql": "SELECT 1"},
        "sql": "SELECT 1",
        "parsed": True,
        "validation_errors": [],
        "execution_passed": True,
        "latency_ms": 3,
    }

    parsed = attempt_trace_from_benchmark(attempt, default_ablation_id="A1")

    assert parsed.item_id == "VTD-1"
    assert parsed.iteration == 0
    assert parsed.ablation_id == "A1"
    assert parsed.generated_sql == "SELECT 1"


def test_validate_benchmark_trace_contract_counts_records():
    summary = validate_benchmark_trace_contract(
        [
            {
                "id": "VTD-1",
                "question": "q",
                "actual_action": "retrieve_context",
                "latency_ms": 1,
            }
        ],
        [
            {
                "case_id": "VTD-1",
                "attempt_index": 0,
                "sql": None,
                "validation_errors": [{"type": "OUTPUT_PARSE_ERROR"}],
            }
        ],
        default_ablation_id="A0",
    )

    assert summary == {"predictions": 1, "attempts": 1}
