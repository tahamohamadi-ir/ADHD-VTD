import uuid
from typing import Any, Dict

from src.config.paths import MODELS_DIR
from src.config.settings import SETTINGS
from src.core.enums import IntentLabel
from src.core.query_ir import QueryIR
from src.graph.state import VTDState, LinkedSchema, SQLAttempt
from src.nlu.persian_normalizer import PersianNormalizer
from src.nlu.intent_classifier import IntentClassifier
from src.nlu.term_extractor import TermExtractor
from src.schema.schema_linker import SchemaLinker
from src.schema.query_planner import QueryPlanner
from src.schema.schema_registry import SchemaRegistry
from src.generation.local_llm import LocalLLM
from src.generation.prompt_builder import PromptBuilder
from src.generation.output_parser import OutputParser
from src.retrieval.context_builder import ContextBuilder
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.retrieval_scorer import RetrievalQuery
from src.sql_validation.validation_pipeline import ValidationPipeline
from src.db.read_only_executor import ReadOnlyExecutor
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _default_generation_model_path() -> str:
    configured = SETTINGS.default_model_path
    if configured:
        return str(configured)
    return str(MODELS_DIR / "generation" / "qwen2.5-coder-7b-instruct-q4_k_m.gguf")


def _with_retry_increment(state: VTDState, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Increment retry_count only for failed retryable attempts."""
    updates["retry_count"] = min(state.retry_count + 1, state.max_retries)
    return updates

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
        "max_retries": SETTINGS.max_retries,
    }

def normalize_input(state: VTDState) -> Dict[str, Any]:
    """
    Cleans and normalizes the Persian input text using the PersianNormalizer.
    Ensures consistent spacing and character normalization.
    """
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
        "should_generate_sql": decision.should_generate_sql
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
        
    linker = SchemaLinker()
    result = linker.link(state.normalized_question)
    
    registry = SchemaRegistry()
    schema_context = {}
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
        "schema_context": schema_context
    }

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
    )
    retriever = HybridRetriever(use_vector_store=False)
    retrieved = retriever.retrieve(retrieval_query, top_k=3)
    context = ContextBuilder().build(retrieved, max_examples=3)

    logger.info(f"Retrieved {len(context.examples)} CAG examples")
    return {
        "retrieved_examples": context.examples,
        "retrieval_context": context.prompt_context,
        "retrieval_diagnostics": context.diagnostics,
    }

def build_prompt(state: VTDState) -> Dict[str, Any]:
    """
    Synthesizes the LLM prompt using the question, QIR, and schema context.
    Uses the sql_generation.j2 template.
    """
    if not state.qir:
        return {"prompt": ""}
        
    builder = PromptBuilder()
    prompt = builder.build_sql_generation_prompt(
        question=state.raw_question,
        qir=state.qir,
        schema=state.schema_context,
        value_links={},
        few_shot=state.retrieved_examples,
    )
    return {"prompt": prompt}

def generate_sql(state: VTDState) -> Dict[str, Any]:
    """
    Invokes the Local LLM (GPU-accelerated) to generate a SQL candidate.
    Enforces JSON structure via LlamaGrammar.
    """
    if not state.prompt:
        return {"generated_sql": ""}
        
    llm = LocalLLM(model_path=_default_generation_model_path(), n_ctx=2048, n_gpu_layers=-1)
    
    response_text = llm.generate_json(state.prompt, enforce_json=True)
    return {"generated_sql": response_text}

def parse_llm_output(state: VTDState) -> Dict[str, Any]:
    """
    Extracts the SQL query and explanation from the LLM's JSON response.
    """
    if not state.generated_sql:
        return {"validation_errors": [{"type": "PARSE_ERROR", "message": "Empty LLM output"}]}
        
    parsed = OutputParser.extract_json(state.generated_sql)
    if not parsed:
        return {"validation_errors": [{"type": "PARSE_ERROR", "message": "Invalid JSON format"}]}
    
    return {
        "generated_sql": parsed.get("sql"),
        "explanation": parsed.get("explanation"),
        "needs_clarification": parsed.get("needs_clarification", False)
    }

def validate_sql(state: VTDState) -> Dict[str, Any]:
    """
    Validates the generated SQL for syntax and schema correctness.
    Records the attempt for the retry logic.
    """
    if not state.generated_sql:
        return _with_retry_increment(
            state,
            {"validation_errors": [{"type": "VALIDATION_ERROR", "message": "No SQL to validate"}]},
        )
        
    registry = SchemaRegistry()
    validator = ValidationPipeline(registry=registry)
    result = validator.validate(state.generated_sql)
    
    attempt = SQLAttempt(
        iteration=state.retry_count,
        sql=state.generated_sql,
        validation_passed=result.ok,
        error_message=", ".join([str(i) for i in result.issues]) if not result.ok else None
    )
    
    updates = {
        "attempts": state.attempts + [attempt],
        "validation_errors": [{"message": str(i)} for i in result.issues] if not result.ok else []
    }
    if not result.ok:
        return _with_retry_increment(state, updates)
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
    Constructs the final Persian response for the user.
    """
    row_count = len(state.execution_result) if state.execution_result else 0
    explanation = state.explanation or "پاسخ بر اساس داده‌های موجود تولید شد."
    return {
        "final_answer": f"تحلیل انجام شد. {explanation} (تعداد رکوردهای بازیابی شده: {row_count})"
    }

def fail_gracefully(state: VTDState) -> Dict[str, Any]:
    """
    Final node for unrecoverable errors after maximum retries.
    """
    logger.error(f"Execution failed after {state.retry_count} retries.")
    return {
        "final_answer": "متأسفانه پس از چند بار تلاش، سیستم قادر به تولید پاسخ دقیق نبود. لطفاً سوال خود را شفاف‌تر بپرسید."
    }

def ask_clarification(state: VTDState) -> Dict[str, Any]:
    """
    Node invoked when the input is ambiguous or low confidence.
    """
    return {
        "final_answer": "سوال شما کمی ابهام دارد یا منابع لازم در دیتابیس یافت نشد. لطفاً جزئیات بیشتری (مثلاً نام دقیق متغیرها) را ذکر کنید."
    }
