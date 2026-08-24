from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

from src.core.query_ir import QueryIR
from src.generation.output_parser import OutputParser
from src.generation.prompt_builder import PromptBuilder

GROUPED_PROMPT_PATH = Path("src/generation/prompts/sql_generation_grouped.j2")


def _schema() -> dict[str, SimpleNamespace]:
    return {
        "student_depression": SimpleNamespace(
            columns=[
                SimpleNamespace(name="gender", type="TEXT"),
                SimpleNamespace(name="depression_flag", type="INTEGER"),
                SimpleNamespace(name="sleep_duration_category", type="TEXT"),
            ]
        )
    }


def test_prompt_builder_routes_scalar_count_to_scalar_prompt():
    prompt = PromptBuilder().build_sql_generation_prompt(
        question="تعداد کل رکوردها چقدر است؟",
        qir=QueryIR(task_type="count_query"),
        schema=_schema(),
    )

    assert "This prompt is only for SCALAR questions" in prompt
    assert "Do not use `GROUP BY`" in prompt
    assert '"shape": "scalar"' in prompt


def test_prompt_builder_routes_grouped_dimensions_to_grouped_prompt():
    prompt = PromptBuilder().build_sql_generation_prompt(
        question="توزیع افسردگی بر اساس جنسیت",
        qir=QueryIR(
            task_type="grouping_query",
            dimensions=["gender"],
            metrics=["depression_flag"],
            expected_result_shape="table",
        ),
        schema=_schema(),
    )

    assert "This prompt is only for GROUPED questions" in prompt
    assert "GROUP BY must include every requested grouping dimension" in prompt
    assert "The QIR Dimensions are required output grouping keys" in prompt
    assert '"shape": "grouped"' in prompt


def test_prompt_builder_routes_ranking_to_generic_prompt_not_grouped_prompt():
    prompt = PromptBuilder().build_sql_generation_prompt(
        question="top genders by depression rate",
        qir=QueryIR(
            task_type="ranking_query",
            dimensions=["gender"],
            metrics=["depression_flag"],
            expected_result_shape="table",
        ),
        schema=_schema(),
    )

    assert "This prompt is only for GROUPED questions" not in prompt
    assert "For ranking questions" in prompt
    assert "ORDER BY on that metric" in prompt


def test_prompt_builder_routes_raw_rows_to_generic_prompt_not_grouped_prompt():
    prompt = PromptBuilder().build_sql_generation_prompt(
        question="show student records",
        qir=QueryIR(
            task_type="raw_retrieval_query",
            dimensions=["gender"],
            expected_result_shape="raw_rows",
        ),
        schema=_schema(),
    )

    assert "This prompt is only for GROUPED questions" not in prompt
    assert "For raw row/list requests" in prompt
    assert "LIMIT 100" in prompt


def test_grouped_prompt_contains_required_negative_examples():
    content = GROUPED_PROMPT_PATH.read_text(encoding="utf-8")

    assert "Scalar collapse" in content
    assert "Hidden WHERE" in content
    assert "Wrong rate formula" in content
    assert "Forbidden join" in content
    assert "SELECT star" in content
    assert "COUNT(depression_flag)" in content
    assert "JOIN mental_health_general" in content
    assert "SELECT *" in content


def test_grouped_prompt_renders_and_schema_is_parser_compatible():
    env = Environment(
        loader=FileSystemLoader("src/generation/prompts"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    rendered = env.get_template("sql_generation_grouped.j2").render(
        question="نرخ افسردگی به تفکیک جنسیت",
        qir=QueryIR(task_type="rate_query", dimensions=["gender"]),
        schema=_schema(),
        value_links={},
        few_shot=[],
        analysis_hints=["For grouped rate questions, return the group key and rate_pct."],
    )

    assert "student_depression" in rendered
    assert "rate_pct" in rendered
    parsed = OutputParser.extract_json("""
        {
          "shape": "grouped",
          "sql": "SELECT gender, COUNT(*) AS n FROM student_depression GROUP BY gender;",
          "needs_clarification": false,
          "clarification_question": null,
          "assumptions": [],
          "rationale_short": "Grouped count by gender."
        }
        """)

    assert parsed is not None
    assert parsed["shape"] == "grouped"
    assert "GROUP BY gender" in parsed["sql"]
