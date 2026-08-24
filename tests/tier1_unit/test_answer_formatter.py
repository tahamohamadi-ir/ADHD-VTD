from __future__ import annotations

from src.output.answer_formatter import (
    EMPTY_RESULT_ANSWER,
    RESEARCH_DISCLAIMER,
    format_answer,
)


def test_refuses_unsafe_sql_in_persian():
    result = format_answer({"actual_action": "refuse_unsafe_sql"})

    assert "امنیتی" in result["final_answer"]


def test_privacy_refusal():
    result = format_answer({"actual_action": "refuse_privacy"})

    assert "حریم خصوصی" in result["final_answer"]


def test_clarification_answer():
    result = format_answer({"actual_action": "ask_clarification"})

    assert "شفاف‌تر" in result["final_answer"]


def test_fail_gracefully_answer():
    result = format_answer({"actual_action": "fail_gracefully"})

    assert "موفقیت‌آمیز نبود" in result["final_answer"]


def test_empty_result_answer():
    result = format_answer({"actual_action": "generate_sql", "execution_result": []})

    assert result["final_answer"] == EMPTY_RESULT_ANSWER


def test_scalar_kpi_answer_rounds_float():
    result = format_answer(
        {
            "actual_action": "format_answer",
            "execution_result": [{"total": 3.14159}],
        }
    )

    assert "3.14" in result["final_answer"]
    assert "تحلیل انجام شد" in result["final_answer"]


def test_table_answer_caps_at_ten_rows_with_disclaimer():
    rows = [{"city": f"city_{i}", "n": i} for i in range(15)]

    result = format_answer({"actual_action": "format_answer", "execution_result": rows})

    answer = result["final_answer"]
    assert "| city |" in answer or "| city_0" not in answer
    assert "city_9" in answer and "city_10" not in answer
    assert "نمایش ۱۰ ردیف از مجموع 15" in answer
    assert RESEARCH_DISCLAIMER in answer
