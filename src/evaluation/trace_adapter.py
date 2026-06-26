from __future__ import annotations

from typing import Any, Iterable

from src.core.trace import AttemptTrace, PredictionRecord, ReliabilityTrace, RetrievalTrace


def prediction_record_from_benchmark(record: dict[str, Any]) -> PredictionRecord:
    item_id = str(record.get("id") or record.get("case_id") or record.get("item_id") or "")
    question = str(
        record.get("question_fa")
        or record.get("question")
        or record.get("user_utterance_fa")
        or record.get("raw_question")
        or ""
    )
    retrieved_examples = _list_of_dicts(record.get("retrieved_examples") or record.get("retrieved"))
    return PredictionRecord(
        item_id=item_id,
        question_fa=question,
        normalized_question=record.get("normalized_question"),
        qir=_dict_or_none(record.get("qir")),
        linked_schema=_dict_or_none(record.get("linked_schema")),
        value_links=_dict_or_empty(record.get("value_links")),
        retrieved_examples=retrieved_examples,
        retrieval=_retrieval_trace(record, retrieved_examples),
        reliability=_reliability_trace(record),
        generated_sql=record.get("generated_sql"),
        gold_sql=record.get("gold_sql") or record.get("sql"),
        final_action=str(record.get("actual_action") or record.get("final_action") or "controlled_failure"),
        execution_correct=_bool_or_none(record.get("execution_correct") if "execution_correct" in record else record.get("result_match")),
        valid_sql=_bool_or_none(record.get("valid_sql") if "valid_sql" in record else record.get("schema_valid")),
        semantic_business_correct=_bool_or_none(record.get("semantic_business_correct")),
        error_category=record.get("error") or record.get("error_category"),
        latency_ms=_int_or_default(record.get("latency_ms"), 0),
    )


def attempt_trace_from_benchmark(attempt: dict[str, Any], *, default_ablation_id: str = "unknown") -> AttemptTrace:
    item_id = str(attempt.get("item_id") or attempt.get("case_id") or attempt.get("id") or "")
    validation_errors = _list_of_dicts(attempt.get("validation_errors") or attempt.get("validation_issues"))
    execution_error = attempt.get("execution_error")
    if execution_error is None and attempt.get("execution_passed") is False:
        execution_error = attempt.get("error_message")
    return AttemptTrace(
        item_id=item_id,
        iteration=_int_or_default(attempt.get("iteration"), _int_or_default(attempt.get("attempt_index"), 0)),
        ablation_id=str(attempt.get("ablation_id") or default_ablation_id),
        prompt=attempt.get("prompt"),
        raw_model_response=attempt.get("raw_model_response"),
        parsed_payload=_dict_or_none(attempt.get("parsed_payload")),
        parsed=bool(attempt.get("parsed")),
        generated_sql=attempt.get("generated_sql") or attempt.get("sql"),
        validation_errors=validation_errors,
        execution_passed=bool(attempt.get("execution_passed")),
        execution_error=execution_error,
        repair_action=attempt.get("repair_action"),
        latency_ms=_int_or_none(attempt.get("latency_ms") or attempt.get("generation_latency_ms")),
    )


def validate_prediction_records(records: Iterable[dict[str, Any]]) -> list[PredictionRecord]:
    return [prediction_record_from_benchmark(record) for record in records]


def validate_attempt_records(
    attempts: Iterable[dict[str, Any]],
    *,
    default_ablation_id: str = "unknown",
) -> list[AttemptTrace]:
    return [
        attempt_trace_from_benchmark(attempt, default_ablation_id=default_ablation_id)
        for attempt in attempts
    ]


def validate_benchmark_trace_contract(
    records: Iterable[dict[str, Any]],
    attempts: Iterable[dict[str, Any]],
    *,
    default_ablation_id: str = "unknown",
) -> dict[str, int]:
    prediction_count = len(validate_prediction_records(records))
    attempt_count = len(validate_attempt_records(attempts, default_ablation_id=default_ablation_id))
    return {"predictions": prediction_count, "attempts": attempt_count}


def _retrieval_trace(record: dict[str, Any], retrieved_examples: list[dict[str, Any]]) -> RetrievalTrace:
    diagnostics = _list_of_dicts(record.get("retrieval_diagnostics"))
    retrieval = record.get("retrieval") if isinstance(record.get("retrieval"), dict) else {}
    bm25_ids = _string_list(record.get("bm25_ids") or retrieval.get("bm25_ids"))
    vector_ids = _string_list(record.get("vector_ids") or retrieval.get("vector_ids"))
    retrieved_ids = _string_list(record.get("retrieved_ids"))
    if not retrieved_ids:
        retrieved_ids = [
            str(item.get("id") or item.get("case_id") or item.get("record", {}).get("id") or "")
            for item in retrieved_examples
            if isinstance(item, dict)
        ]
    return RetrievalTrace(
        retrieved_ids=[value for value in retrieved_ids if value],
        bm25_ids=bm25_ids,
        vector_ids=vector_ids,
        selected_context_tokens=_int_or_none(record.get("selected_context_tokens")),
        self_overlap_removed=_int_or_default(record.get("self_overlap_removed"), 0),
        diagnostics=diagnostics,
    )


def _reliability_trace(record: dict[str, Any]) -> ReliabilityTrace | None:
    reliability = record.get("reliability")
    if hasattr(reliability, "model_dump"):
        reliability = reliability.model_dump()
    gate = record.get("reliability_gate")
    if hasattr(gate, "model_dump"):
        gate = gate.model_dump()
    if isinstance(gate, dict):
        return ReliabilityTrace(
            action=gate.get("action"),
            reason=gate.get("reason"),
            confidence=_float_or_none(gate.get("confidence")),
            warnings=_string_list(gate.get("warnings")),
            signals=_dict_or_empty(gate.get("signals")),
        )
    if isinstance(reliability, dict):
        return ReliabilityTrace(
            action=reliability.get("gate_action") or reliability.get("action"),
            reason=reliability.get("gate_reason") or reliability.get("reason"),
            confidence=_float_or_none(reliability.get("confidence")),
            warnings=_string_list(reliability.get("warnings")),
            signals=_dict_or_empty(reliability.get("signals")),
        )
    return None


def _dict_or_empty(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    return value if isinstance(value, dict) else {}


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    return value if isinstance(value, dict) else None


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    rows: list[dict[str, Any]] = []
    for item in value:
        if hasattr(item, "model_dump"):
            item = item.model_dump()
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    return [str(item) for item in value if item is not None]


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _int_or_default(value: Any, default: int) -> int:
    parsed = _int_or_none(value)
    return default if parsed is None else parsed


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
