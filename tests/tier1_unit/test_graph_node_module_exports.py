from __future__ import annotations

from src.graph.nodes import base_nodes
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
from src.graph.nodes.semantic_check_node import check_consistency
from src.graph.nodes.validation_node import validate_sql
from src.graph.nodes.check_consistency_node import check_consistency as canonical_check_consistency


def test_graph_node_modules_export_current_operational_nodes() -> None:
    assert normalize_input is base_nodes.normalize_input
    assert classify_intent is base_nodes.classify_intent
    assert build_qir is base_nodes.build_qir
    assert link_schema is base_nodes.link_schema
    assert retrieve_context is base_nodes.retrieve_context
    assert build_prompt is base_nodes.build_prompt
    assert plan_multi_candidate is base_nodes.plan_multi_candidate
    assert generate_sql is base_nodes.generate_sql
    assert parse_llm_output is base_nodes.parse_llm_output
    assert validate_sql is base_nodes.validate_sql
    assert execute_sql is base_nodes.execute_sql
    assert format_answer is base_nodes.format_answer
    assert reflect_on_error is base_nodes.reflect_on_error
    assert fail_gracefully is base_nodes.fail_gracefully
    assert ask_clarification is base_nodes.ask_clarification
    assert refuse_unsafe_sql is base_nodes.refuse_unsafe_sql
    assert check_consistency is canonical_check_consistency
