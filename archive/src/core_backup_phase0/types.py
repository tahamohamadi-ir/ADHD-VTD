from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    COUNT = "count_query"
    AGGREGATION = "aggregation_query"
    GROUPING = "grouping_query"
    RANKING = "ranking_query"
    TREND = "trend_query"
    COMPARISON = "comparison_query"
    RAW_RETRIEVAL = "raw_data_query"
    CHART = "chart_request"
    CLARIFICATION = "clarification_required"
    OUT_OF_SCHEMA = "out_of_schema_query"
    UNSAFE = "unsafe_query"
    UNKNOWN = "unknown"


class QueryComplexity(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXTRA_HARD = "extra_hard"


class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNSAFE = "unsafe"
    NEEDS_CLARIFICATION = "needs_clarification"


class ErrorType(str, Enum):
    NONE = "none"
    SYNTAX = "syntax_error"
    SCHEMA = "schema_error"
    SAFETY = "safety_error"
    SEMANTIC = "semantic_error"
    EXECUTION = "execution_error"
    AMBIGUITY = "ambiguity_error"


class DateRange(BaseModel):
    original_text: str
    start_date: str
    end_date: str
    calendar: Literal["jalali", "gregorian", "unknown"] = "jalali"
    granularity: Literal["day", "month", "year", "range"] = "range"


class NormalizationResult(BaseModel):
    raw_text: str
    normalized_text: str
    detected_date_ranges: list[DateRange] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class IntentClassification(BaseModel):
    intent: IntentType
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    complexity: QueryComplexity = QueryComplexity.EASY
    hints: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None


class ColumnRef(BaseModel):
    table: str
    column: str
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "unknown"

    @property
    def fqdn(self) -> str:
        return f"{self.table}.{self.column}"


class TableRef(BaseModel):
    table: str
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "unknown"


class LinkedSchema(BaseModel):
    tables: list[TableRef] = Field(default_factory=list)
    columns: list[ColumnRef] = Field(default_factory=list)
    join_hints: list[str] = Field(default_factory=list)
    schema_context: str = ""
    unresolved_terms: list[str] = Field(default_factory=list)


class RetrievedExample(BaseModel):
    id: str
    question: str
    sql: str
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeneratedSQL(BaseModel):
    sql: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    assumptions: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None


class ValidationIssue(BaseModel):
    error_type: ErrorType
    message: str
    severity: Literal["info", "warning", "error", "critical"] = "error"
    hint: str | None = None


class ValidationResult(BaseModel):
    status: ValidationStatus
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.status == ValidationStatus.VALID and not self.issues


class ExecutionResult(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float | None = None
    error: str | None = None


class AttemptRecord(BaseModel):
    iteration: int
    sql: str | None = None
    validation_result: ValidationResult | None = None
    execution_error: str | None = None
    critic_feedback: str | None = None


class PipelineTrace(BaseModel):
    question: str
    normalized: NormalizationResult | None = None
    intent: IntentClassification | None = None
    linked_schema: LinkedSchema | None = None
    retrieved_examples: list[RetrievedExample] = Field(default_factory=list)
    generated_sql: GeneratedSQL | None = None
    attempts: list[AttemptRecord] = Field(default_factory=list)
    execution_result: ExecutionResult | None = None
    final_answer: str | None = None
