from types import SimpleNamespace

from src.graph.nodes.candidate_inspector import inspect_sql_candidate
from src.graph.state import VTDState
from src.sql_validation.validation_result import ValidationIssue, ValidationResult


class _Registry:
    pass


class _Rewriter:
    def rewrite_for_question(self, sql, *, question):
        return f"{sql} /* rewritten for {question} */"


class _PassingValidator:
    def __init__(self, *, registry):
        self.registry = registry

    def validate(self, sql):
        return ValidationResult.pass_(normalized_sql=sql.replace(" /* rewritten for q */", ""))


class _FailingValidator:
    def __init__(self, *, registry):
        self.registry = registry

    def validate(self, _sql):
        return ValidationResult.fail("FORBIDDEN_KEYWORD", "Forbidden SQL keyword.")


class _PassingShapeValidator:
    def validate(self, *_args, **_kwargs):
        return ValidationResult.pass_()


class _FailingShapeValidator:
    def validate(self, *_args, **_kwargs):
        return ValidationResult.fail("ANALYTICAL_SHAPE_MISSING_GROUP_BY", "missing group by")


class _Executor:
    def __init__(self, calls):
        self.calls = calls

    def execute_readonly(self, sql):
        self.calls.append(sql)
        return SimpleNamespace(ok=True, result_hash="hash", error=None, latency_ms=7)


def _state():
    return VTDState(trace_id="t", raw_question="q")


def test_inspect_sql_candidate_records_missing_sql_without_validation_or_execution():
    execution_calls = []

    result = inspect_sql_candidate(
        candidate_id="candidate_1",
        sql=None,
        state=_state(),
        raw_model_response="{}",
        parsed_payload={},
        prompt_variant="primary",
        registry_factory=_Registry,
        validator_factory=_PassingValidator,
        shape_validator_factory=_PassingShapeValidator,
        rewriter_factory=_Rewriter,
        executor_factory=lambda: _Executor(execution_calls),
    )

    assert result["valid_sql"] is False
    assert result["execution_passed"] is False
    assert result["metadata"]["validation_errors"][0]["code"] == "MISSING_SQL"
    assert execution_calls == []


def test_inspect_sql_candidate_does_not_execute_failed_validation():
    execution_calls = []

    result = inspect_sql_candidate(
        candidate_id="candidate_1",
        sql="DROP TABLE student_depression",
        state=_state(),
        raw_model_response='{"sql": "DROP TABLE student_depression"}',
        parsed_payload={"sql": "DROP TABLE student_depression"},
        prompt_variant="primary",
        registry_factory=_Registry,
        validator_factory=_FailingValidator,
        shape_validator_factory=_PassingShapeValidator,
        rewriter_factory=_Rewriter,
        executor_factory=lambda: _Executor(execution_calls),
    )

    assert result["valid_sql"] is False
    assert result["execution_passed"] is False
    assert result["metadata"]["validation_errors"][0]["code"] == "FORBIDDEN_KEYWORD"
    assert execution_calls == []


def test_inspect_sql_candidate_does_not_execute_shape_failed_sql():
    execution_calls = []

    result = inspect_sql_candidate(
        candidate_id="candidate_1",
        sql="SELECT COUNT(*) AS n FROM student_depression",
        state=_state(),
        raw_model_response='{"sql": "SELECT COUNT(*) AS n FROM student_depression"}',
        parsed_payload={"sql": "SELECT COUNT(*) AS n FROM student_depression"},
        prompt_variant="primary",
        registry_factory=_Registry,
        validator_factory=_PassingValidator,
        shape_validator_factory=_FailingShapeValidator,
        rewriter_factory=_Rewriter,
        executor_factory=lambda: _Executor(execution_calls),
    )

    assert result["valid_sql"] is False
    assert result["metadata"]["shape_ok"] is False
    assert result["metadata"]["validation_errors"][0]["code"] == (
        "ANALYTICAL_SHAPE_MISSING_GROUP_BY"
    )
    assert execution_calls == []


def test_inspect_sql_candidate_executes_validated_sql_through_injected_executor():
    execution_calls = []

    result = inspect_sql_candidate(
        candidate_id="candidate_1",
        sql="SELECT COUNT(*) AS n FROM student_depression",
        state=_state(),
        raw_model_response='{"sql": "SELECT COUNT(*) AS n FROM student_depression"}',
        parsed_payload={"sql": "SELECT COUNT(*) AS n FROM student_depression"},
        prompt_variant="primary",
        registry_factory=_Registry,
        validator_factory=_PassingValidator,
        shape_validator_factory=_PassingShapeValidator,
        rewriter_factory=_Rewriter,
        executor_factory=lambda: _Executor(execution_calls),
    )

    assert result["valid_sql"] is True
    assert result["execution_passed"] is True
    assert result["result_hash"] == "hash"
    assert result["metadata"]["execution_latency_ms"] == 7
    assert execution_calls == ["SELECT COUNT(*) AS n FROM student_depression"]


def test_inspect_sql_candidate_uses_injected_validation_issue_formatter():
    execution_calls = []

    result = inspect_sql_candidate(
        candidate_id="candidate_1",
        sql="DROP TABLE student_depression",
        state=_state(),
        raw_model_response='{"sql": "DROP TABLE student_depression"}',
        parsed_payload={"sql": "DROP TABLE student_depression"},
        prompt_variant="primary",
        registry_factory=_Registry,
        validator_factory=_FailingValidator,
        shape_validator_factory=_PassingShapeValidator,
        rewriter_factory=_Rewriter,
        executor_factory=lambda: _Executor(execution_calls),
        validation_issues_formatter=lambda issues: [
            {
                "code": issue.code if isinstance(issue, ValidationIssue) else "UNKNOWN",
                "message": "redacted",
            }
            for issue in issues
        ],
    )

    assert result["metadata"]["validation_errors"] == [
        {"code": "FORBIDDEN_KEYWORD", "message": "redacted"}
    ]
    assert execution_calls == []
