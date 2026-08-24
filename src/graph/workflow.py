from typing import Any

from langgraph.graph import StateGraph, END

from src.graph.state import VTDState
from src.graph.nodes.base_nodes import initialize_trace
from src.graph.nodes.execution_node import execute_sql
from src.graph.nodes.generation_node import (
    build_prompt,
    generate_sql,
    parse_llm_output,
    plan_multi_candidate,
)
from src.graph.nodes.intent_node import build_qir, classify_intent
from src.graph.nodes.normalize_node import normalize_input
from src.graph.nodes.output_node import (
    ask_clarification,
    fail_gracefully,
    format_answer,
    refuse_unsafe_sql,
)
from src.graph.nodes.reflexion_node import reflect_on_error
from src.graph.nodes.retrieval_node import retrieve_context
from src.graph.nodes.schema_linking_node import link_schema
from src.graph.nodes.validation_node import validate_sql
from src.graph.routes import (
    route_pre_generation,
    route_after_validation,
    route_after_execution,
    route_after_reliability,
)
from src.graph.nodes.check_consistency_node import check_consistency
from src.graph.nodes.compute_reliability_node import compute_reliability
from src.graph.nodes.output_chain_nodes import log_benchmark_record, recommend_chart


def create_workflow(checkpointer: Any | None = None):
    """Create and compile the VTD LangGraph workflow."""
    workflow = StateGraph(VTDState)

    # Add Nodes
    workflow.add_node("initialize_trace", initialize_trace)
    workflow.add_node("normalize_input", normalize_input)
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("build_qir", build_qir)
    workflow.add_node("link_schema", link_schema)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("build_prompt", build_prompt)
    workflow.add_node("plan_multi_candidate", plan_multi_candidate)
    workflow.add_node("generate_sql", generate_sql)
    workflow.add_node("parse_llm_output", parse_llm_output)
    workflow.add_node("validate_sql", validate_sql)
    workflow.add_node("execute_sql", execute_sql)
    workflow.add_node("format_answer", format_answer)
    workflow.add_node("reflect_on_error", reflect_on_error)
    workflow.add_node("fail_gracefully", fail_gracefully)
    workflow.add_node("ask_clarification", ask_clarification)
    workflow.add_node("refuse_unsafe_sql", refuse_unsafe_sql)
    workflow.add_node("check_consistency", check_consistency)
    workflow.add_node("compute_reliability", compute_reliability)
    workflow.add_node("recommend_chart", recommend_chart)
    workflow.add_node("log_benchmark_record", log_benchmark_record)

    # Set Entry Point
    workflow.set_entry_point("initialize_trace")

    # Linear Edges
    workflow.add_edge("initialize_trace", "normalize_input")
    workflow.add_edge("normalize_input", "classify_intent")
    workflow.add_edge("classify_intent", "build_qir")

    # Conditional Routing from QIR
    workflow.add_conditional_edges(
        "build_qir",
        route_pre_generation,
        {
            "link_schema": "link_schema",
            "ask_clarification": "ask_clarification",
            "answer_without_sql": "ask_clarification",
            "refuse_unsafe_sql": "refuse_unsafe_sql",
        },
    )

    workflow.add_edge("link_schema", "retrieve_context")
    workflow.add_edge("retrieve_context", "build_prompt")
    workflow.add_edge("build_prompt", "plan_multi_candidate")
    workflow.add_edge("plan_multi_candidate", "generate_sql")
    workflow.add_edge("generate_sql", "parse_llm_output")
    workflow.add_edge("parse_llm_output", "validate_sql")

    # Validation Loop
    workflow.add_conditional_edges(
        "validate_sql",
        route_after_validation,
        {
            "execute_sql": "check_consistency",
            "reflect_on_error": "reflect_on_error",
            "fail_gracefully": "fail_gracefully",
        },
    )

    workflow.add_edge("check_consistency", "execute_sql")

    # Execution Loop
    workflow.add_conditional_edges(
        "execute_sql",
        route_after_execution,
        {
            "compute_reliability": "compute_reliability",
            "reflect_on_error": "reflect_on_error",
            "fail_gracefully": "fail_gracefully",
        },
    )

    workflow.add_conditional_edges(
        "compute_reliability",
        route_after_reliability,
        {
            "format_answer": "format_answer",
            "reflect_on_error": "reflect_on_error",
            "fail_gracefully": "fail_gracefully",
            "ask_clarification": "ask_clarification",
            "refuse_unsafe_sql": "refuse_unsafe_sql",
        },
    )

    # From reflection back to generation
    workflow.add_edge("reflect_on_error", "plan_multi_candidate")

    # Output chain: every terminal path logs a benchmark record before END
    workflow.add_edge("format_answer", "recommend_chart")
    workflow.add_edge("recommend_chart", "log_benchmark_record")
    workflow.add_edge("fail_gracefully", "log_benchmark_record")
    workflow.add_edge("ask_clarification", "log_benchmark_record")
    workflow.add_edge("refuse_unsafe_sql", "log_benchmark_record")
    workflow.add_edge("log_benchmark_record", END)

    return workflow.compile(checkpointer=checkpointer) if checkpointer else workflow.compile()
