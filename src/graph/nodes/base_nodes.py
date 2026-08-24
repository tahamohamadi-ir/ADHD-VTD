import os
import time
import uuid
from typing import Any, Dict

from src.config.paths import MODELS_DIR
from src.config.settings import SETTINGS
from src.core.enums import IntentLabel
from src.core.enums import ExpectedAction
from src.core.query_ir import QueryIR
from src.graph.state import VTDState, LinkedSchema
from src.graph.nodes.candidate_helpers import (
    CANDIDATE_PROMPT_SUFFIXES,
    CANDIDATE_PROMPT_VARIANTS,
    can_generate_extra_candidates,
    candidate_adoption_id,
    candidate_by_id,
    candidate_generation_prompt,
    candidate_is_adoption_improvement,
    candidate_is_viable,
    candidate_prompt_variant,
    candidate_runtime_score,
    first_candidate_id,
    validation_issues_as_dict,
)
from src.graph.nodes.candidate_inspector import inspect_sql_candidate
from src.graph.nodes.candidate_orchestrator import (
    generate_sql_candidates as run_candidate_orchestrator,
)
from src.graph.nodes.execution_attempts import (
    execution_needs_retry,
    execution_state_updates,
    update_latest_attempt_with_execution_result,
)
from src.graph.nodes.generation_router import route_sql_generation
from src.graph.nodes.output_payloads import (
    action_answer_updates,
    clarification_answer_updates,
    fail_gracefully_updates,
    format_answer_updates,
)
from src.graph.nodes.reflexion_payloads import (
    latest_reflexion_context,
    reflexion_updates,
    repair_critic_feedback,
    repair_validation_error_text,
    seed_transition_memory,
    update_latest_attempt_with_reflexion,
)
from src.graph.nodes.sql_repair_helpers import (
    UNKNOWN_COLUMN_ALIASES,
    has_shape_errors,
    patch_column_name,
    sql_table_names,
    try_shape_surgeon,
    try_unknown_column_surgeon,
    unknown_column_names,
)
from src.graph.nodes.validation_attempts import (
    build_missing_sql_attempt,
    build_validation_attempt,
    decide_validation_retry,
    missing_sql_validation_errors,
    validation_errors_from_issues,
)
from src.nlu.persian_normalizer import PersianNormalizer
from src.nlu.intent_classifier import IntentClassifier
from src.nlu.term_extractor import TermExtractor
from src.schema.schema_linker import SchemaLinker
from src.schema.value_linker import ValueLinker
from src.schema.query_planner import QueryPlanner
from src.schema.schema_registry import SchemaRegistry
from src.generation.local_llm import LocalLLM
from src.generation.prompt_builder import PromptBuilder
from src.generation.template_sql import try_generate_template_sql
from src.generation.output_parser import OutputParser
from src.retrieval.context_builder import ContextBuilder
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.reranker import (
    CrossEncoderReranker,
    create_reranker,
    is_model_backed_reranker,
)
from src.retrieval.retrieval_scorer import RetrievalQuery
from src.retrieval.self_overlap import filter_self_overlaps
from src.sql_validation.validation_pipeline import ValidationPipeline
from src.sql_validation.shape_validator import SQLShapeValidator
from src.sql_validation.shape_rewriter import rewrite_analytical_shape
from src.sql_validation.sql_rewriter import SQLRewriter
from src.sql_validation.validation_result import ValidationResult
from src.db.read_only_executor import ReadOnlyExecutor
from src.utils.logging import get_logger
from src.reflexion.critic import SQLCritic
from src.reflexion.repair_planner import RepairPlanner
from src.reflexion.transition_memory import TransitionMemory
from src.evaluation.candidate_consistency import (
    SqlCandidate as ConsistencySqlCandidate,
    analyze_candidate_consistency,
)
from src.evaluation.candidate_verifier import verify_sql_candidates
from src.evaluation.multi_candidate_policy import (
    decide_multi_candidate,
    multi_candidate_policy_from_config,
)
from src.output.answer_formatter import format_answer as output_format_answer
from src.output.chart_recommender import recommend_chart
from src.output.explanation_builder import build_explanation
from src.output.narrative_generator import generate_narrative

