from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PositiveExample(BaseModel):
    """SQL-positive benchmark item used for Text-to-SQL execution metrics."""

    id: str
    question_fa: str
    difficulty: str = "unknown"
    category: str = "unknown"
    sql: str
    expected_tables: list[str] = Field(default_factory=list)
    expected_columns: list[str] = Field(default_factory=list)
    expected_values: list[str] = Field(default_factory=list)
    expected_join_paths: list[str] = Field(default_factory=list)
    recommended_visual: str | None = None
    safe_sql: bool = True
    dialect: str = "sqlite"
    metadata: dict[str, Any] = Field(default_factory=dict)


class BehavioralExample(BaseModel):
    """Non-SQL or reliability-focused item scored by expected action, not EX."""

    id: str
    evaluation_type: str = "unknown"
    user_utterance_fa: str
    should_generate_sql: bool
    expected_action: str
    expected_sql: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetPackageSummary(BaseModel):
    total: int
    sql_positive: int
    behavioral: int
    by_difficulty: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
