from typing import Literal
from src.graph.state import VTDState

def route_pre_generation(state: VTDState) -> Literal["link_schema", "ask_clarification"]:
    """Decide whether to proceed to schema linking or ask for clarification."""
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

def route_after_execution(state: VTDState) -> Literal["format_answer", "reflect_on_error", "fail_gracefully"]:
    """Decide whether to format the answer or reflect on error if execution failed."""
    if state.execution_result is not None:
        return "format_answer"
        
    # Ablation: if reflexion or repair is disabled, fail immediately on error
    if not state.ablation_config.get("reflexion", True) or not state.ablation_config.get("repair", True):
        return "fail_gracefully"

    if state.retry_count >= state.max_retries:
        return "fail_gracefully"
        
    return "reflect_on_error"
