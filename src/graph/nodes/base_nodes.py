import os
import re
import time
import uuid
from typing import Any, Dict

from src.config.paths import MODELS_DIR
from src.config.settings import SETTINGS
from src.config import features
from src.core.enums import IntentLabel
from src.core.enums import ExpectedAction
from src.core.query_ir import QueryIR
from src.graph.state import VTDState, LinkedSchema, SQLAttempt
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
from src.reflexion.error_taxonomy import classify_error
from src.reflexion.repair_planner import RepairPlanner
from src.reflexion.retry_policy import RetryPolicy
from src.reflexion.transition_memory import TransitionMemory
from src.evaluation.candidate_consistency import (
    SqlCandidate as ConsistencySqlCandidate,
    analyze_candidate_consistency,
)
from src.evaluation.multi_candidate_policy import decide_multi_candidate
from src.output.answer_formatter import format_answer as output_format_answer
from src.output.chart_recommender import recommend_chart
from src.output.explanation_builder import build_explanation

logger = get_logger(__name__)
_LLM_CACHE: dict[tuple[str, int], LocalLLM] = {}
_DEFAULT_SQL_GENERATION_MAX_TOKENS = 512

_UNKNOWN_COLUMN_ALIASES: tuple[dict[str, Any], ...] = (
    {
        "table": "student_depression",
        "unknown": "diet_quality",
        "replacement": "dietary_habits",
        "terms": ("diet", "dietary", "\u0631\u0698\u06cc\u0645", "\u063a\u0630\u0627\u06cc\u06cc"),
    },
    {
        "table": "student_habits_performance",
        "unknown": "dietary_habits",
        "replacement": "diet_quality",
        "terms": ("diet", "dietary", "\u0631\u0698\u06cc\u0645", "\u063a\u0630\u0627\u06cc\u06cc"),
    },
    {
        "table": "university_student_mental_health",
        "unknown": "depression_flag",
        "replacement": "depression_diagnosis",
        "terms": ("depression", "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc"),
    },
    {
        "table": "student_depression",
        "unknown": "depression_diagnosis",
        "replacement": "depression_flag",
        "terms": ("depression", "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc"),
    },
    {
        "table": "mental_health_general",
        "unknown": "depression_flag",
        "replacement": "depression_score",
        "terms": ("depression", "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc"),
    },
)


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
    names: list[str] = []
    for issue in issues:
        if getattr(issue, "code", "") != "UNKNOWN_COLUMN":
            continue
        message = str(getattr(issue, "message", ""))
        match = re.search(r"Unknown (?:unqualified )?column: ([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)", message)
        if match:
            names.append(match.group(1).split(".")[-1])
    return names


