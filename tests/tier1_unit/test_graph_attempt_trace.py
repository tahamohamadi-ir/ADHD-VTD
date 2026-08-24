from __future__ import annotations

from src.graph.nodes import base_nodes
from src.graph.nodes.base_nodes import execute_sql, generate_sql, validate_sql
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
    result = validate_sql(
        _state(generated_sql="SELECT COUNT(*) FROM student_depression", generation_latency_ms=1234)
    )

    attempt = result["attempts"][0]
    assert attempt.prompt == "PROMPT TEXT"
    assert attempt.raw_model_response == '{"sql":"SELECT COUNT(*) FROM student_depression"}'
    assert attempt.generation_latency_ms == 1234
    assert attempt.parsed_payload == {"sql": "SELECT COUNT(*) FROM student_depression"}
    assert attempt.sql == "SELECT COUNT(*) FROM student_depression"


def test_validate_sql_promotes_rewritten_sql_for_execution():
    result = validate_sql(
        _state(
            generated_sql=(
                "SELECT family_history, COUNT(*) AS count "
                "FROM student_depression GROUP BY family_history ORDER BY count DESC"
            )
        )
    )

    assert result["validation_errors"] == []
    assert "family_history_mental_illness" in result["generated_sql"]
    assert "family_history_mental_illness" in result["attempts"][0].sql


def test_generate_sql_uses_bounded_max_tokens(monkeypatch):
    class FakeLLM:
        kwargs = None

        def generate_json(self, prompt, **kwargs):
            self.kwargs = kwargs
            return '{"sql":"SELECT 1","explanation":"","needs_clarification":false}'

    fake = FakeLLM()
    monkeypatch.setenv("VTD_SQL_GENERATION_MAX_TOKENS", "123")
    monkeypatch.setattr(base_nodes, "_get_local_llm", lambda: fake)

    result = generate_sql(_state(prompt="PROMPT"))

    assert result["generation_latency_ms"] >= 0
    assert fake.kwargs["max_tokens"] == 123
    assert fake.kwargs["enforce_json"] is True
    assert result["generation_source"] == "llm"


def test_generate_sql_does_not_use_templates_by_default(monkeypatch):
    class FakeLLM:
        called = False

        def generate_json(self, prompt, **kwargs):
            self.called = True
            return '{"sql":"SELECT 1","explanation":"","needs_clarification":false}'

    fake = FakeLLM()
    monkeypatch.setattr(base_nodes, "_get_local_llm", lambda: fake)
    question = "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 \u0633\u0646 \u062f\u0631 \u062f\u06cc\u062a\u0627\u0633\u062a \u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u0627\u0646 \u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"

    result = generate_sql(_state(raw_question=question, prompt="PROMPT"))

    assert fake.called is True
    assert result["generation_source"] == "llm"


def test_generate_sql_uses_templates_only_when_ablation_enabled(monkeypatch):
    class ExplodingLLM:
        def generate_json(self, prompt, **kwargs):  # pragma: no cover - should not be called
            raise AssertionError("LLM should not be called when deterministic template matches")

    monkeypatch.setattr(base_nodes, "_get_local_llm", lambda: ExplodingLLM())
    question = "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 \u0633\u0646 \u062f\u0631 \u062f\u06cc\u062a\u0627\u0633\u062a \u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u0627\u0646 \u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"

    result = generate_sql(
        _state(
            raw_question=question,
            prompt="PROMPT",
            ablation_config={"deterministic_templates": True},
        )
    )

    assert result["generation_source"] == "deterministic_template"
    assert result["generation_latency_ms"] == 0


def test_execute_sql_records_result_hash_and_preview_on_latest_attempt():
    state = _state(generated_sql="SELECT COUNT(*) AS n FROM student_depression")
    validation_updates = validate_sql(state)
    state = state.model_copy(update=validation_updates)

    execution_updates = execute_sql(state)

    attempt = execution_updates["attempts"][-1]
    assert attempt.execution_passed is True
    assert attempt.execution_result_hash
    assert isinstance(attempt.execution_result_preview, list)
