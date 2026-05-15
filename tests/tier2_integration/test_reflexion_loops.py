import pytest
from src.graph.state import VTDState, SQLAttempt
from src.graph.nodes.base_nodes import reflect_on_error
from src.reflexion.transition_memory import TransitionMemory

def test_transition_memory_loop_detection():
    memory = TransitionMemory()
    sql = "SELECT * FROM depression;"
    error = "no such table: depression"
    
    memory.update(sql, error)
    assert memory.is_looping(sql, error) == True
    assert memory.is_looping("SELECT 1;", error) == False

def test_reflect_on_error_integration():
    # Setup state with a failure
    state = VTDState(
        trace_id="test-loop",
        raw_question="تعداد دانشجویان؟",
        attempts=[
            SQLAttempt(
                iteration=0,
                sql="SELECT count(*) FROM non_existent;",
                error_message="no such table: non_existent"
            )
        ],
        schema_context={"students": {"columns": {"id": "int"}}}
    )
    
    updates = reflect_on_error(state)
    
    assert "prompt" in updates
    assert "attempts" in updates
    assert updates["attempts"][-1].critic_feedback is not None
    assert updates["attempts"][-1].repair_plan is not None
    assert "non_existent" in updates["prompt"]