def _sql_table_names(sql: str) -> set[str]:
    return {
        match.group(1)
        for match in re.finditer(r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", sql or "", flags=re.IGNORECASE)
    }


def _patch_column_name(sql: str, unknown: str, replacement: str) -> str:
    return re.sub(rf"(?<![A-Za-z0-9_]){re.escape(unknown)}(?![A-Za-z0-9_])", replacement, sql)


def _try_unknown_column_surgeon(
    sql: str,
    *,
    question: str,
    state: VTDState,
    registry: SchemaRegistry,
) -> tuple[str | None, ValidationResult | None, str]:
    validator = ValidationPipeline(registry=registry)
    initial = validator.validate(sql)
    unknown_columns = _unknown_column_names(initial.issues)
    if not unknown_columns:
        return None, None, "surgeon_invoked=false"

    tables = _sql_table_names(sql)
    normalized_question = PersianNormalizer().normalize_text(question or "").lower()
    for spec in _UNKNOWN_COLUMN_ALIASES:
        table = str(spec["table"])
        unknown = str(spec["unknown"])
        replacement = str(spec["replacement"])
        terms = tuple(str(term) for term in spec["terms"])
        if unknown not in unknown_columns:
            continue
        if table not in tables:
            continue
        if not any(term in normalized_question for term in terms):
            continue

        patched_sql = _patch_column_name(sql, unknown, replacement)
        if patched_sql == sql:
            continue
        patched_result = validator.validate(patched_sql)
        if patched_result.ok:
            shape_result = SQLShapeValidator().validate(
                patched_result.normalized_sql or patched_sql,
                question=state.raw_question,
                qir=state.qir,
                schema=state.schema_context,
            )
            if not shape_result.ok:
                patched_result = ValidationResult(
                    ok=False,
                    issues=[*patched_result.issues, *shape_result.issues],
                    normalized_sql=patched_result.normalized_sql,
                )
        if patched_result.ok:
            return (
                patched_result.normalized_sql or patched_sql,
                patched_result,
                f"surgeon_invoked=true; surgeon_patch_applied=true; surgeon_patch_validated=true; {unknown}->{replacement}",
            )
        return (
            patched_sql,
            patched_result,
            f"surgeon_invoked=true; surgeon_patch_applied=true; surgeon_patch_validated=false; surgeon_fail_fast=true; {unknown}->{replacement}",
        )

    return None, None, "surgeon_invoked=true; surgeon_patch_applied=false; surgeon_deferred_to_single_retry=true"


def _has_shape_errors(issues: list[Any]) -> bool:
    return any(str(getattr(issue, "code", "")).startswith("ANALYTICAL_SHAPE_") for issue in issues)


def _try_shape_surgeon(
    sql: str,
    *,
    state: VTDState,
    registry: SchemaRegistry,
    issues: list[Any],
) -> tuple[str | None, ValidationResult | None, str]:
    rewrite = rewrite_analytical_shape(
        sql,
        question=state.raw_question,
        qir=state.qir,
        schema=state.schema_context,
        issues=issues,
    )
    if not rewrite.rewritten or not rewrite.sql:
        return None, None, rewrite.action

    validator = ValidationPipeline(registry=registry)
    patched_result = validator.validate(rewrite.sql)
    patched_sql = patched_result.normalized_sql or rewrite.sql
    if patched_result.ok:
        shape_result = SQLShapeValidator().validate(
            patched_sql,
            question=state.raw_question,
            qir=state.qir,
            schema=state.schema_context,
        )
        if not shape_result.ok:
            patched_result = ValidationResult(
                ok=False,
                issues=[*patched_result.issues, *shape_result.issues],
                normalized_sql=patched_sql,
            )
    action = f"{rewrite.action}; shape_surgeon_patch_validated={str(patched_result.ok).lower()}"
    return patched_sql, patched_result, action

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
    return {
        "normalized_question": result.normalized,
        "language": "fa"
    }

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
        terms_list = getattr(terms, 'terms', [])
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
            tables=list(active_tables),
            columns=result.columns,
            confidence=0.8
        ),
        "schema_context": schema_context,
        "qir": qir_obj,
    }


