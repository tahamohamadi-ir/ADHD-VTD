from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RetrievalTrace(BaseModel):
    retrieved_ids: list[str] = Field(default_factory=list)
    bm25_ids: list[str] = Field(default_factory=list)
    vector_ids: list[str] = Field(default_factory=list)
    selected_context_tokens: int | None = None
    self_overlap_removed: int = 0
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)


class ReliabilityTrace(BaseModel):
    action: str | None = None
    reason: str | None = None
    confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)
    signals: dict[str, Any] = Field(default_factory=dict)


class AttemptTrace(BaseModel):
    item_id: str
    iteration: int
    ablation_id: str = "unknown"
    prompt: str | None = None
    raw_model_response: str | None = None
    parsed_payload: dict[str, Any] | None = None
    parsed: bool = False
    generated_sql: str | None = None
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    execution_passed: bool = False
    execution_error: str | None = None
    repair_action: str | None = None
    latency_ms: int | None = None


class PredictionRecord(BaseModel):
    item_id: str
    question_fa: str
    normalized_question: str | None = None
    qir: dict[str, Any] | None = None
    linked_schema: dict[str, Any] | None = None
    value_links: dict[str, Any] = Field(default_factory=dict)
    retrieved_examples: list[dict[str, Any]] = Field(default_factory=list)
    retrieval: RetrievalTrace | None = None
    reliability: ReliabilityTrace | None = None
    generated_sql: str | None = None
    gold_sql: str | None = None
    final_action: str
    execution_correct: bool | None = None
    valid_sql: bool | None = None
    semantic_business_correct: bool | None = None
    error_category: str | None = None
    latency_ms: int
