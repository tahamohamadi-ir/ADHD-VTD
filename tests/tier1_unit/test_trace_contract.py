from __future__ import annotations

from src.core.trace import AttemptTrace, PredictionRecord, ReliabilityTrace, RetrievalTrace


def test_attempt_trace_contract_accepts_parse_failure_record():
    attempt = AttemptTrace(
        item_id="VTD-1",
        iteration=0,
        ablation_id="A1",
        prompt="PROMPT",
        raw_model_response="not json",
        parsed=False,
        generated_sql=None,
        validation_errors=[{"type": "OUTPUT_PARSE_ERROR", "message": "Invalid JSON format"}],
    )

    assert attempt.generated_sql is None
    assert attempt.validation_errors[0]["type"] == "OUTPUT_PARSE_ERROR"


def test_prediction_record_contract_keeps_behavioral_final_action():
    record = PredictionRecord(
        item_id="VTD-EVAL-1",
        question_fa="این سوال مبهم است",
        final_action="ask_clarification",
        valid_sql=None,
        execution_correct=None,
        latency_ms=5,
        retrieval=RetrievalTrace(retrieved_ids=[]),
        reliability=ReliabilityTrace(action="ask_clarification", reason="ambiguous"),
    )

    assert record.final_action == "ask_clarification"
    assert record.reliability is not None
    assert record.execution_correct is None
