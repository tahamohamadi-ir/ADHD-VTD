from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

class SQLAttempt(BaseModel):
    iteration: int
    prompt_id: str | None = None
    prompt: str | None = None
    raw_model_response: str | None = None
    parsed_payload: dict[str, Any] | None = None
    sql: str | None = None
    parsed: bool = False
    validation_passed: bool = False
    execution_passed: bool = False
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    execution_result_preview: list[dict[str, Any]] | None = None
    execution_result_hash: str | None = None
    gold_result_hash: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    repair_action: str | None = None
    critic_feedback: str | None = None
    repair_plan: str | None = None
    semantic_business_score: float | None = None
    semantic_business_reason: str | None = None
    latency_ms: int | None = None

class LinkedSchema(BaseModel):
    tables: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    join_paths: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    unresolved_terms: list[str] = Field(default_factory=list)

from src.core.query_ir import QueryIR

class VTDState(BaseModel):
    trace_id: str
    raw_question: str
    normalized_question: str | None = None
    language: Literal["fa", "en", "mixed"] = "fa"

    intent: str | None = None
    intent_confidence: float = 0.0
    safety_label: str = "safe"
    ambiguity_score: float = 0.0
    needs_clarification: bool = False
    clarification_question: str | None = None

    qir: QueryIR | None = None
    linked_schema: LinkedSchema | None = None
    schema_context: dict[str, Any] = Field(default_factory=dict)

    retrieved_examples: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_context: str | None = None
    retrieval_diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    prompt: str | None = None

    generated_sql: str | None = None
    raw_model_response: str | None = None
    parsed_payload: dict[str, Any] | None = None
    attempts: list[SQLAttempt] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    execution_result: list[dict[str, Any]] | None = None
    execution_error: str | None = None
    semantic_passed: bool = False

    final_answer: str | None = None
    explanation: str | None = None
    benchmark_record: dict[str, Any] | None = None
    
    # Ablation configuration for research studies
    ablation_config: dict[str, bool] = Field(default_factory=lambda: {
        "reflexion": True,
        "cag": True,
        "nlu": True
    })
