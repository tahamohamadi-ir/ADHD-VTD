from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.config.settings import SETTINGS
from src.graph.nodes import base_nodes
from src.graph.nodes.base_nodes import (
    _default_generation_model_path,
    execute_sql,
    initialize_trace,
    validate_sql,
)
from src.graph.routes import route_after_validation
from src.graph.state import VTDState


def _state(**updates):
    data = {"trace_id": "t", "raw_question": "test"}
    data.update(updates)
    return VTDState(**data)


def test_initialize_trace_uses_configured_max_retries():
    result = initialize_trace(_state(trace_id="existing", retry_count=2, max_retries=99))

    assert result["trace_id"] == "existing"
    assert result["retry_count"] == 0
    assert result["max_retries"] == SETTINGS.max_retries


def test_validate_sql_increments_retry_count_on_failure():
    state = _state(generated_sql="DROP TABLE student_depression", retry_count=0, max_retries=3)

    result = validate_sql(state)

    assert result["retry_count"] == 1
    assert result["validation_errors"]
    assert result["attempts"][0].validation_passed is False


def test_route_after_validation_stops_at_max_retries_after_increment():
    state = _state(
        generated_sql="DROP TABLE student_depression",
        retry_count=2,
        max_retries=3,
    )
    updates = validate_sql(state)
    next_state = state.model_copy(update=updates)

    assert next_state.retry_count == 3
    assert route_after_validation(next_state) == "fail_gracefully"


def test_execute_sql_increments_retry_count_on_execution_failure():
    state = _state(
        generated_sql="SELECT missing_column FROM student_depression LIMIT 1",
        retry_count=0,
        max_retries=3,
    )

    result = execute_sql(state)

    assert result["retry_count"] == 1
    assert result["execution_error"]


def test_default_generation_model_path_uses_settings(monkeypatch):
    monkeypatch.setattr(
        base_nodes,
        "SETTINGS",
        SimpleNamespace(default_model_path="custom/model.gguf"),
    )

    assert _default_generation_model_path() == "custom/model.gguf"


def test_default_generation_model_path_has_project_default(monkeypatch):
    monkeypatch.setattr(base_nodes, "SETTINGS", SimpleNamespace(default_model_path=None))

    assert Path(_default_generation_model_path()).name == "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