def _qir_retrieval_skeleton(state: VTDState) -> str:
    qir = state.qir
    qir_dict = qir.model_dump() if hasattr(qir, "model_dump") else (qir if isinstance(qir, dict) else {})
    text = " ".join([state.raw_question or "", state.normalized_question or ""]).lower()
    tags: list[str] = []
    if qir_dict.get("expected_result_shape") == "table" or qir_dict.get("dimensions"):
        tags.append("group")
    task_type = str(qir_dict.get("task_type") or state.intent or "")
    if "rate" in task_type or any(term in text for term in ("rate", "percent", "percentage", "\u0646\u0631\u062e", "\u062f\u0631\u0635\u062f")):
        tags.extend(["count", "sum", "rate"])
    if "ranking" in task_type or any(term in text for term in ("rank", "top", "\u0631\u062a\u0628\u0647", "\u0627\u0648\u0644", "\u0628\u06cc\u0634\u062a\u0631\u06cc\u0646")):
        tags.extend(["order", "limit"])
    if "trend" in task_type or any(term in text for term in ("trend", "time", "year", "\u0631\u0648\u0646\u062f", "\u0633\u0627\u0644")):
        tags.append("group")
    if any(term in text for term in ("dashboard", "\u062f\u0627\u0634\u0628\u0648\u0631\u062f", "gap", "\u0634\u06a9\u0627\u0641")):
        tags.append("cte")
    if any(term in text for term in ("quartile", "percentile", "ntile", "\u0686\u0647\u0627\u0631\u06a9", "\u0635\u062f\u06a9")):
        tags.extend(["window", "rank"])
    return " ".join(dict.fromkeys(tags))


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
            "retrieval_diagnostics": []
        }

    retriever = HybridRetriever(use_vector_store=False)
    requested_top_k = max(1, int(state.retrieval_top_k or 5))
    retrieval_top_k = max(requested_top_k * 5, requested_top_k) if state.exclude_self_retrieval else requested_top_k
    retrieved = retriever.retrieve(retrieval_query, top_k=retrieval_top_k, candidate_pool_size=max(25, retrieval_top_k * 2))
    removed_ids: list[str] = []
    if state.exclude_self_retrieval:
        retrieved, removed_ids = filter_self_overlaps(
            retrieved,
            case_id=state.benchmark_case_id,
            question=query_text,
        )
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
        links = ValueLinker().resolve(state.normalized_question or state.raw_question, candidate_columns)
        value_links = {
            f"{link.user_value} [{link.column}]": link.resolved_value
            for link in links
        }
        
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
        }
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
    if not state.prompt:
        return {"generated_sql": ""}

    if bool(state.ablation_config.get("deterministic_templates", False)):
        template_response = try_generate_template_sql(state.raw_question)
        if template_response is not None:
            return {
                "generated_sql": template_response,
                "raw_model_response": template_response,
                "generation_source": "deterministic_template",
                "generation_latency_ms": 0,
            }
        
    llm = _get_local_llm()

    policy = state.multi_candidate_policy if isinstance(state.multi_candidate_policy, dict) else {}
    multi_candidate_generation_flag = (
        bool(state.ablation_config["multi_candidate_generation"])
        if "multi_candidate_generation" in state.ablation_config
        else features.ENABLE_MULTI_CANDIDATE_GENERATION
    )
    multi_candidate_enabled = (
        multi_candidate_generation_flag
        and bool(policy.get("enabled"))
        and int(policy.get("candidate_count") or 1) > 1
        and _can_generate_extra_candidates(state)
    )

    if multi_candidate_enabled:
        return _generate_sql_candidates(state, llm, int(policy.get("candidate_count") or 1))

    started = time.perf_counter()
    response_text = llm.generate_json(
        state.prompt,
        enforce_json=True,
        max_tokens=_sql_generation_max_tokens(),
    )
    generation_latency_ms = int((time.perf_counter() - started) * 1000)
    return {
        "generated_sql": response_text,
        "raw_model_response": response_text,
        "generation_source": "llm",
        "generation_latency_ms": generation_latency_ms,
    }


