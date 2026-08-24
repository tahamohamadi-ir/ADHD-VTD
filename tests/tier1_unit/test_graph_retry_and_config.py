from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.graph.nodes import base_nodes
from src.graph.nodes.base_nodes import (
    _default_generation_model_path,
    _schema_candidate_columns,
    build_prompt,
    execute_sql,
    initialize_trace,
    link_schema,
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
    assert result["max_retries"] == 99


def test_validate_sql_increments_retry_count_on_failure():
    state = _state(generated_sql="DROP TABLE student_depression", retry_count=0, max_retries=3)

    result = validate_sql(state)

    assert result["retry_count"] == 1
    assert result["validation_errors"]
    assert result["attempts"][0].validation_passed is False


def test_validate_sql_repairs_unknown_column_with_one_shot_surgeon():
    state = _state(
        raw_question="توزیع رژیم غذایی دانشجویان افسردگی را نشان بده.",
        generated_sql=(
            "SELECT diet_quality, COUNT(*) AS count FROM student_depression "
            "GROUP BY diet_quality ORDER BY count DESC"
        ),
        retry_count=0,
        max_retries=3,
    )

    result = validate_sql(state)

    assert result["generated_sql"]
    assert "dietary_habits" in result["generated_sql"]
    assert "diet_quality" not in result["generated_sql"]
    assert result["validation_errors"] == []
    assert "retry_count" not in result
    assert result["attempts"][0].validation_passed is True
    assert result["attempts"][0].repair_action == "schema_surgeon"
    assert "surgeon_patch_validated=true" in (result["attempts"][0].repair_plan or "")


def test_validate_sql_repairs_simple_shape_error_before_retry_loop():
    registry = base_nodes.SchemaRegistry()
    state = _state(
        raw_question="compare depressed and non-depressed students",
        generated_sql="SELECT COUNT(*) AS total FROM student_depression WHERE depression_flag = 0",
        retry_count=0,
        max_retries=3,
        qir=base_nodes.QueryIR(
            task_type="comparison_query",
            dimensions=["depression_flag"],
            metrics=["count"],
            expected_result_shape="table",
        ),
        schema_context={"student_depression": registry.tables["student_depression"]},
    )

    result = validate_sql(state)

    assert result["validation_errors"] == []
    assert "GROUP BY depression_flag" in result["generated_sql"]
    assert "depression_flag = 0" not in result["generated_sql"]
    assert "retry_count" not in result
    assert result["attempts"][0].validation_passed is True
    assert result["attempts"][0].repair_action == "shape_surgeon"
    assert "shape_surgeon_patch_validated=true" in (result["attempts"][0].repair_plan or "")


def test_validate_sql_keeps_one_retry_when_unknown_column_surgeon_has_no_mapping():
    state = _state(
        raw_question="توزیع ستون ناموجود را نشان بده.",
        generated_sql="SELECT hallucinated_metric FROM student_depression",
        retry_count=0,
        max_retries=3,
    )

    result = validate_sql(state)

    assert result["retry_count"] == 2
    assert result["validation_errors"]
    assert result["attempts"][0].validation_passed is False
    assert "surgeon_deferred_to_single_retry=true" in (result["attempts"][0].repair_plan or "")


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


def test_link_schema_uses_full_schema_when_schema_linking_disabled():
    result = link_schema(
        _state(
            normalized_question="average depression",
            ablation_config={"schema_linking": False},
        )
    )

    linked = result["linked_schema"]
    assert "schema_linking_disabled" in linked.unresolved_terms
    assert linked.confidence == 0.0
    assert len(result["schema_context"]) > 1


def test_build_prompt_includes_value_links_when_enabled():
    schema_result = link_schema(
        _state(
            normalized_question="میانگین فشار تحصیلی برای دانشجویان دختر چقدر است؟",
        )
    )
    state = _state(
        raw_question="میانگین فشار تحصیلی برای دانشجویان دختر چقدر است؟",
        normalized_question="میانگین فشار تحصیلی برای دانشجویان دختر چقدر است؟",
        qir=base_nodes.QueryIR(task_type="aggregation_query"),
        schema_context=schema_result["schema_context"],
        ablation_config={"value_linking": True},
    )

    result = build_prompt(state)

    assert result["value_links"]
    assert any(value == "Female" for value in result["value_links"].values())
    assert "Female" in result["prompt"]


def test_build_prompt_omits_value_links_when_disabled():
    schema_result = link_schema(
        _state(
            normalized_question="میانگین فشار تحصیلی برای دانشجویان دختر چقدر است؟",
        )
    )
    state = _state(
        raw_question="میانگین فشار تحصیلی برای دانشجویان دختر چقدر است؟",
        normalized_question="میانگین فشار تحصیلی برای دانشجویان دختر چقدر است؟",
        qir=base_nodes.QueryIR(task_type="aggregation_query"),
        schema_context=schema_result["schema_context"],
        ablation_config={"value_linking": False},
    )

    result = build_prompt(state)

    assert result["value_links"] == {}


def test_schema_candidate_columns_supports_dict_style_schema_context():
    schema_context = {
        "student_depression": {
            "columns": [
                {"name": "depression_flag"},
                {"name": "sleep_duration_category"},
                "dietary_habits",
            ]
        }
    }

    assert _schema_candidate_columns(schema_context) == [
        "student_depression.depression_flag",
        "student_depression.sleep_duration_category",
        "student_depression.dietary_habits",
    ]


def test_build_prompt_limits_value_links_to_schema_context_columns():
    state = _state(
        raw_question="Build a sleep and diet matrix for depressed students and CGPA.",
        normalized_question="Build a sleep and diet matrix for depressed students and cgpa.",
        qir=base_nodes.QueryIR(task_type="grouping_query"),
        schema_context={
            "student_depression": {
                "columns": [
                    {"name": "depression_flag"},
                    {"name": "sleep_duration_category"},
                    {"name": "dietary_habits"},
                    {"name": "cgpa_10"},
                ]
            }
        },
        ablation_config={"value_linking": True},
    )

    result = build_prompt(state)

    assert result["value_links"]
    assert any("student_depression.depression_flag" in key for key in result["value_links"])
    assert not any("workplace_mental_health_survey" in key for key in result["value_links"])
