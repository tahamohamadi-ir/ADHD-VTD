from __future__ import annotations

from src.graph.routes import route_after_validation, route_pre_generation
from src.graph.state import VTDState


def test_route_pre_generation_skips_llm_for_non_sql_cases():
    state = VTDState(
        trace_id="trace",
        raw_question="non sql",
        intent_confidence=1.0,
        should_generate_sql=False,
    )

    assert route_pre_generation(state) == "ask_clarification"


def test_route_pre_generation_allows_sql_when_confident():
    state = VTDState(
        trace_id="trace",
        raw_question="sql",
        intent_confidence=0.9,
        should_generate_sql=True,
    )

    assert route_pre_generation(state) == "link_schema"


def test_route_after_validation_stops_repair_when_repair_flag_disabled():
    state = VTDState(
        trace_id="trace",
        raw_question="sql",
        validation_errors=[{"message": "bad sql"}],
        retry_count=0,
        max_retries=3,
        ablation_config={"reflexion": True, "repair": False},
    )

    assert route_after_validation(state) == "fail_gracefully"