def _generate_sql_candidates(state: VTDState, llm: LocalLLM, candidate_count: int) -> Dict[str, Any]:
    """Generate and inspect multiple candidates behind an explicit feature flag.

    The first candidate is the primary generation. Extra candidates are adopted
    only when consistency passes and the selected candidate is viable. Otherwise
    the primary response continues through the normal graph path and candidate
    evidence remains review-only.
    """

    requested = max(1, min(3, candidate_count))
    raw_outputs: dict[str, str] = {}
    parsed_payloads: dict[str, dict[str, Any] | None] = {}
    candidates: list[dict[str, Any]] = []
    started = time.perf_counter()

    for index in range(requested):
        candidate_id = f"candidate_{index + 1}"
        response_text = llm.generate_json(
            state.prompt,
            enforce_json=True,
            max_tokens=_sql_generation_max_tokens(),
        )
        raw_outputs[candidate_id] = response_text
        parsed = OutputParser.extract_json(response_text)
        parsed_payloads[candidate_id] = parsed
        sql = parsed.get("sql") if isinstance(parsed, dict) else None
        candidate = _inspect_sql_candidate(
            candidate_id=candidate_id,
            sql=sql,
            state=state,
            raw_model_response=response_text,
            parsed_payload=parsed,
        )
        candidates.append(candidate)

    consistency_report = analyze_candidate_consistency(
        [
            ConsistencySqlCandidate(
                candidate_id=str(candidate["candidate_id"]),
                sql=candidate.get("sql"),
                valid_sql=candidate.get("valid_sql"),
                execution_passed=candidate.get("execution_passed"),
                result_hash=candidate.get("result_hash"),
                metadata=candidate.get("metadata") or {},
            )
            for candidate in candidates
        ]
    )
    primary = candidates[0] if candidates else {}
    primary_id = str(primary.get("candidate_id") or "candidate_1")
    selected_candidate_id = consistency_report.selected_candidate_id
    selected = _candidate_by_id(candidates, selected_candidate_id)
    adoption_enabled = (
        bool(state.ablation_config["multi_candidate_adoption"])
        if "multi_candidate_adoption" in state.ablation_config
        else False
    )
    adopted_candidate_id = (
        str(selected_candidate_id)
        if adoption_enabled and consistency_report.passed and selected is not None and _candidate_is_viable(selected)
        else None
    )
    output_candidate_id = adopted_candidate_id or primary_id
    selected_raw = raw_outputs.get(output_candidate_id) or ""
    selected_payload = parsed_payloads.get(output_candidate_id)
    generation_latency_ms = int((time.perf_counter() - started) * 1000)

    return {
        "generated_sql": selected_raw,
        "raw_model_response": selected_raw,
        "generation_source": "llm_multi_candidate",
        "generation_latency_ms": generation_latency_ms,
        "candidate_sqls": candidates,
        "selected_candidate_id": adopted_candidate_id,
        "candidate_consistency": consistency_report.as_dict(),
        "parsed_payload": selected_payload,
    }


def _inspect_sql_candidate(
    *,
    candidate_id: str,
    sql: str | None,
    state: VTDState,
    raw_model_response: str,
    parsed_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "raw_model_response": raw_model_response,
        "parsed": parsed_payload is not None,
    }
    if not sql:
        metadata["validation_errors"] = [{"message": "Missing SQL in candidate payload."}]
        return {
            "candidate_id": candidate_id,
            "sql": sql,
            "valid_sql": False,
            "execution_passed": False,
            "result_hash": None,
            "source": "multi_candidate_generation",
            "metadata": metadata,
        }

    registry = SchemaRegistry()
    validator = ValidationPipeline(registry=registry)
    sql = SQLRewriter().rewrite_for_question(sql, question=state.raw_question)
    validation = validator.validate(sql)
    validated_sql = validation.normalized_sql or sql
    if validation.ok:
        shape_result = SQLShapeValidator().validate(
            validated_sql,
            question=state.raw_question,
            qir=state.qir,
            schema=state.schema_context,
        )
        if not shape_result.ok:
            validation = ValidationResult(
                ok=False,
                issues=[*validation.issues, *shape_result.issues],
                normalized_sql=validation.normalized_sql,
            )
    metadata["validation_errors"] = [{"message": str(issue)} for issue in validation.issues] if not validation.ok else []

    result_hash = None
    execution_passed = False
    if validation.ok:
        execution = ReadOnlyExecutor(db_path=SETTINGS.db_path).execute_readonly(validated_sql)
        execution_passed = execution.ok
        result_hash = execution.result_hash if execution.ok else None
        metadata["execution_error"] = execution.error if not execution.ok else None
        metadata["execution_latency_ms"] = execution.latency_ms
    return {
        "candidate_id": candidate_id,
        "sql": validated_sql,
        "valid_sql": validation.ok,
        "execution_passed": execution_passed,
        "result_hash": result_hash,
        "source": "multi_candidate_generation",
        "metadata": metadata,
    }


def _first_candidate_id(candidates: list[dict[str, Any]]) -> str | None:
    if not candidates:
        return None
    return str(candidates[0].get("candidate_id"))


def _candidate_by_id(candidates: list[dict[str, Any]], candidate_id: str | None) -> dict[str, Any] | None:
    for candidate in candidates:
        if str(candidate.get("candidate_id")) == str(candidate_id):
            return candidate
    return None


