from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

from src.core.query_ir import QueryIR
from src.generation.output_parser import OutputParser

PROMPT_PATH = Path("src/generation/prompts/sql_generation_scalar.j2")


def _schema() -> dict[str, SimpleNamespace]:
    return {
        "student_depression": SimpleNamespace(
            columns=[
                SimpleNamespace(name="age", type="INTEGER"),
                SimpleNamespace(name="gender", type="TEXT"),
                SimpleNamespace(name="depression_flag", type="INTEGER"),
            ]
        )
    }


def test_scalar_prompt_renders_with_core_context():
    env = Environment(
        loader=FileSystemLoader("src/generation/prompts"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("sql_generation_scalar.j2")

    rendered = template.render(
        question="تعداد کل رکوردها چقدر است؟",
        qir=QueryIR(task_type="count_query"),
        schema=_schema(),
        value_links={},
        few_shot=[],
        analysis_hints=[],
    )

    assert "SCALAR" in rendered
    assert "student_depression" in rendered
    assert "depression_flag" in rendered
    assert '"shape": "scalar"' in rendered
    assert '"needs_clarification": false' in rendered


def test_scalar_prompt_contains_required_shape_constraints():
    content = PROMPT_PATH.read_text(encoding="utf-8")

    assert "exactly one SQL query" in content
    assert "return one row" in content
    assert "Do not use `GROUP BY`" in content
    assert "Do not add a `WHERE` clause unless the user explicitly requested" in content
    assert "COUNT(*)" in content
    assert "ROUND(AVG(column), 2)" in content
    assert "WHERE column IS NOT NULL" in content
    assert "SQLite only" in content


def test_scalar_prompt_contains_required_negative_examples():
    content = PROMPT_PATH.read_text(encoding="utf-8")

    assert "Hidden GROUP BY" in content
    assert "Hidden WHERE" in content
    assert "Wrong rate formula" in content
    assert "Forbidden join" in content
    assert "SELECT star" in content
    assert "GROUP BY depression_flag" in content
    assert "WHERE depression_flag = 1" in content
    assert "COUNT(depression_flag)" in content
    assert "JOIN mental_health_general" in content
    assert "SELECT *" in content


def test_scalar_prompt_output_schema_is_parser_compatible():
    parsed = OutputParser.extract_json("""
        {
          "shape": "scalar",
          "sql": "SELECT COUNT(*) AS total_records FROM student_depression;",
          "needs_clarification": false,
          "clarification_question": null,
          "assumptions": [],
          "rationale_short": "Single scalar count; no hidden grouping."
        }
        """)

    assert parsed is not None
    assert parsed["shape"] == "scalar"
    assert parsed["sql"].startswith("SELECT COUNT(*)")
    assert parsed["needs_clarification"] is False
