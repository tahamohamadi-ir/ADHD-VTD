from __future__ import annotations

from src.graph.nodes.output_payloads import format_answer_updates
from src.graph.state import VTDState
from src.output.narrative_generator import generate_narrative, to_persian_digits


def _state(rows: list[dict] | None) -> VTDState:
    return VTDState(
        trace_id="t1",
        raw_question="تعداد دانشجوها چقدر است؟",
        execution_result=rows,
    )


def _payload(rows, chart=None, narrative_generator=None):
    state = _state(rows)
    return format_answer_updates(
        state,
        answer_formatter=lambda s: {"final_answer": "تحلیل انجام شد."},
        chart_recommender=lambda r: chart or {"recommended_visual": None, "chart_reason": None},
        explanation_builder=lambda s: None,
        narrative_generator=narrative_generator,
    )


def test_generate_narrative_is_deterministic():
    rows = [{"city": "Tehran", "n": 12}, {"city": "Shiraz", "n": 7}]

    first = generate_narrative(execution_result=rows, category="analysis")
    second = generate_narrative(execution_result=rows, category="analysis")

    assert first == second and first


def test_generate_narrative_scalar_uses_persian_digits():
    narrative = generate_narrative(
        execution_result=[{"total": 125}], chart_recommendation={"recommended_visual": "kpi"}
    )

    assert "۱۲۵" in narrative
    assert "KPI" in narrative


def test_generate_narrative_multi_row_includes_highlight_and_chart_sentence():
    rows = [
        {"city": "Tehran", "n": 9},
        {"city": "Qom", "n": 4},
    ]

    narrative = generate_narrative(
        execution_result=rows,
        chart_recommendation={"recommended_visual": "bar_chart"},
        category="distribution",
    )

    assert "۲ ردیف" in narrative
    assert "بیشترین مقدار" in narrative
    assert "نمودار میله‌ای" in narrative
    assert "پژوهشی" in narrative


def test_generate_narrative_empty_result_variant():
    narrative = generate_narrative(execution_result=[])

    assert "داده‌ای یافت نشد" in narrative


def test_to_persian_digits_converts_all_ascii_numbers():
    assert to_persian_digits(2026) == "۲۰۲۶"
    assert to_persian_digits("a1b2") == "a۱b۲"


def test_payload_appends_narrative_only_on_success_rows():
    with_rows = _payload(
        [{"n": 5}],
        chart={"recommended_visual": "kpi", "chart_reason": "r"},
        narrative_generator=generate_narrative,
    )
    without_rows = _payload([], narrative_generator=generate_narrative)

    assert "**روایت:**" in (with_rows["final_answer"] or "")
    assert with_rows["narrative"]
    assert without_rows["narrative"] is None
    assert "**روایت:**" not in (without_rows["final_answer"] or "")


def test_payload_survives_narrative_exceptions():
    def _boom(**kwargs):
        raise RuntimeError("boom")

    payload = _payload([{"n": 1}], narrative_generator=_boom)

    assert payload["narrative"] is None
    assert payload["final_answer"] == "تحلیل انجام شد."


def test_payload_without_generator_keeps_legacy_shape():
    payload = _payload([{"n": 1}])

    assert payload["narrative"] is None
    assert payload["actual_action"] == "format_answer"
