from typing import Literal
from src.graph.state import VTDState

def route_pre_generation(state: VTDState) -> Literal["link_schema", "ask_clarification", "refuse_unsafe_sql"]:
    """Decide whether to proceed to schema linking or ask for clarification."""
    if state.intent == "unsafe_query" or state.safety_label != "safe":
        return "refuse_unsafe_sql"
    if not state.should_generate_sql:
        return "ask_clarification"
    if state.needs_clarification or state.intent_confidence < 0.4:
        return "ask_clarification"
    return "link_schema"

def route_after_validation(state: VTDState) -> Literal["execute_sql", "reflect_on_error", "fail_gracefully"]:
    """Decide whether to execute SQL, reflect on error, or fail."""
    if not state.validation_errors:
        return "execute_sql"
    
    # Ablation: if reflexion or repair is disabled, fail immediately on error
    if not state.ablation_config.get("reflexion", True) or not state.ablation_config.get("repair", True):
        return "fail_gracefully"

    if state.retry_count >= state.max_retries:
        return "fail_gracefully"
        
    return "reflect_on_error"

def route_after_execution(state: VTDState) -> Literal["compute_reliability", "reflect_on_error", "fail_gracefully"]:
    """Decide whether to compute reliability or reflect on error if execution failed."""
    if state.execution_result is not None:
        return "compute_reliability"
        
    # Ablation: if reflexion or repair is disabled, fail immediately on error
    if not state.ablation_config.get("reflexion", True) or not state.ablation_config.get("repair", True):
        return "fail_gracefully"

    if state.retry_count >= state.max_retries:
        return "fail_gracefully"
        
    return "reflect_on_error"

def route_after_reliability(state: VTDState) -> Literal["format_answer", "reflect_on_error", "fail_gracefully", "ask_clarification", "refuse_unsafe_sql"]:
    """Decide final action based on reliability gate decision."""
    decision = state.reliability_decision
    if not decision:
        return "format_answer"
        
    action = decision.get("action")
    if action == "answer":
        return "format_answer"
    elif action == "retry" or action == "needs_review":
        # If we exhausted retries, fail gracefully.
        if state.retry_count >= state.max_retries:
            return "fail_gracefully"
        # Ablation check
        if not state.ablation_config.get("reflexion", True) or not state.ablation_config.get("repair", True):
            return "fail_gracefully"
        return "reflect_on_error"
    elif action == "ask_clarification":
        return "ask_clarification"
    elif action == "refuse_unsafe":
        return "refuse_unsafe_sql"
        
    return "format_answer"
