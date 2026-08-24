from typing import Any, Dict, List


def recommend_chart(execution_result: List[Dict[str, Any]] | None) -> Dict[str, str]:
    """Recommend a chart type based on the shape of the execution result."""
    if not execution_result:
        return {"recommended_visual": None, "chart_reason": None}

    rows = execution_result
    if not rows:
        return {"recommended_visual": None, "chart_reason": "No data"}

    num_rows = len(rows)
    num_cols = len(rows[0]) if num_rows > 0 else 0
    headers = list(rows[0].keys()) if num_rows > 0 else []

    if num_rows == 1 and num_cols == 1:
        return {"recommended_visual": "kpi", "chart_reason": "Single scalar value"}

    if num_rows > 1 and num_cols == 2:
        return {
            "recommended_visual": "bar_chart",
            "chart_reason": "Two columns typically represent a dimension and a metric",
        }

    if num_rows > 1 and num_cols >= 3:
        if any("year" in h.lower() or "date" in h.lower() or "month" in h.lower() for h in headers):
            return {"recommended_visual": "line_chart", "chart_reason": "Time dimension detected"}
        return {
            "recommended_visual": "heatmap",
            "chart_reason": "Matrix data suitable for heatmap or stacked bar chart",
        }

    return {"recommended_visual": "table", "chart_reason": "Default table representation"}
