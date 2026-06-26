from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class QueryShape(str, Enum):
    """Expected analytical result shape for a natural-language query."""

    SCALAR = "scalar"
    GROUPED = "grouped"
    RANKING = "ranking"
    TIMESERIES = "timeseries"
    MATRIX = "matrix"
    RAW_ROWS = "raw_rows"
    CLARIFICATION = "clarification"


class QueryShapeContract(BaseModel):
    """Static contract used to reject valid SQL with the wrong answer shape."""

    shape: QueryShape
    max_rows: int | None = None
    require_group_by: bool = False
    forbid_group_by: bool = False
    require_order_by: bool = False
    require_limit: bool = False
    forbid_limit: bool = False
    forbid_where: bool = False
    min_group_by_dimensions: int | None = None
    required_dimensions: list[str] = Field(default_factory=list)
    expected_aggregate_aliases: list[str] = Field(default_factory=list)

    @classmethod
    def scalar(cls, *, allow_filters: bool = False) -> "QueryShapeContract":
        return cls(
            shape=QueryShape.SCALAR,
            max_rows=1,
            forbid_group_by=True,
            forbid_limit=True,
            forbid_where=not allow_filters,
        )

    @classmethod
    def grouped(cls, *, dimensions: list[str] | None = None) -> "QueryShapeContract":
        return cls(
            shape=QueryShape.GROUPED,
            require_group_by=True,
            min_group_by_dimensions=max(1, len(dimensions or [])),
            required_dimensions=dimensions or [],
        )

    @classmethod
    def ranking(cls, *, require_limit: bool = False) -> "QueryShapeContract":
        return cls(
            shape=QueryShape.RANKING,
            require_order_by=True,
            require_limit=require_limit,
        )

    @classmethod
    def timeseries(cls, *, time_dimension: str | None = None) -> "QueryShapeContract":
        dimensions = [time_dimension] if time_dimension else []
        return cls(
            shape=QueryShape.TIMESERIES,
            require_group_by=bool(dimensions),
            require_order_by=True,
            required_dimensions=dimensions,
            min_group_by_dimensions=1 if dimensions else None,
        )

    @classmethod
    def matrix(cls, *, dimensions: list[str] | None = None) -> "QueryShapeContract":
        return cls(
            shape=QueryShape.MATRIX,
            require_group_by=True,
            min_group_by_dimensions=max(2, len(dimensions or [])),
            required_dimensions=dimensions or [],
        )

    @classmethod
    def raw_rows(cls) -> "QueryShapeContract":
        return cls(
            shape=QueryShape.RAW_ROWS,
            require_limit=True,
            forbid_group_by=True,
        )
