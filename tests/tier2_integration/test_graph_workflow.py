import pytest
from src.graph.workflow import create_workflow
from src.graph.state import VTDState

TERMINAL_SIDE_EXIT_NODES = ("fail_gracefully", "ask_clarification", "refuse_unsafe_sql")


def _graph_edges(workflow) -> set[tuple[str, str]]:
    return {(edge.source, edge.target) for edge in workflow.get_graph().edges}


def _node_names(workflow) -> set[str]:
    return {node.name for node in workflow.get_graph().nodes.values()}


@pytest.fixture
def workflow():
    return create_workflow()


def test_workflow_initialization(workflow):
    """Test if the workflow can be initialized and nodes are present."""
    # This is a basic smoke test for the graph structure
    assert workflow is not None
    # We can't easily introspect nodes in a compiled graph without internal API,
    # but we can try to run it.


def test_workflow_contains_spec_output_chain_nodes(workflow):
    node_names = _node_names(workflow)

    assert "recommend_chart" in node_names
    assert "log_benchmark_record" in node_names


def test_workflow_output_chain_follows_spec_topology(workflow):
    edges = _graph_edges(workflow)

    assert ("format_answer", "recommend_chart") in edges
    assert ("recommend_chart", "log_benchmark_record") in edges


def test_all_terminal_side_exits_route_through_log_benchmark_record(workflow):
    edges = _graph_edges(workflow)

    for terminal in TERMINAL_SIDE_EXIT_NODES:
        assert (terminal, "log_benchmark_record") in edges


def test_log_benchmark_record_is_sole_end_predecessor(workflow):
    edges = _graph_edges(workflow)

    end_predecessors = {source for source, target in edges if target == "__end__"}
    assert end_predecessors == {"log_benchmark_record"}


def test_create_workflow_accepts_checkpointer(tmp_path):
    pytest.importorskip("langgraph.checkpoint.sqlite")
    from src.graph.checkpoints import build_checkpointer

    checkpointer = build_checkpointer(tmp_path / "checkpoints")
    assert checkpointer is not None

    workflow = create_workflow(checkpointer=checkpointer)

    assert workflow is not None
    assert ("log_benchmark_record", "__end__") in _graph_edges(workflow)


def test_workflow_safe_refusal(workflow):
    """Test if the graph correctly refuses an ambiguous/empty question."""
    # We use a mocked or simple state to trigger ask_clarification
    state = VTDState(trace_id="test_trace", raw_question="", retry_count=0, max_retries=3)

    # We run the graph. Note: initialize_trace is the entry point.
    # We need to provide the initial state as a dict or VTDState depending on how it's called.
    # LangGraph run usually takes a dict.

    config = {"configurable": {"thread_id": "1"}}
    final_state = workflow.invoke(state, config=config)

    assert final_state["final_answer"] is not None
    # Empty question should lead to ask_clarification or fail_gracefully
    assert any(
        phrase in final_state["final_answer"]
        for phrase in ("سوال شما", "سوال خود", "شفاف", "متأسفانه")
    )


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
        validation_errors=[],
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
        validation_errors=[{"message": "error"}],
    )

    decision = route_after_validation(state)
    assert decision == "fail_gracefully"