logger = get_logger(__name__)
_LLM_CACHE: dict[tuple[str, int], LocalLLM] = {}
_DEFAULT_SQL_GENERATION_MAX_TOKENS = 512
_CANDIDATE_PROMPT_VARIANTS = CANDIDATE_PROMPT_VARIANTS
_CANDIDATE_PROMPT_SUFFIXES = CANDIDATE_PROMPT_SUFFIXES

_UNKNOWN_COLUMN_ALIASES = UNKNOWN_COLUMN_ALIASES


def _default_generation_model_path() -> str:
    configured = SETTINGS.default_model_path
    if configured:
        return configured
    return str(MODELS_DIR / "generation" / "qwen2.5-coder-7b-instruct-q4_k_m.gguf")


def _get_local_llm() -> LocalLLM:
    model_path = _default_generation_model_path()
    n_ctx = SETTINGS.llm_context_window
    cache_key = (model_path, n_ctx)
    if cache_key not in _LLM_CACHE:
        _LLM_CACHE[cache_key] = LocalLLM(model_path=model_path, n_ctx=n_ctx, n_gpu_layers=-1)
    return _LLM_CACHE[cache_key]


def _sql_generation_max_tokens() -> int:
    raw = os.environ.get("VTD_SQL_GENERATION_MAX_TOKENS")
    if not raw:
        return _DEFAULT_SQL_GENERATION_MAX_TOKENS
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_SQL_GENERATION_MAX_TOKENS
    return value if value > 0 else _DEFAULT_SQL_GENERATION_MAX_TOKENS


