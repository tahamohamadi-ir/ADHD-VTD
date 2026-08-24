from __future__ import annotations

from src.output.chart_recommender import recommend_chart


def test_empty_result_has_no_recommendation():
    result = recommend_chart(None)
    empty = recommend_chart([])

    assert result["recommended_visual"] is None
    assert empty["recommended_visual"] is None
    assert empty["chart_reason"] is None


def test_single_scalar_is_kpi():
    result = recommend_chart([{"total": 12}])

    assert result["recommended_visual"] == "kpi"


def test_two_columns_is_bar_chart():
    result = recommend_chart([{"city": "a", "n": 3}, {"city": "b", "n": 5}])

    assert result["recommended_visual"] == "bar_chart"


def test_time_column_is_line_chart():
    result = recommend_chart(
        [
            {"year": 2023, "n": 3, "m": 1},
            {"year": 2024, "n": 4, "m": 2},
        ]
    )

    assert result["recommended_visual"] == "line_chart"
    assert "Time" in result["chart_reason"]


def test_matrix_without_time_is_heatmap():
    result = recommend_chart(
        [
            {"gender": "f", "sleep": 6, "gpa": 3.1},
            {"gender": "m", "sleep": 7, "gpa": 3.4},
        ]
    )

    assert result["recommended_visual"] == "heatmap"


def test_single_row_multi_column_falls_back_to_table():
    result = recommend_chart([{"a": 1, "b": 2}])

    assert result["recommended_visual"] == "table"
