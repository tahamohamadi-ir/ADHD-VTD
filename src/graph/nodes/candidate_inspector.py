from collections.abc import Callable
from typing import Any

from src.graph.nodes.candidate_helpers import validation_issues_as_dict
from src.graph.state import VTDState
from src.sql_validation.validation_result import ValidationResult


def inspect_sql_candidate(
    *,
    candidate_id: str,
    sql: str | None,
    state: VTDState,
    raw_model_response: str,
    parsed_payload: dict[str, Any] | None,
    prompt_variant: str,
    registry_factory: Callable[[], Any],
    validator_factory: Callable[..., Any],
    shape_validator_factory: Callable[[], Any],
    rewriter_factory: Callable[[], Any],
    executor_factory: Callable[[], Any],
    validation_issues_formatter: Callable[[list[Any]], list[dict[str, Any]]] = (
        validation_issues_as_dict
    ),
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "raw_model_response": raw_model_response,
        "parsed": parsed_payload is not None,
        "prompt_variant": prompt_variant,
    }
    if not sql:
        metadata["shape_ok"] = False
        metadata["validation_errors"] = [
            {
                "code": "MISSING_SQL",
                "message": "Missing SQL in candidate payload.",
                "severity": "error",
            }
        ]
        return {
            "candidate_id": candidate_id,
            "sql": sql,
            "valid_sql": False,
            "execution_passed": False,
            "result_hash": None,
            "source": "multi_candidate_generation",
            "metadata": metadata,
        }

    registry = registry_factory()
    validator = validator_factory(registry=registry)
    rewritten_sql = rewriter_factory().rewrite_for_question(sql, question=state.raw_question)
    validation = validator.validate(rewritten_sql)
    validated_sql = validation.normalized_sql or rewritten_sql
    shape_ok = validation.ok
    if validation.ok:
        shape_result = shape_validator_factory().validate(
            validated_sql,
            question=state.raw_question,
            qir=state.qir,
            schema=state.schema_context,
        )
        shape_ok = shape_result.ok
        if not shape_result.ok:
            validation = ValidationResult(
                ok=False,
                issues=[*validation.issues, *shape_result.issues],
                normalized_sql=validation.normalized_sql,
            )
    metadata["shape_ok"] = shape_ok
    metadata["validation_errors"] = (
        validation_issues_formatter(validation.issues) if not validation.ok else []
    )

    result_hash = None
    execution_passed = False
    if validation.ok:
        execution = executor_factory().execute_readonly(validated_sql)
        execution_passed = execution.ok
        result_hash = execution.result_hash if execution.ok else None
        metadata["execution_error"] = execution.error if not execution.ok else None
        metadata["execution_latency_ms"] = execution.latency_ms
    return {
        "candidate_id": candidate_id,
        "sql": validated_sql,
        "valid_sql": validation.ok,
        "execution_passed": execution_passed,
        "result_hash": result_hash,
        "source": "multi_candidate_generation",
        "metadata": metadata,
    }
