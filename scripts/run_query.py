import argparse
import json
from pathlib import Path

from src.nlu.persian_normalizer import PersianNormalizer
from src.nlu.intent_classifier import IntentClassifier
from src.nlu.term_extractor import TermExtractor
from src.schema.schema_linker import SchemaLinker
from src.schema.query_planner import QueryPlanner
from src.schema.schema_registry import SchemaRegistry
from src.generation.local_llm import LocalLLM
from src.generation.prompt_builder import PromptBuilder
from src.generation.output_parser import OutputParser
from src.sql_validation.validation_pipeline import ValidationPipeline
from src.db.read_only_executor import ReadOnlyExecutor
from src.utils.logging import get_logger

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description="End-to-End SQL Generation using Local LLM")
    parser.add_argument("question", type=str, help="User's question in Persian or English")
    parser.add_argument("--model", type=str, default="models/generation/qwen2.5-coder-7b-instruct-q4_k_m.gguf", help="Path to GGUF model")
    parser.add_argument("--db", type=str, default="data/db/vtd_health_research_v1.db", help="Path to SQLite DB")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    logger.info(f"Question: {args.question}")

    # 1. NLU Pipeline
    normalizer = PersianNormalizer()
    norm_result = normalizer.normalize(args.question)
    norm_text = norm_result.normalized
    logger.info(f"Normalized: {norm_text}")

    intent_clf = IntentClassifier()
    intent = intent_clf.classify(norm_text)
    logger.info(f"Intent: {intent}")

    extractor = TermExtractor()
    try:
        terms = extractor.extract_terms(norm_text)
    except AttributeError:
        terms = extractor.extract(norm_text)

    schema_linker = SchemaLinker()
    link_result = schema_linker.link(norm_text)
    logger.info(f"Linked Tables: {link_result.tables}, Columns: {link_result.columns}")

    # 2. QIR Pipeline
    planner = QueryPlanner()
    
    # Try to extract actual list of strings from terms
    terms_list = getattr(terms, 'terms', [])
    if not terms_list:
        terms_list = getattr(terms, 'extracted_terms', [])
        
    qir = planner.build_qir(norm_text, terms_list, intent.intent, None)
    logger.info(f"QIR Metrics: {qir.metrics}, Dimensions: {qir.dimensions}")

    # 3. Schema Context
    schema_registry = SchemaRegistry()
    active_tables = set(link_result.tables)
    if not active_tables:
        active_tables = {"student_depression"}
        
    schema_context = {}
    for t in active_tables:
        info = schema_registry.tables.get(t)
        if info:
            schema_context[t] = info

    # 4. Prompt Generation
    builder = PromptBuilder()
    prompt = builder.build_sql_generation_prompt(
        question=args.question,
        qir=qir,
        schema=schema_context,
        value_links={}
    )
    if args.verbose:
        logger.debug(f"Prompt:\n{prompt}")

    # 5. LLM Generation
    import time
    logger.info(f"Loading LLM from {args.model} ...")
    t0 = time.time()
    llm = LocalLLM(model_path=args.model, n_ctx=2048, n_gpu_layers=-1, verbose=args.verbose)
    
    logger.info("Generating SQL...")
    t1 = time.time()
    response_text = llm.generate_json(prompt, max_tokens=1024, enforce_json=True)
    t2 = time.time()
    
    logger.info(f"Model Load Time: {t1 - t0:.2f}s | Generation Time: {t2 - t1:.2f}s")
    
    if args.verbose:
        logger.debug(f"LLM Response:\n{response_text}")

    # 6. Parsing
    parsed = OutputParser.extract_json(response_text)
    if not parsed:
        logger.error("Failed to parse JSON from LLM response")
        return

    if parsed.get("needs_clarification"):
        logger.warning(f"Model requested clarification. Explanation: {parsed.get('explanation')}")
        return

    sql = parsed.get("sql")
    if not sql:
        logger.error("No SQL found in parsed output")
        return

    logger.info(f"Generated SQL:\n{sql}")

    # 7. Validation
    validator = ValidationPipeline(registry=schema_registry)
    val_result = validator.validate(sql)
    if not val_result.ok:
        logger.error(f"SQL Validation Failed: {val_result.issues}")
        return

    logger.info("SQL Validation Passed")

    # 8. Execution
    executor = ReadOnlyExecutor(db_path=args.db)
    sql_to_execute = str(val_result.normalized_sql or sql)
    exec_result = executor.execute_readonly(sql_to_execute)
    
    if not exec_result.ok:
        logger.error(f"SQL Execution Failed: {exec_result.error}")
        return

    logger.info(f"Query returned {exec_result.row_count} rows in {exec_result.latency_ms}ms")
    
    print("\n" + "="*50)
    print(f"Explanation: {parsed.get('explanation')}")
    print(f"SQL: {val_result.normalized_sql}")
    print(f"Result (sample): {json.dumps(exec_result.rows[:2], ensure_ascii=False, indent=2)}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
