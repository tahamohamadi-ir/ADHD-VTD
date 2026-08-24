from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryIR(BaseModel):
    """
    Intermediate Representation of the user's natural language query.
    Decouples intent understanding from raw SQL syntax.
    """

    task_type: str | None = None
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    filters: list[dict[str, Any]] = Field(default_factory=list)
    aggregation: str | None = None
    time_range: dict[str, str] | None = None
    expected_result_shape: str | None = None
    chart_intent: bool = False
    should_generate_sql: bool = True
