from types import SimpleNamespace

from src.graph.state import VTDState
from src.graph.nodes.sql_repair_helpers import (
    has_shape_errors,
    patch_column_name,
    sql_table_names,
    try_shape_surgeon,
    unknown_column_names,
)
from src.schema.schema_registry import SchemaRegistry
from src.sql_validation.validation_result import ValidationIssue, ValidationResult


class _PassingValidator:
    def __init__(self, *, registry):
        self.registry = registry

    def validate(self, sql):
        return ValidationResult.pass_(normalized_sql=sql)


class _PassingShapeValidator:
    def validate(self, *_args, **_kwargs):
        return ValidationResult.pass_()


class _FailingShapeValidator:
    def validate(self, *_args, **_kwargs):
        return ValidationResult.fail("ANALYTICAL_SHAPE_MISSING_GROUP_BY", "still wrong shape")


def test_unknown_column_names_extracts_qualified_and_unqualified_columns():
    issues = [
        ValidationIssue("UNKNOWN_COLUMN", "Unknown column: diet_quality"),
        ValidationIssue("UNKNOWN_COLUMN", "Unknown unqualified column: s.depression_flag"),
        ValidationIssue("OTHER", "Unknown column: ignored"),
    ]

    assert unknown_column_names(issues) == ["diet_quality", "depression_flag"]


def test_patch_column_name_is_token_safe():
    sql = (
        "SELECT diet_quality, diet_quality_score "
        "FROM student_depression WHERE diet_quality = 'poor'"
    )

    patched = patch_column_name(sql, "diet_quality", "dietary_habits")

    assert "SELECT dietary_habits, diet_quality_score" in patched
    assert "WHERE dietary_habits = 'poor'" in patched


def test_sql_table_names_extracts_from_and_join_tables():
    sql = (
        "WITH x AS (SELECT 1) "
        "SELECT * FROM student_depression sd "
        "JOIN university_student_mental_health umh ON sd.id = umh.id"
    )

    assert sql_table_names(sql) == {
        "student_depression",
        "university_student_mental_health",
    }


def test_has_shape_errors_detects_analytical_shape_codes():
    assert has_shape_errors(
        [
            ValidationIssue("UNKNOWN_COLUMN", "Unknown column: x"),
            ValidationIssue("ANALYTICAL_SHAPE_MISSING_GROUP_BY", "missing group"),
        ]
    )
    assert not has_shape_errors([ValidationIssue("UNKNOWN_COLUMN", "Unknown column: x")])


def test_try_shape_surgeon_validates_rewritten_sql_before_adoption():
    state = VTDState(trace_id="t", raw_question="compare groups")

    def rewrite_fn(*_args, **_kwargs):
        return SimpleNamespace(
            rewritten=True,
            sql="SELECT depression_flag, COUNT(*) AS count FROM student_depression GROUP BY depression_flag",
            action="shape_surgeon_invoked=true; shape_surgeon_patch_applied=true",
        )

    patched_sql, result, action = try_shape_surgeon(
        "SELECT COUNT(*) AS count FROM student_depression WHERE depression_flag = 1",
        state=state,
        registry=SchemaRegistry(),
        issues=[ValidationIssue("ANALYTICAL_SHAPE_SINGLE_SIDED_COMPARISON", "single-sided")],
        validator_factory=_PassingValidator,
        shape_validator_factory=_PassingShapeValidator,
        rewrite_fn=rewrite_fn,
    )

    assert result is not None
    assert result.ok
    assert patched_sql == (
        "SELECT depression_flag, COUNT(*) AS count FROM student_depression GROUP BY depression_flag"
    )
    assert "shape_surgeon_patch_validated=true" in action


def test_try_shape_surgeon_rejects_rewrite_that_still_fails_shape_validation():
    state = VTDState(trace_id="t", raw_question="compare groups")

    def rewrite_fn(*_args, **_kwargs):
        return SimpleNamespace(
            rewritten=True,
            sql="SELECT COUNT(*) AS count FROM student_depression",
            action="shape_surgeon_invoked=true; shape_surgeon_patch_applied=true",
        )

    _patched_sql, result, action = try_shape_surgeon(
        "SELECT COUNT(*) AS count FROM student_depression WHERE depression_flag = 1",
        state=state,
        registry=SchemaRegistry(),
        issues=[ValidationIssue("ANALYTICAL_SHAPE_SINGLE_SIDED_COMPARISON", "single-sided")],
        validator_factory=_PassingValidator,
        shape_validator_factory=_FailingShapeValidator,
        rewrite_fn=rewrite_fn,
    )

    assert result is not None
    assert not result.ok
    assert any(issue.code == "ANALYTICAL_SHAPE_MISSING_GROUP_BY" for issue in result.issues)
    assert "shape_surgeon_patch_validated=false" in action
