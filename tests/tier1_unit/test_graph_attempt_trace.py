from __future__ import annotations

from src.graph.nodes.base_nodes import execute_sql, validate_sql
from src.graph.state import VTDState


def _state(**updates):
    data = {
        "trace_id": "trace",
        "raw_question": "تعداد دانشجوها را بده",
        "prompt": "PROMPT TEXT",
        "raw_model_response": '{"sql":"SELECT COUNT(*) FROM student_depression"}',
        "parsed_payload": {"sql": "SELECT COUNT(*) FROM student_depression"},
    }
    data.update(updates)
    return VTDState(**data)


def test_validate_sql_records_prompt_and_raw_model_response_in_attempt():
    result = validate_sql(_state(generated_sql="SELECT COUNT(*) FROM student_depression"))

    attempt = result["attempts"][0]
    assert attempt.prompt == "PROMPT TEXT"
    assert attempt.raw_model_response == '{"sql":"SELECT COUNT(*) FROM student_depression"}'
    assert attempt.parsed_payload == {"sql": "SELECT COUNT(*) FROM student_depression"}
    assert attempt.sql == "SELECT COUNT(*) FROM student_depression"


def test_execute_sql_records_result_hash_and_preview_on_latest_attempt():
    state = _state(generated_sql="SELECT COUNT(*) AS n FROM student_depression")
    validation_updates = validate_sql(state)
    state = state.model_copy(update=validation_updates)

    execution_updates = execute_sql(state)

    attempt = execution_updates["attempts"][-1]
    assert attempt.execution_passed is True
    assert attempt.execution_result_hash
    assert isinstance(attempt.execution_result_preview, list)
