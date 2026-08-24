from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

from src.config.settings import SETTINGS
from src.core.query_ir import QueryIR


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
    generation_latency_ms: int | None = None
    latency_ms: int | None = None


class LinkedSchema(BaseModel):
    tables: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    join_paths: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    unresolved_terms: list[str] = Field(default_factory=list)


class SQLCandidate(BaseModel):
    candidate_id: str
    sql: str | None = None
    valid_sql: bool | None = None
    execution_passed: bool | None = None
    result_hash: str | None = None
    source: str = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReliabilityState(BaseModel):
    gate_action: str | None = None
    gate_reason: str | None = None
    confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)
    signals: dict[str, Any] = Field(default_factory=dict)


class VTDState(BaseModel):
    trace_id: str
    raw_question: str
    normalized_question: str | None = None
    language: Literal["fa", "en", "mixed"] = "fa"

    intent: str | None = None
    intent_confidence: float = 0.0
    should_generate_sql: bool = True
    safety_label: str = "safe"
    ambiguity_score: float = 0.0
    needs_clarification: bool = False
    clarification_question: str | None = None

    qir: QueryIR | None = None
    linked_schema: LinkedSchema | None = None
    schema_context: dict[str, Any] = Field(default_factory=dict)
    value_links: dict[str, Any] = Field(default_factory=dict)

    retrieved_examples: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_context: str | None = None
    retrieval_diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_top_k: int = 5
    benchmark_case_id: str | None = None
    exclude_self_retrieval: bool = False
    self_overlap_removed: int = 0
    self_overlap_removed_ids: list[str] = Field(default_factory=list)
    prompt: str | None = None

    generated_sql: str | None = None
    raw_model_response: str | None = None
    generation_source: str | None = None
    generation_latency_ms: int | None = None
    parsed_payload: dict[str, Any] | None = None
    attempts: list[SQLAttempt] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = Field(default_factory=lambda: SETTINGS.max_retries)

    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    execution_result: list[dict[str, Any]] | None = None
    execution_error: str | None = None
    semantic_passed: bool = False

    candidate_sqls: list[SQLCandidate] = Field(default_factory=list)
    selected_candidate_id: str | None = None
    candidate_consistency: dict[str, Any] | None = None
    candidate_consistency_report: dict[str, Any] | None = None
    candidate_verification: dict[str, Any] | None = None
    reliability_decision: dict[str, Any] | None = None
    multi_candidate_policy: dict[str, Any] | None = None
    multi_candidate_generation_budget: dict[str, Any] | None = None
    reliability: ReliabilityState | None = None

    final_answer: str | None = None
    explanation: str | None = None
    narrative: str | None = None
    recommended_visual: str | None = None
    chart_reason: str | None = None
    actual_action: str | None = None
    benchmark_record: dict[str, Any] | None = None

    # Ablation configuration for research studies
    ablation_config: dict[str, Any] = Field(
        default_factory=lambda: {
            "reflexion": True,
            "cag": True,
            "nlu": True,
            "multi_candidate_generation": False,
            "multi_candidate_adoption": False,
            "multi_candidate_verifier": True,
            "deterministic_templates": False,
        }
    )
