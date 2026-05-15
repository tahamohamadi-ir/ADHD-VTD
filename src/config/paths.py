from __future__ import annotations

from pathlib import Path


def find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        if (parent / "src").exists() and (parent / "data").exists():
            return parent
    # Fallback for unusual execution contexts
    return Path.cwd()


PROJECT_ROOT: Path = find_project_root()

DATA_DIR: Path = PROJECT_ROOT / "data"
DB_DIR: Path = DATA_DIR / "db"
SCHEMA_DIR: Path = DATA_DIR / "schema"
QUESTIONS_DIR: Path = DATA_DIR / "questions"
QUESTION_AUDIT_DIR: Path = QUESTIONS_DIR / "audit"
GOLDEN_SQL_DIR: Path = DATA_DIR / "golden_sql"
RAG_DIR: Path = DATA_DIR / "rag"
RESULTS_DIR: Path = PROJECT_ROOT / "results"
MODELS_DIR: Path = PROJECT_ROOT / "models"
DOCS_DIR: Path = PROJECT_ROOT / "docs"
SCRIPTS_DIR: Path = PROJECT_ROOT / "scripts"
LOGS_DIR: Path = PROJECT_ROOT / "logs"
BENCHMARK_DIR: Path = PROJECT_ROOT / "benchmark"

DB_PATH: Path = DB_DIR / "vtd_health_research_v1.db"
SCHEMA_SQL_PATH: Path = DB_DIR / "vtd_health_research_schema.sql"

SCHEMA_SNAPSHOT_PATH: Path = SCHEMA_DIR / "schema_snapshot.json"
GENERATED_SCHEMA_SNAPSHOT_PATH: Path = SCHEMA_DIR / "schema_snapshot.generated.json"
SCHEMA_GRAPH_PATH: Path = SCHEMA_DIR / "schema_graph.json"
COLUMN_ALIASES_PATH: Path = SCHEMA_DIR / "column_aliases.fa.json"
BUSINESS_GLOSSARY_PATH: Path = SCHEMA_DIR / "business_glossary.fa.json"
METRIC_DEFINITIONS_PATH: Path = SCHEMA_DIR / "metric_definitions.json"
VALUE_DICTIONARY_PATH: Path = SCHEMA_DIR / "value_dictionary.generated.json"

PHASE0_50Q_CASES_PATH: Path = QUESTION_AUDIT_DIR / "phase0_50q_audit_cases.json"
PHASE0_50Q_RESULTS_PATH: Path = QUESTION_AUDIT_DIR / "phase0_50q_audit_results.jsonl"
PHASE0_50Q_REPORT_PATH: Path = QUESTION_AUDIT_DIR / "phase0_50q_audit_report.md"
MILESTONE_1_5_STRESS_TEST_PATH: Path = QUESTION_AUDIT_DIR / "milestone_1_5_stress_test.json"
MILESTONE_1_5_STRESS_TEST_RESULTS_PATH: Path = QUESTION_AUDIT_DIR / "milestone_1_5_stress_test_results.jsonl"
MILESTONE_1_5_STRESS_TEST_REPORT_PATH: Path = QUESTION_AUDIT_DIR / "milestone_1_5_stress_test_report.md"

GOLDEN_EXAMPLES_PATH: Path = GOLDEN_SQL_DIR / "golden_examples.jsonl"
FEW_SHOT_BANK_PATH: Path = GOLDEN_SQL_DIR / "few_shot_bank.jsonl"
INDEXED_EXAMPLES_PATH: Path = RAG_DIR / "indexed_examples.jsonl"

DEFAULT_GENERATION_MODEL_PATH: Path = MODELS_DIR / "generation" / "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
DEFAULT_EMBEDDING_MODEL_PATH: Path = MODELS_DIR / "embedding" / "multilingual-e5-small"


def ensure_runtime_dirs() -> None:
    for path in [
        DATA_DIR,
        DB_DIR,
        SCHEMA_DIR,
        QUESTIONS_DIR,
        QUESTION_AUDIT_DIR,
        GOLDEN_SQL_DIR,
        RAG_DIR,
        RESULTS_DIR,
        MODELS_DIR,
        DOCS_DIR,
        LOGS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
