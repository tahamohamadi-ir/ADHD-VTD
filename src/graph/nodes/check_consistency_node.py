from typing import Any, Dict
from src.graph.state import VTDState
from src.evaluation.sql_consistency_critic import analyze_question_sql_consistency


def check_consistency(state: VTDState) -> Dict[str, Any]:
    """
    Checks the semantic consistency of the generated SQL against the raw question.
    """
    if not state.generated_sql:
        return {"candidate_consistency_report": None}

    question = state.raw_question or state.normalized_question
    if not question:
        return {"candidate_consistency_report": None}

    report = analyze_question_sql_consistency(str(question), str(state.generated_sql))

    # Store the report in state
    return {"candidate_consistency_report": report.as_dict()}
