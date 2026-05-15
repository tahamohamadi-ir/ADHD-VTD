import pytest
from src.graph.workflow import create_workflow
from src.graph.state import VTDState
from src.core.enums import IntentLabel

@pytest.fixture
def workflow():
    return create_workflow()

def test_workflow_initialization(workflow):
    """Test if the workflow can be initialized and nodes are present."""
    # This is a basic smoke test for the graph structure
    assert workflow is not None
    # We can't easily introspect nodes in a compiled graph without internal API, 
    # but we can try to run it.

def test_workflow_safe_refusal(workflow):
    """Test if the graph correctly refuses an ambiguous/empty question."""
    # We use a mocked or simple state to trigger ask_clarification
    state = VTDState(
        trace_id="test_trace",
        raw_question="",
        retry_count=0,
        max_retries=3
    )
    
    # We run the graph. Note: initialize_trace is the entry point.
    # We need to provide the initial state as a dict or VTDState depending on how it's called.
    # LangGraph run usually takes a dict.
    
    config = {"configurable": {"thread_id": "1"}}
    final_state = workflow.invoke(state, config=config)
    
    assert final_state["final_answer"] is not None
    # Empty question should lead to ask_clarification or fail_gracefully
    assert "سوال شما" in final_state["final_answer"] or "متأسفانه" in final_state["final_answer"]

def test_retry_count_increment(workflow):
    """
    Test that retry_count increments if validation fails.
    Since we don't want to run the actual LLM (GPU required), 
    we would ideally mock the generate_sql node.
    However, for a quick check, we can verify the logic in base_nodes directly.
    """
    from src.graph.nodes.base_nodes import validate_sql
    from src.graph.state import VTDState
    
    state = VTDState(
        trace_id="test_retry",
        raw_question="test",
        generated_sql="INVALID SQL",
        retry_count=0,
        max_retries=3,
        validation_errors=[]
    )
    
    # Manually call validate_sql to see if it returns incremented retry_count
    updates = validate_sql(state)
    assert updates["retry_count"] == 1
    assert len(updates["validation_errors"]) > 0

def test_max_retries_termination(workflow):
    """Verify that the graph terminates after max_retries."""
    from src.graph.routes import route_after_validation
    from src.graph.state import VTDState
    
    state = VTDState(
        trace_id="test_max",
        raw_question="test",
        retry_count=3,
        max_retries=3,
        validation_errors=[{"message": "error"}]
    )
    
    decision = route_after_validation(state)
    assert decision == "fail_gracefully"
