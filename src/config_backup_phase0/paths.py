from __future__ import annotations

from pathlib import Path


def find_project_root(start: Path | None = None) -> Path:
    """
    Find project root by walking upward until a known project marker is found.
    """
    current = (start or Path(__file__)).resolve()

    if current.is_file():
        current = current.parent

    markers = ("requirements.txt", "pyproject.toml", ".git")

    for parent in [current, *current.parents]:
        if any((parent / marker).exists() for marker in markers):
            return parent

    return Path.cwd().resolve()


PROJECT_ROOT: Path = find_project_root()

DATA_DIR: Path = PROJECT_ROOT / "data"
DB_DIR: Path = DATA_DIR / "db"
SCHEMA_DIR: Path = DATA_DIR / "schema"
QUESTIONS_DIR: Path = DATA_DIR / "questions"
GOLDEN_SQL_DIR: Path = DATA_DIR / "golden_sql"
RAG_DATA_DIR: Path = DATA_DIR / "rag"

MODELS_DIR: Path = PROJECT_ROOT / "models"
EMBEDDING_MODELS_DIR: Path = MODELS_DIR / "embedding"
RERANKER_MODELS_DIR: Path = MODELS_DIR / "reranker"
NARRATIVE_MODELS_DIR: Path = MODELS_DIR / "narrative"

LOGS_DIR: Path = PROJECT_ROOT / "logs"
RESULTS_DIR: Path = PROJECT_ROOT / "results"
DOCS_DIR: Path = PROJECT_ROOT / "docs"

DEFAULT_DB_PATH: Path = DB_DIR / "vtd_health_research_v1.db"
DEFAULT_SCHEMA_SQL_PATH: Path = DB_DIR / "vtd_health_research_schema.sql"
DEFAULT_SCHEMA_SNAPSHOT_PATH: Path = SCHEMA_DIR / "schema_snapshot.json"
DEFAULT_SCHEMA_GRAPH_PATH: Path = SCHEMA_DIR / "schema_graph.json"
DEFAULT_COLUMN_ALIASES_PATH: Path = SCHEMA_DIR / "column_aliases.fa.json"
DEFAULT_BUSINESS_GLOSSARY_PATH: Path = SCHEMA_DIR / "business_glossary.fa.json"
DEFAULT_METRIC_DEFINITIONS_PATH: Path = SCHEMA_DIR / "metric_definitions.json"

DEFAULT_GOLDEN_EXAMPLES_PATH: Path = GOLDEN_SQL_DIR / "golden_examples.jsonl"
DEFAULT_FEW_SHOT_BANK_PATH: Path = GOLDEN_SQL_DIR / "few_shot_bank.jsonl"
DEFAULT_INDEXED_EXAMPLES_PATH: Path = RAG_DATA_DIR / "indexed_examples.jsonl"


def resolve_project_path(path: str | Path) -> Path:
    """
    Resolve a project-relative path into an absolute Path.
    """
    p = Path(path)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p


def ensure_project_directories() -> None:
    """
    Create required runtime directories.
    """
    for directory in [
        DATA_DIR,
        DB_DIR,
        SCHEMA_DIR,
        QUESTIONS_DIR,
        GOLDEN_SQL_DIR,
        RAG_DATA_DIR,
        MODELS_DIR,
        LOGS_DIR,
        RESULTS_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
