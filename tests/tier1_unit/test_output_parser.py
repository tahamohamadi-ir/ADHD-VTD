from __future__ import annotations

from src.generation.output_parser import OutputParser
from src.graph.nodes.base_nodes import parse_llm_output, validate_sql
from src.graph.state import VTDState


def test_output_parser_returns_none_for_non_json_non_sql_text():
    assert OutputParser.extract_json("I cannot answer this as JSON.") is None


def test_parse_llm_output_clears_generated_sql_on_invalid_json():
    state = VTDState(
        trace_id="trace",
        raw_question="تعداد دانشجوها را بده",
        prompt="PROMPT",
        generated_sql="this is not json and not sql",
        raw_model_response="this is not json and not sql",
    )

    updates = parse_llm_output(state)

    assert updates["generated_sql"] is None
    assert updates["parsed_payload"] is None
    assert updates["validation_errors"][0]["type"] == "OUTPUT_PARSE_ERROR"


def test_validate_sql_records_parse_failure_without_validating_raw_response():
    state = VTDState(
        trace_id="trace",
        raw_question="تعداد دانشجوها را بده",
        prompt="PROMPT",
        raw_model_response="DROP TABLE student_depression",
        generated_sql=None,
        validation_errors=[{"type": "OUTPUT_PARSE_ERROR", "message": "Invalid JSON format"}],
    )

    updates = validate_sql(state)

    assert updates["generated_sql"] is None
    assert updates["validation_errors"][0]["type"] == "OUTPUT_PARSE_ERROR"
    assert updates["attempts"][0].sql is None
    assert updates["attempts"][0].raw_model_response == "DROP TABLE student_depression"
    assert updates["attempts"][0].error_type == "OUTPUT_PARSE_ERROR"
