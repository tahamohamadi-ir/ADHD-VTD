from typing import Any, Dict
from src.graph.state import VTDState
from src.evaluation.sql_consistency_critic import analyze_question_sql_consistency
from src.sql_validation.egir import check_intent_result_alignment


def _row_count(state: VTDState) -> int | None:
    rows = state.execution_result
    if isinstance(rows, list):
        return len(rows)
    return None


def _egir_payload(state: VTDState) -> dict[str, Any] | None:
    question = state.raw_question or state.normalized_question
    sql = state.generated_sql
    if not question or not sql:
        return None
    report = check_intent_result_alignment(str(question), str(sql), _row_count(state))
    return {
        "ok": report.ok,
        "matched_intents": list(report.matched_intents),
        "issues": [
            {
                "code": issue.code,
                "message": issue.message,
                "feedback_fa": issue.feedback_fa,
                "severity": "warning",
            }
            for issue in report.issues
        ],
    }


def check_consistency(state: VTDState) -> Dict[str, Any]:
    """
    Checks the semantic consistency of the generated SQL against the raw question.
    """
    egir = _egir_payload(state)
    if not state.generated_sql:
        payload: Dict[str, Any] = {"candidate_consistency_report": None}
        if egir:
            payload["egir_report"] = egir
        return payload

    question = state.raw_question or state.normalized_question
    if not question:
        payload = {"candidate_consistency_report": None}
        if egir:
            payload["egir_report"] = egir
        return payload

    report = analyze_question_sql_consistency(str(question), str(state.generated_sql))
    report_dict = report.as_dict()
    if egir:
        report_dict["egir_issues"] = egir["issues"]
        report_dict["egir_ok"] = egir["ok"]

    # Store the report in state
    payload = {"candidate_consistency_report": report_dict}
    if egir:
        payload["egir_report"] = egir
    return payload
