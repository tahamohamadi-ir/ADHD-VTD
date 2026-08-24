from __future__ import annotations

from src.core.query_ir import QueryIR
from src.schema.schema_registry import SchemaRegistry
from src.sql_validation.shape_rewriter import rewrite_analytical_shape
from src.sql_validation.shape_validator import SQLShapeValidator
from src.sql_validation.validation_result import ValidationIssue


def _schema(*tables: str) -> dict:
    registry = SchemaRegistry()
    return {table: registry.tables[table] for table in tables}


def _issue(code: str) -> ValidationIssue:
    return ValidationIssue(code=code, message=code)


def test_shape_rewriter_repairs_single_sided_binary_comparison_to_grouped_count():
    qir = QueryIR(
        task_type="comparison_query",
        dimensions=["depression_flag"],
        metrics=["count"],
        expected_result_shape="table",
    )

    result = rewrite_analytical_shape(
        "SELECT COUNT(*) AS total FROM student_depression WHERE depression_flag = 0",
        question="compare depressed and non-depressed students",
        qir=qir,
        schema=_schema("student_depression"),
        issues=[
            _issue("ANALYTICAL_SHAPE_MISSING_GROUP_BY"),
            _issue("ANALYTICAL_SHAPE_SINGLE_SIDED_COMPARISON"),
        ],
    )

    assert result.rewritten
    assert "GROUP BY depression_flag" in result.sql
    assert "depression_flag = 0" not in result.sql
    assert "depression_flag IS NOT NULL" in result.sql
    assert (
        SQLShapeValidator()
        .validate(
            result.sql,
            question="compare depressed and non-depressed students",
            qir=qir,
            schema=_schema("student_depression"),
        )
        .ok
    )


def test_shape_rewriter_repairs_grouped_rate_from_count_only_sql():
    qir = QueryIR(
        task_type="rate_query",
        dimensions=["gender"],
        metrics=["depression_flag"],
        expected_result_shape="table",
    )

    result = rewrite_analytical_shape(
        "SELECT gender, COUNT(*) AS count FROM student_depression GROUP BY gender",
        question="depression rate by gender",
        qir=qir,
        schema=_schema("student_depression"),
        issues=[_issue("ANALYTICAL_SHAPE_MISSING_RATE_FORMULA")],
    )

    assert result.rewritten
    assert "SUM(depression_flag) AS positives" in result.sql
    assert "ROUND(100.0 * SUM(depression_flag) / COUNT(*), 2) AS rate_pct" in result.sql
    assert "GROUP BY gender" in result.sql
    assert (
        SQLShapeValidator()
        .validate(
            result.sql,
            question="depression rate by gender",
            qir=qir,
            schema=_schema("student_depression"),
        )
        .ok
    )


def test_shape_rewriter_repairs_multi_dimension_grouping_shape():
    qir = QueryIR(
        task_type="grouping_query",
        dimensions=["sleep_duration_category", "dietary_habits"],
        metrics=["depression_flag"],
        expected_result_shape="table",
    )

    result = rewrite_analytical_shape(
        "SELECT sleep_duration_category, COUNT(*) AS count FROM student_depression GROUP BY sleep_duration_category",
        question="sleep and diet combination matrix",
        qir=qir,
        schema=_schema("student_depression"),
        issues=[_issue("ANALYTICAL_SHAPE_MISSING_MULTI_DIMENSION_GROUPING")],
    )

    assert result.rewritten
    assert "GROUP BY sleep_duration_category, dietary_habits" in result.sql
    assert "sleep_duration_category IS NOT NULL" in result.sql
    assert "dietary_habits IS NOT NULL" in result.sql


def test_shape_rewriter_skips_complex_sql_without_guessing():
    qir = QueryIR(task_type="grouping_query", dimensions=["gender"], expected_result_shape="table")

    result = rewrite_analytical_shape(
        "SELECT gender, COUNT(*) FROM a JOIN b ON a.id = b.id GROUP BY gender",
        question="count by gender",
        qir=qir,
        schema=_schema("student_depression"),
        issues=[_issue("ANALYTICAL_SHAPE_MISSING_GROUP_BY")],
    )

    assert not result.rewritten
    assert "not_single_table_select" in result.action