def _candidate_is_viable(candidate: dict[str, Any]) -> bool:
    return bool(candidate.get("sql")) and candidate.get("valid_sql") is not False and candidate.get("execution_passed") is not False


def _can_generate_extra_candidates(state: VTDState) -> bool:
    """Keep extra generation off the repair loop until A/B evidence improves."""

    if state.retry_count > 0:
        return False
    if state.validation_errors or state.execution_error:
        return False
    return True

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
        "needs_clarification": parsed.get("needs_clarification", False)
    }

def validate_sql(state: VTDState) -> Dict[str, Any]:
    """
    Validates the generated SQL for syntax and schema correctness.
    Records the attempt for the retry logic.
    """
    if not state.generated_sql:
        existing_errors = list(state.validation_errors or [])
        validation_errors = existing_errors or [{"type": "VALIDATION_ERROR", "message": "No SQL to validate"}]
        attempt = SQLAttempt(
            iteration=state.retry_count,
            prompt=state.prompt,
            raw_model_response=state.raw_model_response,
            generation_latency_ms=state.generation_latency_ms,
            parsed_payload=state.parsed_payload,
            sql=None,
            parsed=bool(state.parsed_payload),
            validation_passed=False,
            validation_errors=validation_errors,
            error_type=str(validation_errors[0].get("type") or "VALIDATION_ERROR") if validation_errors else "VALIDATION_ERROR",
            error_message=", ".join(
                str(error.get("message", error)) if isinstance(error, dict) else str(error)
                for error in validation_errors
            ),
        )
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
    validation_errors = [{"message": str(i)} for i in result.issues] if not result.ok else []
    
    attempt = SQLAttempt(
        iteration=state.retry_count,
        prompt=state.prompt,
        raw_model_response=state.raw_model_response,
        generation_latency_ms=state.generation_latency_ms,
        parsed_payload=state.parsed_payload,
        sql=validated_sql,
        parsed=bool(state.parsed_payload),
        validation_passed=result.ok,
        validation_errors=validation_errors,
        error_message=", ".join([str(i) for i in result.issues]) if not result.ok else None,
        repair_action=(
            "shape_surgeon"
            if surgeon_action and "shape_surgeon_patch_applied=true" in surgeon_action
            else "schema_surgeon"
            if surgeon_action and "patch_applied=true" in surgeon_action
            else None
        ),
        repair_plan=surgeon_action,
    )
    
    updates = {
        "attempts": state.attempts + [attempt],
        "validation_errors": validation_errors,
    }
    if not result.ok:
        if surgeon_fail_fast:
            updates["retry_count"] = state.max_retries
            return updates
        if surgeon_single_retry:
            return _with_single_retry_slot(state, updates)
        if shape_single_retry or _has_shape_errors(result.issues):
            return _with_single_retry_slot(state, updates)
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

    attempts = state.attempts
    if attempts:
        latest = attempts[-1]
        attempts = attempts[:-1] + [
            latest.model_copy(
                update={
                    "execution_passed": result.ok,
                    "execution_result_preview": result.rows[:5] if result.ok else None,
                    "execution_result_hash": result.result_hash if result.ok else None,
                    "latency_ms": result.latency_ms,
                    "error_message": result.error if not result.ok else latest.error_message,
                }
            )
        ]

    updates = {
        "attempts": attempts,
        "execution_result": result.rows if result.ok else None,
        "execution_error": result.error if not result.ok else None,
        "semantic_passed": result.ok
    }
    if not result.ok:
        return _with_retry_increment(state, updates)
    return updates

def format_answer(state: VTDState) -> Dict[str, Any]:
    """
    Final node to format the execution result into a user-friendly answer.
    """
    state_dict = state.model_dump()
    state_dict["actual_action"] = "format_answer"
    
    ans = output_format_answer(state_dict)
    chart = recommend_chart(state_dict.get("execution_result", []))
    exp = build_explanation(state_dict)
    
    return {
        "final_answer": ans.get("final_answer"),
        "recommended_visual": chart.get("recommended_visual"),
        "chart_reason": chart.get("chart_reason"),
        "explanation": exp or state.explanation,
        "actual_action": "format_answer"
    }