def _multi_candidate_extra_generation_budget_ms(config: dict[str, Any]) -> int | None:
    raw = config.get("multi_candidate_extra_generation_budget_ms")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _with_retry_increment(state: VTDState, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Increment retry_count only for failed retryable attempts."""
    updates["retry_count"] = min(state.retry_count + 1, state.max_retries)
    return updates


def _with_single_retry_slot(state: VTDState, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Leave exactly one retry for high-cost failures that still might be repairable."""
    next_retry = min(state.retry_count + 1, state.max_retries)
    if next_retry < state.max_retries:
        next_retry = max(next_retry, state.max_retries - 1)
    updates["retry_count"] = next_retry
    return updates


def _unknown_column_names(issues: list[Any]) -> list[str]:
    return unknown_column_names(issues)


def _sql_table_names(sql: str) -> set[str]:
    return sql_table_names(sql)


def _patch_column_name(sql: str, unknown: str, replacement: str) -> str:
    return patch_column_name(sql, unknown, replacement)


def _try_unknown_column_surgeon(
    sql: str,
    *,
    question: str,
    state: VTDState,
    registry: SchemaRegistry,
) -> tuple[str | None, ValidationResult | None, str]:
    return try_unknown_column_surgeon(
        sql,
        question=question,
        state=state,
        registry=registry,
        validator_factory=ValidationPipeline,
        aliases=_UNKNOWN_COLUMN_ALIASES,
    )


def _has_shape_errors(issues: list[Any]) -> bool:
    return has_shape_errors(issues)


def _try_shape_surgeon(
    sql: str,
    *,
    state: VTDState,
    registry: SchemaRegistry,
    issues: list[Any],
) -> tuple[str | None, ValidationResult | None, str]:
    return try_shape_surgeon(
        sql,
        state=state,
        registry=registry,
        issues=issues,
        validator_factory=ValidationPipeline,
        shape_validator_factory=SQLShapeValidator,
        rewrite_fn=rewrite_analytical_shape,
    )


def initialize_trace(state: VTDState) -> Dict[str, Any]:
    """
    Initializes the execution trace with a unique ID and resets the retry counter.
    This is the entry point of the graph.
    """
    trace_id = state.trace_id or str(uuid.uuid4())
    logger.info(f"--- Starting New Trace: {trace_id} ---")
    return {
        "trace_id": trace_id,
        "retry_count": 0,
        "max_retries": state.max_retries,
    }


def normalize_input(state: VTDState) -> Dict[str, Any]:
    """
    Cleans and normalizes the Persian input text using the PersianNormalizer.
    Ensures consistent spacing and character normalization.
    """
    # Ablation: if nlu is disabled, skip normalization
    if not state.ablation_config.get("nlu", True):
        return {"normalized_question": state.raw_question, "language": "fa"}

    normalizer = PersianNormalizer()
    result = normalizer.normalize(state.raw_question)
    logger.debug(f"Normalized Question: {result.normalized}")
    return {"normalized_question": result.normalized, "language": "fa"}


def classify_intent(state: VTDState) -> Dict[str, Any]:
    """
    Determines the user's intent (e.g., aggregation, count, rate) from the normalized text.
    Also assesses whether the question is safe and requires SQL generation.
    """
    if not state.normalized_question:
        return {"intent": IntentLabel.AMBIGUOUS_QUERY.value, "intent_confidence": 0.0}

    classifier = IntentClassifier()
    decision = classifier.classify(state.normalized_question)
    logger.info(f"Detected Intent: {decision.intent.value} (Confidence: {decision.confidence})")

    return {
        "intent": decision.intent.value,
        "intent_confidence": decision.confidence,
        "should_generate_sql": decision.should_generate_sql,
        "safety_label": decision.safety_label,
        "ambiguity_score": decision.ambiguity_score,
        "needs_clarification": decision.expected_action == ExpectedAction.ASK_CLARIFICATION,
    }


def build_qir(state: VTDState) -> Dict[str, Any]:
    """
    Constructs the Query Intermediate Representation (QIR).
    Maps natural language concepts to structured metrics, dimensions, and filters.
    """
    if not state.normalized_question:
        return {"qir": QueryIR(task_type="ambiguous")}

    extractor = TermExtractor()
    try:
        terms = extractor.extract_terms(state.normalized_question)
        terms_list = getattr(terms, "terms", [])
    except Exception as e:
        logger.warning(f"Term extraction failed: {e}")
        terms_list = []

    planner = QueryPlanner()
    intent_enum = IntentLabel(state.intent) if state.intent else IntentLabel.AMBIGUOUS_QUERY
    qir_obj = planner.build_qir(state.normalized_question, terms_list, intent_enum, None)

    return {"qir": qir_obj}


def link_schema(state: VTDState) -> Dict[str, Any]:
    """
    Links the QIR concepts to actual database tables and columns.
    Provides the DDL context needed for SQL generation.
    """
    if not state.normalized_question:
        return {"linked_schema": LinkedSchema()}

    registry = SchemaRegistry()
    schema_context = {}

    if not state.ablation_config.get("schema_linking", True):
        schema_context = dict(registry.tables)
        return {
            "linked_schema": LinkedSchema(
                tables=list(schema_context),
                columns=[],
                confidence=0.0,
                unresolved_terms=["schema_linking_disabled"],
            ),
            "schema_context": schema_context,
        }

    linker = SchemaLinker()
    result = linker.link(state.normalized_question)
    planner = QueryPlanner()
    intent_enum = IntentLabel(state.intent) if state.intent else IntentLabel.AMBIGUOUS_QUERY
    qir_obj = planner.build_qir(state.normalized_question, [], intent_enum, result)

    active_tables = set(result.tables)

    # Fallback to a default table if no mapping was found
    if not active_tables:
        active_tables = {"student_depression"}

    for t in active_tables:
        info = registry.tables.get(t)
        if info:
            schema_context[t] = info

    return {
        "linked_schema": LinkedSchema(
            tables=list(active_tables), columns=result.columns, confidence=0.8
        ),
        "schema_context": schema_context,
        "qir": qir_obj,
    }


def retrieve_values(state: VTDState) -> Dict[str, Any]:
    """
    Maps user-facing Persian values to database values over linked columns
    (spec 02 section 10 optional node). Preserves existing value_links entries.
    """
    if not state.linked_schema or not state.linked_schema.columns:
        return {}

    links = ValueLinker().resolve(
        state.normalized_question or state.raw_question,
        list(state.linked_schema.columns),
    )
    resolved = {f"{link.user_value} [{link.column}]": link.resolved_value for link in links}
    return {"value_links": {**state.value_links, **resolved}}


def _qir_retrieval_skeleton(state: VTDState) -> str:
    qir = state.qir
    qir_dict = (
        qir.model_dump() if hasattr(qir, "model_dump") else (qir if isinstance(qir, dict) else {})
    )
    text = " ".join([state.raw_question or "", state.normalized_question or ""]).lower()
    tags: list[str] = []
    if qir_dict.get("expected_result_shape") == "table" or qir_dict.get("dimensions"):
        tags.append("group")
    task_type = str(qir_dict.get("task_type") or state.intent or "")
    if "rate" in task_type or any(
        term in text
        for term in (
            "rate",
            "percent",
            "percentage",
            "\u0646\u0631\u062e",
            "\u062f\u0631\u0635\u062f",
        )
    ):
        tags.extend(["count", "sum", "rate"])
    if "ranking" in task_type or any(
        term in text
        for term in (
            "rank",
            "top",
            "\u0631\u062a\u0628\u0647",
            "\u0627\u0648\u0644",
            "\u0628\u06cc\u0634\u062a\u0631\u06cc\u0646",
        )
    ):
        tags.extend(["order", "limit"])
    if "trend" in task_type or any(
        term in text
        for term in (
            "trend",
            "time",
            "year",
            "\u0631\u0648\u0646\u062f",
            "\u0633\u0627\u0644",
        )
    ):
        tags.append("group")
    if any(
        term in text
        for term in (
            "dashboard",
            "\u062f\u0627\u0634\u0628\u0648\u0631\u062f",
            "gap",
            "\u0634\u06a9\u0627\u0641",
        )
    ):
        tags.append("cte")
    if any(
        term in text
        for term in (
            "quartile",
            "percentile",
            "ntile",
            "\u0686\u0647\u0627\u0631\u06a9",
            "\u0635\u062f\u06a9",
        )
    ):
        tags.extend(["window", "rank"])
    return " ".join(dict.fromkeys(tags))


def build_agent_retriever(
    backend: str | None,
    reranker_name: str | None,
) -> tuple[HybridRetriever, CrossEncoderReranker | None]:
    """Resolve agent-mode retrieval overrides from the ablation config.

    Returns the retriever and an active model-backed reranker (or None when
    no reranker override is set, or only the identity placeholder is available).
    """
    mode: str | None = None
    if backend in {"bm25", "vector", "hybrid"}:
        mode = backend
    elif backend == "hybrid_rerank":
        mode = "hybrid"
    if mode is None:
        retriever = HybridRetriever(use_vector_store=False)
    else:
        retriever = HybridRetriever(retrieval_mode=mode)
    active_reranker: CrossEncoderReranker | None = None
    if reranker_name:
        candidate = create_reranker(reranker_name)
        if is_model_backed_reranker(candidate):
            active_reranker = candidate
    return retriever, active_reranker


def retrieve_context(state: VTDState) -> Dict[str, Any]:
    """
    Retrieves compact few-shot examples for CAG.
    The graph uses lexical/schema-aware retrieval by default to avoid loading
    heavyweight embedding models during every local agent run.
    """
    query_text = state.normalized_question or state.raw_question
    linked_schema = state.linked_schema or LinkedSchema()
    retrieval_query = RetrievalQuery(
        text=query_text,
        intent=state.intent,
        tables=linked_schema.tables,
        columns=linked_schema.columns,
        skeleton=_qir_retrieval_skeleton(state),
    )
    # Ablation: if cag is disabled, return empty examples
    if not state.ablation_config.get("cag", True):
        return {
            "retrieved_examples": [],
            "retrieval_context": "",
            "retrieval_diagnostics": [],
        }

    retriever, active_reranker = build_agent_retriever(
        backend=state.ablation_config.get("retrieval_backend"),
        reranker_name=state.ablation_config.get("reranker"),
    )
    requested_top_k = max(1, int(state.retrieval_top_k or 5))
    retrieval_top_k = (
        max(requested_top_k * 5, requested_top_k)
        if state.exclude_self_retrieval
        else requested_top_k
    )
    retrieved = retriever.retrieve(
        retrieval_query,
        top_k=retrieval_top_k,
        candidate_pool_size=max(25, retrieval_top_k * 2),
    )
    removed_ids: list[str] = []
    if state.exclude_self_retrieval:
        retrieved, removed_ids = filter_self_overlaps(
            retrieved,
            case_id=state.benchmark_case_id,
            question=query_text,
        )
    if active_reranker is not None:
        retrieved = active_reranker.rerank(retrieved, query=query_text)
    retrieved = retrieved[:requested_top_k]
    context = ContextBuilder().build(retrieved, max_examples=requested_top_k)

    logger.info(f"Retrieved {len(context.examples)} CAG examples")
    return {
        "retrieved_examples": context.examples,
        "retrieval_context": context.prompt_context,
        "retrieval_diagnostics": context.diagnostics,
        "self_overlap_removed": len(removed_ids),
        "self_overlap_removed_ids": removed_ids,
    }


def build_prompt(state: VTDState) -> Dict[str, Any]:
    """
    Synthesizes the LLM prompt using the question, QIR, and schema context.
    Uses the sql_generation.j2 template.
    """
    if not state.qir:
        return {"prompt": ""}

    value_links: dict[str, Any] = {}
    if state.ablation_config.get("value_linking", True):
        candidate_columns = _schema_candidate_columns(state.schema_context)
        links = ValueLinker().resolve(
            state.normalized_question or state.raw_question, candidate_columns
        )
        value_links = {f"{link.user_value} [{link.column}]": link.resolved_value for link in links}

    builder = PromptBuilder()
    prompt = builder.build_sql_generation_prompt(
        question=state.raw_question,
        qir=state.qir,
        schema=state.schema_context,
        value_links=value_links,
        few_shot=state.retrieved_examples,
    )
    return {"prompt": prompt, "value_links": value_links}


def plan_multi_candidate(state: VTDState) -> Dict[str, Any]:
    """Record whether extra candidates would be worth the latency cost.

    This node is intentionally annotation-only. It does not call the LLM and does
    not generate additional SQL candidates.
    """

    decision = decide_multi_candidate(
        {
            "question": state.raw_question,
            "normalized_question": state.normalized_question,
            "intent": state.intent,
            "intent_confidence": state.intent_confidence,
            "qir": state.qir.model_dump() if hasattr(state.qir, "model_dump") else state.qir,
            "generated_sql": state.generated_sql,
            "retry_count": state.retry_count,
            "max_retries": state.max_retries,
            "validation_errors": state.validation_errors,
            "execution_error": state.execution_error,
            "should_generate_sql": state.should_generate_sql,
            "generation_attempted": bool(state.attempts or state.raw_model_response),
        },
        policy=multi_candidate_policy_from_config(state.ablation_config),
    )
    return {"multi_candidate_policy": decision.as_dict()}


def _schema_candidate_columns(schema_context: dict[str, Any]) -> list[str]:
    candidate_columns: list[str] = []
    for table_name, table_info in schema_context.items():
        columns = getattr(table_info, "columns", None)
        if columns is None and isinstance(table_info, dict):
            columns = table_info.get("columns", [])
        iterable_columns = columns.values() if isinstance(columns, dict) else (columns or [])
        for column in iterable_columns:
            if isinstance(column, str):
                name = column
            elif isinstance(column, dict):
                name = column.get("name") or column.get("column_name")
            else:
                name = getattr(column, "name", None)
            if name:
                candidate_columns.append(f"{table_name}.{name}")
    return candidate_columns


def generate_sql(state: VTDState) -> Dict[str, Any]:
    """
    Invokes the Local LLM (GPU-accelerated) to generate a SQL candidate.
    Enforces JSON structure via LlamaGrammar.
    """
    return route_sql_generation(
        state,
        llm_factory=_get_local_llm,
        template_generator=try_generate_template_sql,
        multi_candidate_generator=_generate_sql_candidates,
        can_generate_extra_candidates_fn=_can_generate_extra_candidates,
        clock=time.perf_counter,
        max_tokens_fn=_sql_generation_max_tokens,
    )


def _generate_sql_candidates(
    state: VTDState, llm: LocalLLM, candidate_count: int
) -> Dict[str, Any]:
    """Generate and inspect multiple candidates behind an explicit feature flag.

    The first candidate is the primary generation. Extra candidates are adopted
    only when consistency passes and the selected candidate is viable. Otherwise
    the primary response continues through the normal graph path and candidate
    evidence remains review-only.
    """

    return run_candidate_orchestrator(
        state,
        llm,
        candidate_count,
        clock=time.perf_counter,
        max_tokens_fn=_sql_generation_max_tokens,
        extra_generation_budget_ms_fn=_multi_candidate_extra_generation_budget_ms,
        prompt_variant_fn=_candidate_prompt_variant,
        candidate_prompt_fn=_candidate_generation_prompt,
        parse_json_fn=OutputParser.extract_json,
        inspect_candidate_fn=_inspect_sql_candidate,
        consistency_candidate_factory=ConsistencySqlCandidate,
        analyze_consistency_fn=analyze_candidate_consistency,
        verify_candidates_fn=verify_sql_candidates,
        adoption_id_fn=candidate_adoption_id,
    )


def _inspect_sql_candidate(
    *,
    candidate_id: str,
    sql: str | None,
    state: VTDState,
    raw_model_response: str,
    parsed_payload: dict[str, Any] | None,
    prompt_variant: str,
) -> dict[str, Any]:
    return inspect_sql_candidate(
        candidate_id=candidate_id,
        sql=sql,
        state=state,
        raw_model_response=raw_model_response,
        parsed_payload=parsed_payload,
        prompt_variant=prompt_variant,
        registry_factory=SchemaRegistry,
        validator_factory=ValidationPipeline,
        shape_validator_factory=SQLShapeValidator,
        rewriter_factory=SQLRewriter,
        executor_factory=lambda: ReadOnlyExecutor(db_path=SETTINGS.db_path),
        validation_issues_formatter=_validation_issues_as_dict,
    )


def _first_candidate_id(candidates: list[dict[str, Any]]) -> str | None:
    return first_candidate_id(candidates)


def _candidate_by_id(
    candidates: list[dict[str, Any]], candidate_id: str | None
) -> dict[str, Any] | None:
    return candidate_by_id(candidates, candidate_id)


def _candidate_is_viable(candidate: dict[str, Any]) -> bool:
    return candidate_is_viable(candidate)


def _candidate_prompt_variant(index: int) -> str:
    return candidate_prompt_variant(index, variants=_CANDIDATE_PROMPT_VARIANTS)


def _candidate_generation_prompt(base_prompt: str | None, prompt_variant: str) -> str:
    return candidate_generation_prompt(
        base_prompt,
        prompt_variant,
        prompt_suffixes=_CANDIDATE_PROMPT_SUFFIXES,
    )


def _candidate_is_adoption_improvement(
    selected: dict[str, Any],
    primary: dict[str, Any],
    *,
    primary_id: str,
) -> bool:
    return candidate_is_adoption_improvement(selected, primary, primary_id=primary_id)


def _candidate_runtime_score(candidate: dict[str, Any]) -> float:
    return candidate_runtime_score(candidate)


def _validation_issues_as_dict(issues: list[Any]) -> list[dict[str, Any]]:
    return validation_issues_as_dict(issues)


def _can_generate_extra_candidates(state: VTDState) -> bool:
    return can_generate_extra_candidates(state)


def parse_llm_output(state: VTDState) -> Dict[str, Any]:
    """
    Extracts the SQL query and explanation from the LLM's JSON response.
    """
    if not state.generated_sql:
        return {
            "generated_sql": None,
            "parsed_payload": None,
            "validation_errors": [{"type": "OUTPUT_PARSE_ERROR", "message": "Empty LLM output"}],
        }

    parsed = OutputParser.extract_json(state.generated_sql)
    if not parsed:
        return {
            "generated_sql": None,
            "parsed_payload": None,
            "validation_errors": [{"type": "OUTPUT_PARSE_ERROR", "message": "Invalid JSON format"}],
        }

    return {
        "generated_sql": parsed.get("sql"),
        "parsed_payload": parsed,
        "explanation": parsed.get("explanation"),
        "needs_clarification": parsed.get("needs_clarification", False),
    }


def validate_sql(state: VTDState) -> Dict[str, Any]:
    """
    Validates the generated SQL for syntax and schema correctness.
    Records the attempt for the retry logic.
    """
    if not state.generated_sql:
        validation_errors = missing_sql_validation_errors(state.validation_errors)
        attempt = build_missing_sql_attempt(state, validation_errors=validation_errors)
        return _with_retry_increment(
            state,
            {
                "attempts": state.attempts + [attempt],
                "validation_errors": validation_errors,
                "generated_sql": None,
            },
        )

    registry = SchemaRegistry()
    validator = ValidationPipeline(registry=registry)
    question_rewritten_sql = SQLRewriter().rewrite_for_question(
        state.generated_sql,
        question=state.raw_question,
    )
    result = validator.validate(question_rewritten_sql)
    validated_sql = result.normalized_sql or state.generated_sql
    surgeon_action: str | None = None
    surgeon_fail_fast = False
    surgeon_single_retry = False
    shape_single_retry = False
    if not result.ok and _unknown_column_names(result.issues):
        patched_sql, patched_result, surgeon_action = _try_unknown_column_surgeon(
            validated_sql,
            question=state.raw_question,
            state=state,
            registry=registry,
        )
        if patched_result is not None:
            result = patched_result
            validated_sql = patched_result.normalized_sql or patched_sql or validated_sql
            surgeon_fail_fast = not patched_result.ok
        else:
            surgeon_single_retry = True

    if result.ok:
        shape_result = SQLShapeValidator().validate(
            validated_sql,
            question=state.raw_question,
            qir=state.qir,
            schema=state.schema_context,
        )
        if not shape_result.ok:
            result = ValidationResult(
                ok=False,
                issues=[*result.issues, *shape_result.issues],
                normalized_sql=result.normalized_sql,
            )
            patched_sql, patched_result, shape_action = _try_shape_surgeon(
                validated_sql,
                state=state,
                registry=registry,
                issues=shape_result.issues,
            )
            surgeon_action = "; ".join([part for part in (surgeon_action, shape_action) if part])
            if patched_result is not None:
                result = patched_result
                validated_sql = patched_result.normalized_sql or patched_sql or validated_sql
                shape_single_retry = not patched_result.ok
            else:
                shape_single_retry = True
    validation_errors = validation_errors_from_issues(result.issues) if not result.ok else []

    attempt = build_validation_attempt(
        state,
        sql=validated_sql,
        validation_passed=result.ok,
        validation_errors=validation_errors,
        issues=result.issues,
        repair_plan=surgeon_action,
    )

    updates = {
        "attempts": state.attempts + [attempt],
        "validation_errors": validation_errors,
    }
    retry_decision = decide_validation_retry(
        validation_passed=result.ok,
        surgeon_fail_fast=surgeon_fail_fast,
        surgeon_single_retry=surgeon_single_retry,
        shape_single_retry=shape_single_retry,
        has_shape_errors=_has_shape_errors(result.issues),
    )
    if retry_decision == "fail_fast":
        updates["retry_count"] = state.max_retries
        return updates
    if retry_decision == "single_retry":
        return _with_single_retry_slot(state, updates)
    if retry_decision == "retry_increment":
        return _with_retry_increment(state, updates)
    updates["generated_sql"] = validated_sql
    return updates


def execute_sql(state: VTDState) -> Dict[str, Any]:
    """
    Executes the validated SQL query against the read-only database.
    """
    if not state.generated_sql:
        return {"execution_error": "No SQL to execute"}

    executor = ReadOnlyExecutor(db_path=SETTINGS.db_path)
    result = executor.execute_readonly(state.generated_sql)

    attempts = update_latest_attempt_with_execution_result(state.attempts, result)
    updates = execution_state_updates(attempts=attempts, result=result)
    if execution_needs_retry(result):
        return _with_retry_increment(state, updates)
    return updates


def format_answer(state: VTDState) -> Dict[str, Any]:
    """
    Final node to format the execution result into a user-friendly answer.
    """
    return format_answer_updates(
        state,
        answer_formatter=output_format_answer,
        chart_recommender=recommend_chart,
        explanation_builder=build_explanation,
        narrative_generator=generate_narrative,
    )


def fail_gracefully(state: VTDState) -> Dict[str, Any]:
    """
    Fallback node when execution fails after max retries.
    """
    logger.error(f"Execution failed after {state.retry_count} retries.")
    return fail_gracefully_updates(state, answer_formatter=output_format_answer)


def reflect_on_error(state: VTDState) -> Dict[str, Any]:
    """
    Analyzes the most recent failure and updates the prompt with repair instructions.
    This node implements the 'Critic' and 'Planner' roles of Reflexion.
    """
    if not state.attempts:
        return {}

    error_msg, sql = latest_reflexion_context(state)

    critic = SQLCritic()
    planner = RepairPlanner()
    memory = TransitionMemory()

    seed_transition_memory(state.attempts[:-1], memory)

    if memory.is_looping(sql, error_msg):
        logger.warning(f"Loop detected for trace {state.trace_id}. Forcing failure.")
        # We can't easily force failure here without changing routes,
        # but we can set a flag or just let retry_count handle it.
        pass

    feedback = critic.analyze(sql, error_msg, str(state.schema_context))
    repair_plan = planner.plan(sql, error_msg)

    logger.info(f"Reflexion Feedback: {repair_plan}")

    new_attempts = update_latest_attempt_with_reflexion(
        state.attempts,
        critic_feedback=feedback,
        repair_plan=repair_plan,
    )

    # Update prompt for the next generation
    from src.generation.prompt_builder import PromptBuilder

    builder = PromptBuilder()

    validation_err_str = repair_validation_error_text(state, error_msg)

    repair_prompt = builder.build_repair_prompt(
        question=state.raw_question,
        schema=state.schema_context,
        qir=state.qir,
        value_links=state.value_links,
        previous_sql=sql,
        validation_errors=validation_err_str,
        critic_feedback=repair_critic_feedback(feedback, repair_plan),
    )

    return reflexion_updates(prompt=repair_prompt, attempts=new_attempts)


def ask_clarification(state: VTDState) -> Dict[str, Any]:
    """
    Node invoked when the input is ambiguous or low confidence.
    """
    return clarification_answer_updates(state, answer_formatter=output_format_answer)


def refuse_unsafe_sql(state: VTDState) -> Dict[str, Any]:
    """
    Node invoked when the safety check fails.
    """
    return action_answer_updates(
        state,
        action="refuse_unsafe_sql",
        answer_formatter=output_format_answer,
    )
