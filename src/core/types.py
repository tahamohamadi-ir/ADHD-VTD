from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.enums import (
    AbstentionReason,
    ErrorType,
    EvaluationType,
    ExpectedAction,
    IntentLabel,
    MilestoneStage,
    RuntimeMode,
    SafetyLabel,
)


class BenchmarkCase(BaseModel):
    id: str
    question_fa: str
    sql: str | None = None
    difficulty: str | None = None
    category: str | None = None
    pattern: str | None = None
    dialect: str = "sqlite"
    safe_sql: bool = True
    recommended_visual: str | None = None
    storytelling_hint_fa: str | None = None
    expected_action: ExpectedAction = ExpectedAction.GENERATE_SQL
    metadata: dict[str, Any] = Field(default_factory=dict)


class BehavioralEvalCase(BaseModel):
    id: str
    user_utterance_fa: str
    evaluation_type: EvaluationType
    should_generate_sql: bool
    expected_action: ExpectedAction
    expected_sql: str | None = None
    expected_clarification_fa: str | None = None
    recommended_visual: str | None = None
    context_fa: str | None = None
    turns: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LinkedTable(BaseModel):
    table: str
    score: float = 0.0
    source: str | None = None


class LinkedColumn(BaseModel):
    table: str
    column: str
    score: float = 0.0
    source: str | None = None


class SchemaLinkResult(BaseModel):
    tables: list[LinkedTable] = Field(default_factory=list)
    columns: list[LinkedColumn] = Field(default_factory=list)
    join_hints: list[str] = Field(default_factory=list)
    schema_context: str = ""
    unresolved_terms: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class ValueLinkResult(BaseModel):
    table: str
    column: str
    user_value: str
    resolved_value: Any
    confidence: float = 0.0
    source: str = "unknown"
    alternatives: list[Any] = Field(default_factory=list)
    needs_clarification: bool = False


class ValidationIssue(BaseModel):
    type: ErrorType
    message: str
    repairable: bool = False
    hint: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    ok: bool
    sql: str | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    normalized_sql: str | None = None


class ExecutionResult(BaseModel):
    success: bool
    sql: str
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    result_hash: str | None = None
    latency_ms: int | None = None
    error: str | None = None


class AuditResult(BaseModel):
    audit_id: str
    source_id: str | None = None
    stage: MilestoneStage
    passed: bool
    status: str
    issues: list[ValidationIssue] = Field(default_factory=list)
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelRunResult(BaseModel):
    case_id: str
    model_name: str
    runtime_mode: RuntimeMode = RuntimeMode.RESEARCH
    prompt: str | None = None
    raw_output: str | None = None
    generated_sql: str | None = None
    validation: ValidationResult | None = None
    execution: ExecutionResult | None = None
    expected_action: ExpectedAction | None = None
    actual_action: ExpectedAction | None = None
    latency_ms: int | None = None
    tokens_per_second: float | None = None
    retry_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReliabilityResult(BaseModel):
    case_id: str
    correct_sql: bool = False
    correct_abstention: bool = False
    wrong_answer: bool = False
    unnecessary_abstention: bool = False
    unsafe_failure: bool = False
    reliability_score: float = 0.0
    abstention_reason: AbstentionReason | None = None
    explanation: str | None = None


class RouterDecision(BaseModel):
    intent: IntentLabel = IntentLabel.UNKNOWN
    safety_label: SafetyLabel = SafetyLabel.UNKNOWN
    expected_action: ExpectedAction
    confidence: float = 0.0
    needs_clarification: bool = False
    clarification_question_fa: str | None = None
    abstention_reason: AbstentionReason | None = None
    notes: str = ""