def fail_gracefully(state: VTDState) -> Dict[str, Any]:
    """
    Fallback node when execution fails after max retries.
    """
    logger.error(f"Execution failed after {state.retry_count} retries.")
    state_dict = state.model_dump()
    state_dict["actual_action"] = "fail_gracefully"
    ans = output_format_answer(state_dict)
    ans["actual_action"] = "fail_gracefully"
    return ans

def reflect_on_error(state: VTDState) -> Dict[str, Any]:
    """
    Analyzes the most recent failure and updates the prompt with repair instructions.
    This node implements the 'Critic' and 'Planner' roles of Reflexion.
    """
    if not state.attempts:
        return {}
        
    latest = state.attempts[-1]
    error_msg = latest.error_message or "Unknown failure"
    sql = latest.sql or ""
    
    critic = SQLCritic()
    planner = RepairPlanner()
    memory = TransitionMemory()
    
    # Load memory from state.attempts
    for a in state.attempts[:-1]:
        memory.update(a.sql or "", a.error_message or "")
        
    if memory.is_looping(sql, error_msg):
        logger.warning(f"Loop detected for trace {state.trace_id}. Forcing failure.")
        # We can't easily force failure here without changing routes, 
        # but we can set a flag or just let retry_count handle it.
        pass

    feedback = critic.analyze(sql, error_msg, str(state.schema_context))
    repair_plan = planner.plan(sql, error_msg)
    
    logger.info(f"Reflexion Feedback: {repair_plan}")
    
    # Update latest attempt with feedback/plan
    new_attempts = list(state.attempts)
    if new_attempts:
        latest = new_attempts[-1]
        new_attempts[-1] = latest.model_copy(
            update={
                "critic_feedback": feedback,
                "repair_plan": repair_plan
            }
        )

    # Update prompt for the next generation
    from src.generation.prompt_builder import PromptBuilder
    builder = PromptBuilder()
    
    if state.validation_errors:
        validation_err_str = "\n".join([str(e.get("message", e)) if isinstance(e, dict) else str(e) for e in state.validation_errors])
    else:
        validation_err_str = error_msg or "Unknown failure"
        if validation_err_str == "Unknown failure" and state.candidate_consistency_report and not state.candidate_consistency_report.get("passed"):
            issues = state.candidate_consistency_report.get("issues", [])
            if issues:
                validation_err_str = "\n".join([str(i.get("message", i)) for i in issues])
    
    repair_prompt = builder.build_repair_prompt(
        question=state.raw_question,
        schema=state.schema_context,
        qir=state.qir,
        value_links=state.value_links,
        previous_sql=sql,
        validation_errors=validation_err_str,
        critic_feedback=f"{feedback}\n\nRepair Plan: {repair_plan}"
    )
    
    return {
        "prompt": repair_prompt,
        "attempts": new_attempts
    }

def ask_clarification(state: VTDState) -> Dict[str, Any]:
    """
    Node invoked when the input is ambiguous or low confidence.
    """
    from src.core.enums import IntentLabel
    state_dict = state.model_dump()
    if state.intent == IntentLabel.DEFINITION_QUERY:
        state_dict["actual_action"] = "answer_without_sql"
    elif state.intent == IntentLabel.CHART_QUERY and not state.should_generate_sql:
        state_dict["actual_action"] = "answer_chart_recommendation"
    else:
        state_dict["actual_action"] = "ask_clarification"
    ans = output_format_answer(state_dict)
    ans["actual_action"] = state_dict["actual_action"]
    return ans

def refuse_unsafe_sql(state: VTDState) -> Dict[str, Any]:
    """
    Node invoked when the safety check fails.
    """
    state_dict = state.model_dump()
    state_dict["actual_action"] = "refuse_unsafe_sql"
    ans = output_format_answer(state_dict)
    ans["actual_action"] = "refuse_unsafe_sql"
    return ans
