from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from textwrap import dedent


ROOT = Path.cwd()
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_if_needed(path: Path, new_content: str) -> None:
    if path.exists():
        old_content = path.read_text(encoding="utf-8", errors="ignore")
        if old_content.strip() and old_content != new_content:
            backup_path = path.with_suffix(path.suffix + f".bak_{STAMP}")
            shutil.copy2(path, backup_path)
            print(f"Backup created: {backup_path}")


def write_file(rel_path: str, content: str) -> None:
    path = ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    content = dedent(content).lstrip()
    backup_if_needed(path, content)
    path.write_text(content, encoding="utf-8")
    print(f"Wrote: {rel_path}")


def write_json(rel_path: str, obj) -> None:
    content = json.dumps(obj, ensure_ascii=False, indent=2)
    write_file(rel_path, content + "\n")


def write_jsonl(rel_path: str, rows) -> None:
    content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    write_file(rel_path, content)


# ---------------------------------------------------------------------
# data/schema bootstrap files
# ---------------------------------------------------------------------

schema_snapshot = {
    "version": "vtd_health_research_v1",
    "dialect": "sqlite",
    "database_path": "data/db/vtd_health_research_v1.db",
    "description": "Research-grade mental health and student lifestyle Text-to-SQL schema snapshot.",
    "tables": {
        "individuals_core": {
            "description": "Base demographic table for individuals.",
            "primary_key": ["user_id"],
            "columns": {
                "user_id": {"type": "INTEGER", "semantic_type": "identifier", "description": "Unique individual identifier."},
                "age": {"type": "INTEGER", "semantic_type": "numeric", "description": "Age in years."},
                "gender": {"type": "TEXT", "semantic_type": "categorical", "values": ["Male", "Female"], "description": "Gender."},
                "country": {"type": "TEXT", "semantic_type": "categorical", "description": "Country of residence."},
                "province": {"type": "TEXT", "semantic_type": "categorical", "description": "Province or state."}
            }
        },
        "student_metrics": {
            "description": "Academic metrics for students.",
            "primary_key": ["user_id"],
            "foreign_keys": [{"column": "user_id", "ref_table": "individuals_core", "ref_column": "user_id"}],
            "columns": {
                "user_id": {"type": "INTEGER", "semantic_type": "identifier", "description": "FK to individuals_core.user_id."},
                "education_level": {"type": "TEXT", "semantic_type": "categorical", "description": "Bachelor, Master, PhD, etc."},
                "year_of_study": {"type": "INTEGER", "semantic_type": "ordinal", "description": "Current academic year."},
                "cgpa": {"type": "REAL", "semantic_type": "numeric", "description": "Cumulative GPA. Avoid hallucinating gpa; use cgpa."},
                "attendance_rate": {"type": "REAL", "semantic_type": "percentage", "description": "Attendance percentage."}
            }
        },
        "clinical_assessments": {
            "description": "Mental health assessment scores and diagnoses.",
            "primary_key": ["id"],
            "foreign_keys": [{"column": "user_id", "ref_table": "individuals_core", "ref_column": "user_id"}],
            "columns": {
                "id": {"type": "INTEGER", "semantic_type": "identifier", "description": "Assessment row identifier."},
                "user_id": {"type": "INTEGER", "semantic_type": "identifier", "description": "FK to individuals_core.user_id."},
                "assessment_date": {"type": "TEXT", "semantic_type": "date", "description": "Assessment date in ISO format."},
                "phq9_score": {"type": "INTEGER", "semantic_type": "clinical_score", "range": [0, 27], "description": "PHQ-9 depression score."},
                "gad7_score": {"type": "INTEGER", "semantic_type": "clinical_score", "range": [0, 21], "description": "GAD-7 anxiety score."},
                "depression_diagnosis": {"type": "TEXT", "semantic_type": "binary_label", "values": ["Yes", "No"], "description": "Depression diagnosis flag."},
                "anxiety_diagnosis": {"type": "TEXT", "semantic_type": "binary_label", "values": ["Yes", "No"], "description": "Anxiety diagnosis flag."},
                "stress_level": {"type": "TEXT", "semantic_type": "ordinal_category", "description": "Stress level label."}
            }
        },
        "lifestyle_risk_factors": {
            "description": "Lifestyle and behavioral risk factors.",
            "primary_key": ["user_id"],
            "foreign_keys": [{"column": "user_id", "ref_table": "individuals_core", "ref_column": "user_id"}],
            "columns": {
                "user_id": {"type": "INTEGER", "semantic_type": "identifier", "description": "FK to individuals_core.user_id."},
                "sleep_hours": {"type": "REAL", "semantic_type": "numeric", "description": "Average sleep hours."},
                "exercise_frequency": {"type": "INTEGER", "semantic_type": "numeric", "description": "Exercise frequency per week."},
                "smoking_status": {"type": "TEXT", "semantic_type": "categorical", "description": "Smoking status."},
                "social_media_hours": {"type": "REAL", "semantic_type": "numeric", "description": "Daily social media usage in hours."}
            }
        },
        "global_benchmarks": {
            "description": "Reference benchmark values for comparison.",
            "primary_key": ["id"],
            "columns": {
                "id": {"type": "INTEGER", "semantic_type": "identifier", "description": "Benchmark row identifier."},
                "metric_name": {"type": "TEXT", "semantic_type": "metric_name", "description": "Name of benchmark metric."},
                "population_group": {"type": "TEXT", "semantic_type": "categorical", "description": "Reference group."},
                "benchmark_value": {"type": "REAL", "semantic_type": "numeric", "description": "Benchmark value."},
                "source": {"type": "TEXT", "semantic_type": "text", "description": "Benchmark source."}
            }
        }
    }
}

schema_graph = {
    "version": "vtd_health_research_v1",
    "nodes": [
        {"id": "individuals_core", "type": "table", "role": "base"},
        {"id": "student_metrics", "type": "table", "role": "academic"},
        {"id": "clinical_assessments", "type": "table", "role": "clinical"},
        {"id": "lifestyle_risk_factors", "type": "table", "role": "lifestyle"},
        {"id": "global_benchmarks", "type": "table", "role": "reference"}
    ],
    "edges": [
        {
            "source": "student_metrics",
            "target": "individuals_core",
            "source_column": "user_id",
            "target_column": "user_id",
            "relationship": "many_to_one",
            "join_sql": "student_metrics.user_id = individuals_core.user_id"
        },
        {
            "source": "clinical_assessments",
            "target": "individuals_core",
            "source_column": "user_id",
            "target_column": "user_id",
            "relationship": "many_to_one",
            "join_sql": "clinical_assessments.user_id = individuals_core.user_id"
        },
        {
            "source": "lifestyle_risk_factors",
            "target": "individuals_core",
            "source_column": "user_id",
            "target_column": "user_id",
            "relationship": "many_to_one",
            "join_sql": "lifestyle_risk_factors.user_id = individuals_core.user_id"
        }
    ],
    "default_base_table": "individuals_core"
}

column_aliases = {
    "سن": ["individuals_core.age"],
    "جنسیت": ["individuals_core.gender"],
    "مرد": ["individuals_core.gender"],
    "زن": ["individuals_core.gender"],
    "کشور": ["individuals_core.country"],
    "استان": ["individuals_core.province"],
    "دانشجو": ["student_metrics.user_id"],
    "مقطع": ["student_metrics.education_level"],
    "سال تحصیل": ["student_metrics.year_of_study"],
    "معدل": ["student_metrics.cgpa"],
    "gpa": ["student_metrics.cgpa"],
    "cgpa": ["student_metrics.cgpa"],
    "حضور": ["student_metrics.attendance_rate"],
    "نرخ حضور": ["student_metrics.attendance_rate"],
    "افسردگی": ["clinical_assessments.depression_diagnosis", "clinical_assessments.phq9_score"],
    "نمره افسردگی": ["clinical_assessments.phq9_score"],
    "phq9": ["clinical_assessments.phq9_score"],
    "phq-9": ["clinical_assessments.phq9_score"],
    "اضطراب": ["clinical_assessments.anxiety_diagnosis", "clinical_assessments.gad7_score"],
    "نمره اضطراب": ["clinical_assessments.gad7_score"],
    "gad7": ["clinical_assessments.gad7_score"],
    "gad-7": ["clinical_assessments.gad7_score"],
    "استرس": ["clinical_assessments.stress_level"],
    "خواب": ["lifestyle_risk_factors.sleep_hours"],
    "ساعت خواب": ["lifestyle_risk_factors.sleep_hours"],
    "ورزش": ["lifestyle_risk_factors.exercise_frequency"],
    "سیگار": ["lifestyle_risk_factors.smoking_status"],
    "شبکه اجتماعی": ["lifestyle_risk_factors.social_media_hours"],
    "سوشال مدیا": ["lifestyle_risk_factors.social_media_hours"]
}

business_glossary = {
    "افسردگی": {
        "canonical_term": "depression",
        "preferred_columns": ["clinical_assessments.depression_diagnosis", "clinical_assessments.phq9_score"],
        "default_rule": "depression_diagnosis = 'Yes'",
        "alternative_rule": "phq9_score >= 15",
        "notes": "For diagnosis questions prefer depression_diagnosis. For severity/score questions use phq9_score."
    },
    "اضطراب": {
        "canonical_term": "anxiety",
        "preferred_columns": ["clinical_assessments.anxiety_diagnosis", "clinical_assessments.gad7_score"],
        "default_rule": "anxiety_diagnosis = 'Yes'",
        "alternative_rule": "gad7_score >= 10",
        "notes": "For diagnosis questions prefer anxiety_diagnosis. For severity/score questions use gad7_score."
    },
    "معدل": {
        "canonical_term": "cgpa",
        "preferred_columns": ["student_metrics.cgpa"],
        "anti_hallucination": ["gpa"],
        "notes": "The schema uses cgpa, not gpa."
    },
    "دانشجو": {
        "canonical_term": "student",
        "preferred_tables": ["student_metrics"],
        "notes": "Student-related questions usually require student_metrics joined with individuals_core."
    }
}

metric_definitions = {
    "count_individuals": {
        "description": "Count all individuals.",
        "sql_expression": "COUNT(*)",
        "default_table": "individuals_core",
        "aggregation": "count"
    },
    "count_students": {
        "description": "Count students with rows in student_metrics.",
        "sql_expression": "COUNT(DISTINCT student_metrics.user_id)",
        "default_table": "student_metrics",
        "aggregation": "count"
    },
    "average_age": {
        "description": "Average age.",
        "sql_expression": "AVG(individuals_core.age)",
        "default_table": "individuals_core",
        "aggregation": "avg"
    },
    "average_cgpa": {
        "description": "Average CGPA.",
        "sql_expression": "AVG(student_metrics.cgpa)",
        "default_table": "student_metrics",
        "aggregation": "avg"
    },
    "average_phq9": {
        "description": "Average depression score.",
        "sql_expression": "AVG(clinical_assessments.phq9_score)",
        "default_table": "clinical_assessments",
        "aggregation": "avg"
    },
    "average_gad7": {
        "description": "Average anxiety score.",
        "sql_expression": "AVG(clinical_assessments.gad7_score)",
        "default_table": "clinical_assessments",
        "aggregation": "avg"
    }
}

golden_examples = [
    {
        "id": "gold_001_count_students",
        "question_fa": "چند دانشجو در داده‌ها داریم؟",
        "normalized_question": "تعداد دانشجوها چقدر است؟",
        "intent": "count_query",
        "tables": ["student_metrics"],
        "columns": ["student_metrics.user_id"],
        "sql": "SELECT COUNT(DISTINCT user_id) AS student_count FROM student_metrics;",
        "difficulty": "easy",
        "chart_type": "kpi"
    },
    {
        "id": "gold_002_avg_age_male_students",
        "question_fa": "میانگین سن دانشجویان مرد چقدر است؟",
        "normalized_question": "میانگین سن دانشجویان با جنسیت Male",
        "intent": "aggregation_query",
        "tables": ["individuals_core", "student_metrics"],
        "columns": ["individuals_core.age", "individuals_core.gender", "student_metrics.user_id"],
        "sql": "SELECT AVG(i.age) AS avg_age FROM individuals_core i JOIN student_metrics s ON s.user_id = i.user_id WHERE i.gender = 'Male';",
        "difficulty": "medium",
        "chart_type": "kpi"
    },
    {
        "id": "gold_003_depression_by_province",
        "question_fa": "تعداد افراد دارای افسردگی در هر استان را بده",
        "normalized_question": "count depression diagnosis by province",
        "intent": "grouping_query",
        "tables": ["individuals_core", "clinical_assessments"],
        "columns": ["individuals_core.province", "clinical_assessments.depression_diagnosis", "clinical_assessments.user_id"],
        "sql": "SELECT i.province, COUNT(DISTINCT c.user_id) AS depression_count FROM individuals_core i JOIN clinical_assessments c ON c.user_id = i.user_id WHERE c.depression_diagnosis = 'Yes' GROUP BY i.province ORDER BY depression_count DESC;",
        "difficulty": "medium",
        "chart_type": "bar"
    },
    {
        "id": "gold_004_avg_cgpa_by_gender",
        "question_fa": "میانگین معدل دانشجویان بر اساس جنسیت چقدر است؟",
        "normalized_question": "average cgpa grouped by gender",
        "intent": "grouping_query",
        "tables": ["individuals_core", "student_metrics"],
        "columns": ["individuals_core.gender", "student_metrics.cgpa", "student_metrics.user_id"],
        "sql": "SELECT i.gender, AVG(s.cgpa) AS avg_cgpa FROM individuals_core i JOIN student_metrics s ON s.user_id = i.user_id GROUP BY i.gender ORDER BY avg_cgpa DESC;",
        "difficulty": "medium",
        "chart_type": "bar"
    }
]

indexed_examples = [
    {
        "id": row["id"],
        "text_for_embedding": f"query: {row['question_fa']} intent: {row['intent']} columns: {' '.join(row['columns'])}",
        "metadata": {
            "intent": row["intent"],
            "difficulty": row["difficulty"],
            "chart_type": row["chart_type"],
            "tables": row["tables"],
            "columns": row["columns"]
        },
        "sql": row["sql"]
    }
    for row in golden_examples
]

write_json("data/schema/schema_snapshot.json", schema_snapshot)
write_json("data/schema/schema_graph.json", schema_graph)
write_json("data/schema/column_aliases.fa.json", column_aliases)
write_json("data/schema/business_glossary.fa.json", business_glossary)
write_json("data/schema/metric_definitions.json", metric_definitions)
write_jsonl("data/golden_sql/golden_examples.jsonl", golden_examples)
write_jsonl("data/golden_sql/few_shot_bank.jsonl", golden_examples)
write_jsonl("data/rag/indexed_examples.jsonl", indexed_examples)


# ---------------------------------------------------------------------
# src/config/paths.py
# ---------------------------------------------------------------------

write_file("src/config/paths.py", r'''
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
''')


# ---------------------------------------------------------------------
# src/config/settings.py
# ---------------------------------------------------------------------

write_file("src/config/settings.py", r'''
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config.paths import (
    DEFAULT_BUSINESS_GLOSSARY_PATH,
    DEFAULT_CHROMA_PATH if False else RAG_DATA_DIR,
    DEFAULT_COLUMN_ALIASES_PATH,
    DEFAULT_DB_PATH,
    DEFAULT_GOLDEN_EXAMPLES_PATH,
    DEFAULT_INDEXED_EXAMPLES_PATH,
    DEFAULT_METRIC_DEFINITIONS_PATH,
    DEFAULT_SCHEMA_GRAPH_PATH,
    DEFAULT_SCHEMA_SNAPSHOT_PATH,
    DEFAULT_SCHEMA_SQL_PATH,
    PROJECT_ROOT,
    resolve_project_path,
)


class AppSettings(BaseSettings):
    """
    Central project settings.

    Values can be overridden using environment variables or .env.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_path: str = Field(default=str(DEFAULT_DB_PATH), alias="VTD_DB_PATH")
    schema_sql_path: str = Field(default=str(DEFAULT_SCHEMA_SQL_PATH), alias="VTD_SCHEMA_PATH")

    schema_snapshot_path: str = Field(
        default=str(DEFAULT_SCHEMA_SNAPSHOT_PATH),
        alias="VTD_SCHEMA_SNAPSHOT_PATH",
    )
    schema_graph_path: str = Field(default=str(DEFAULT_SCHEMA_GRAPH_PATH), alias="VTD_SCHEMA_GRAPH_PATH")
    column_aliases_path: str = Field(
        default=str(DEFAULT_COLUMN_ALIASES_PATH),
        alias="VTD_COLUMN_ALIASES_PATH",
    )
    business_glossary_path: str = Field(
        default=str(DEFAULT_BUSINESS_GLOSSARY_PATH),
        alias="VTD_BUSINESS_GLOSSARY_PATH",
    )
    metric_definitions_path: str = Field(
        default=str(DEFAULT_METRIC_DEFINITIONS_PATH),
        alias="VTD_METRIC_DEFINITIONS_PATH",
    )

    golden_examples_path: str = Field(
        default=str(DEFAULT_GOLDEN_EXAMPLES_PATH),
        alias="VTD_GOLDEN_EXAMPLES_PATH",
    )
    indexed_examples_path: str = Field(
        default=str(DEFAULT_INDEXED_EXAMPLES_PATH),
        alias="VTD_INDEXED_EXAMPLES_PATH",
    )

    chroma_path: str = Field(default=str(RAG_DATA_DIR / "chroma"), alias="VTD_CHROMA_PATH")

    main_llm_path: str = Field(
        default="models/qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        alias="VTD_MAIN_LLM_PATH",
    )
    fallback_llm_path: str = Field(
        default="models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
        alias="VTD_FALLBACK_LLM_PATH",
    )

    embedding_model_path: str = Field(
        default="models/embedding/multilingual-e5-small",
        alias="VTD_EMBEDDING_MODEL_PATH",
    )
    reranker_model_path: str = Field(
        default="models/reranker/bge-reranker-base",
        alias="VTD_RERANKER_MODEL_PATH",
    )

    max_retries: int = Field(default=3, alias="VTD_MAX_RETRIES")
    default_limit: int = Field(default=100, alias="VTD_DEFAULT_LIMIT")
    log_level: str = Field(default="INFO", alias="VTD_LOG_LEVEL")

    @property
    def db(self) -> Path:
        return resolve_project_path(self.db_path)

    @property
    def schema_sql(self) -> Path:
        return resolve_project_path(self.schema_sql_path)

    @property
    def schema_snapshot(self) -> Path:
        return resolve_project_path(self.schema_snapshot_path)

    @property
    def schema_graph(self) -> Path:
        return resolve_project_path(self.schema_graph_path)

    @property
    def column_aliases(self) -> Path:
        return resolve_project_path(self.column_aliases_path)

    @property
    def business_glossary(self) -> Path:
        return resolve_project_path(self.business_glossary_path)

    @property
    def metric_definitions(self) -> Path:
        return resolve_project_path(self.metric_definitions_path)

    @property
    def golden_examples(self) -> Path:
        return resolve_project_path(self.golden_examples_path)

    @property
    def indexed_examples(self) -> Path:
        return resolve_project_path(self.indexed_examples_path)

    @property
    def chroma(self) -> Path:
        return resolve_project_path(self.chroma_path)


settings = AppSettings()
''')


# Fix accidental import trick in settings.py after writing
settings_path = ROOT / "src/config/settings.py"
settings_text = settings_path.read_text(encoding="utf-8")
settings_text = settings_text.replace(
    "    DEFAULT_CHROMA_PATH if False else RAG_DATA_DIR,\n",
    "    RAG_DATA_DIR,\n",
)
settings_path.write_text(settings_text, encoding="utf-8")


# ---------------------------------------------------------------------
# src/core/types.py
# ---------------------------------------------------------------------

write_file("src/core/types.py", r'''
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    COUNT = "count_query"
    AGGREGATION = "aggregation_query"
    GROUPING = "grouping_query"
    RANKING = "ranking_query"
    TREND = "trend_query"
    COMPARISON = "comparison_query"
    RAW_RETRIEVAL = "raw_data_query"
    CHART = "chart_request"
    CLARIFICATION = "clarification_required"
    OUT_OF_SCHEMA = "out_of_schema_query"
    UNSAFE = "unsafe_query"
    UNKNOWN = "unknown"


class QueryComplexity(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXTRA_HARD = "extra_hard"


class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNSAFE = "unsafe"
    NEEDS_CLARIFICATION = "needs_clarification"


class ErrorType(str, Enum):
    NONE = "none"
    SYNTAX = "syntax_error"
    SCHEMA = "schema_error"
    SAFETY = "safety_error"
    SEMANTIC = "semantic_error"
    EXECUTION = "execution_error"
    AMBIGUITY = "ambiguity_error"


class DateRange(BaseModel):
    original_text: str
    start_date: str
    end_date: str
    calendar: Literal["jalali", "gregorian", "unknown"] = "jalali"
    granularity: Literal["day", "month", "year", "range"] = "range"


class NormalizationResult(BaseModel):
    raw_text: str
    normalized_text: str
    detected_date_ranges: list[DateRange] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class IntentClassification(BaseModel):
    intent: IntentType
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    complexity: QueryComplexity = QueryComplexity.EASY
    hints: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None


class ColumnRef(BaseModel):
    table: str
    column: str
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "unknown"

    @property
    def fqdn(self) -> str:
        return f"{self.table}.{self.column}"


class TableRef(BaseModel):
    table: str
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "unknown"


class LinkedSchema(BaseModel):
    tables: list[TableRef] = Field(default_factory=list)
    columns: list[ColumnRef] = Field(default_factory=list)
    join_hints: list[str] = Field(default_factory=list)
    schema_context: str = ""
    unresolved_terms: list[str] = Field(default_factory=list)


class RetrievedExample(BaseModel):
    id: str
    question: str
    sql: str
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeneratedSQL(BaseModel):
    sql: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    assumptions: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None


class ValidationIssue(BaseModel):
    error_type: ErrorType
    message: str
    severity: Literal["info", "warning", "error", "critical"] = "error"
    hint: str | None = None


class ValidationResult(BaseModel):
    status: ValidationStatus
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.status == ValidationStatus.VALID and not self.issues


class ExecutionResult(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float | None = None
    error: str | None = None


class AttemptRecord(BaseModel):
    iteration: int
    sql: str | None = None
    validation_result: ValidationResult | None = None
    execution_error: str | None = None
    critic_feedback: str | None = None


class PipelineTrace(BaseModel):
    question: str
    normalized: NormalizationResult | None = None
    intent: IntentClassification | None = None
    linked_schema: LinkedSchema | None = None
    retrieved_examples: list[RetrievedExample] = Field(default_factory=list)
    generated_sql: GeneratedSQL | None = None
    attempts: list[AttemptRecord] = Field(default_factory=list)
    execution_result: ExecutionResult | None = None
    final_answer: str | None = None
''')


# ---------------------------------------------------------------------
# src/nlu/persian_normalizer.py
# ---------------------------------------------------------------------

write_file("src/nlu/persian_normalizer.py", r'''
from __future__ import annotations

import re
import unicodedata

from src.core.types import NormalizationResult


class PersianNormalizer:
    """
    Persian-first text normalizer for Text-to-SQL.

    Responsibilities:
    - Arabic/Persian character unification
    - ZWNJ handling
    - Arabic/Persian digit normalization is delegated to NumberNormalizer
    - Basic punctuation and whitespace cleanup
    """

    ARABIC_TO_PERSIAN = str.maketrans(
        {
            "ك": "ک",
            "ي": "ی",
            "ى": "ی",
            "ۀ": "ه",
            "ة": "ه",
            "ؤ": "و",
            "إ": "ا",
            "أ": "ا",
            "آ": "آ",
        }
    )

    DIACRITICS_PATTERN = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")
    ZWNJ_PATTERN = re.compile(r"[\u200c\u200d]")
    MULTISPACE_PATTERN = re.compile(r"\s+")

    PUNCT_TRANSLATION = str.maketrans(
        {
            "؟": "?",
            "،": ",",
            "؛": ";",
            "٬": ",",
            "٫": ".",
            "“": '"',
            "”": '"',
            "’": "'",
        }
    )

    def __init__(self, replace_zwnj_with_space: bool = True) -> None:
        self.replace_zwnj_with_space = replace_zwnj_with_space

    def normalize(self, text: str) -> NormalizationResult:
        raw = text or ""
        normalized = self.normalize_text(raw)
        notes: list[str] = []

        if raw != normalized:
            notes.append("Persian text normalized.")

        return NormalizationResult(
            raw_text=raw,
            normalized_text=normalized,
            detected_date_ranges=[],
            notes=notes,
        )

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""

        text = unicodedata.normalize("NFKC", text)
        text = text.translate(self.ARABIC_TO_PERSIAN)
        text = text.translate(self.PUNCT_TRANSLATION)
        text = self.DIACRITICS_PATTERN.sub("", text)

        if self.replace_zwnj_with_space:
            text = self.ZWNJ_PATTERN.sub(" ", text)
        else:
            text = self.ZWNJ_PATTERN.sub("\u200c", text)

        text = self.MULTISPACE_PATTERN.sub(" ", text)
        return text.strip()

    def normalize_for_search(self, text: str) -> str:
        text = self.normalize_text(text).lower()
        text = re.sub(r"[^\w\s\-.]", " ", text, flags=re.UNICODE)
        text = self.MULTISPACE_PATTERN.sub(" ", text)
        return text.strip()


def normalize_persian(text: str) -> str:
    return PersianNormalizer().normalize_text(text)
''')


# ---------------------------------------------------------------------
# src/nlu/number_normalizer.py
# ---------------------------------------------------------------------

write_file("src/nlu/number_normalizer.py", r'''
from __future__ import annotations

import re


class NumberNormalizer:
    """
    Converts Persian and Arabic digits into Western digits.

    This component intentionally keeps complex Persian number-word parsing minimal.
    """

    DIGIT_MAP = str.maketrans(
        {
            "۰": "0",
            "۱": "1",
            "۲": "2",
            "۳": "3",
            "۴": "4",
            "۵": "5",
            "۶": "6",
            "۷": "7",
            "۸": "8",
            "۹": "9",
            "٠": "0",
            "١": "1",
            "٢": "2",
            "٣": "3",
            "٤": "4",
            "٥": "5",
            "٦": "6",
            "٧": "7",
            "٨": "8",
            "٩": "9",
        }
    )

    SIMPLE_WORD_NUMBERS = {
        "صفر": 0,
        "یک": 1,
        "یه": 1,
        "دو": 2,
        "سه": 3,
        "چهار": 4,
        "پنج": 5,
        "شش": 6,
        "شیش": 6,
        "هفت": 7,
        "هشت": 8,
        "نه": 9,
        "ده": 10,
        "یازده": 11,
        "دوازده": 12,
        "سیزده": 13,
        "چهارده": 14,
        "پانزده": 15,
        "شانزده": 16,
        "هفده": 17,
        "هجده": 18,
        "نوزده": 19,
        "بیست": 20,
    }

    NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?")

    def normalize_digits(self, text: str) -> str:
        if not text:
            return ""
        return text.translate(self.DIGIT_MAP)

    def replace_simple_number_words(self, text: str) -> str:
        if not text:
            return ""

        result = text
        for word, number in sorted(self.SIMPLE_WORD_NUMBERS.items(), key=lambda x: len(x[0]), reverse=True):
            result = re.sub(rf"\b{re.escape(word)}\b", str(number), result)
        return result

    def normalize(self, text: str, replace_words: bool = False) -> str:
        text = self.normalize_digits(text)
        if replace_words:
            text = self.replace_simple_number_words(text)
        return text

    def extract_numbers(self, text: str) -> list[float]:
        text = self.normalize_digits(text)
        values: list[float] = []

        for match in self.NUMBER_PATTERN.findall(text):
            if "." in match:
                values.append(float(match))
            else:
                values.append(float(int(match)))

        return values


def normalize_digits(text: str) -> str:
    return NumberNormalizer().normalize_digits(text)
''')


# ---------------------------------------------------------------------
# src/nlu/date_normalizer.py
# ---------------------------------------------------------------------

write_file("src/nlu/date_normalizer.py", r'''
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

from src.core.types import DateRange
from src.nlu.number_normalizer import NumberNormalizer
from src.nlu.persian_normalizer import PersianNormalizer

try:
    from persiantools.jdatetime import JalaliDate
except Exception:  # pragma: no cover
    JalaliDate = None


class PersianDateNormalizer:
    """
    Converts common Persian/Jalali date expressions into Gregorian ISO ranges.

    Supported examples:
    - 1404/01/15
    - ۱۴۰۴-۰۱-۱۵
    - فروردین ۱۴۰۴
    - سال ۱۴۰۴
    """

    MONTHS = {
        "فروردین": 1,
        "اردیبهشت": 2,
        "خرداد": 3,
        "تیر": 4,
        "مرداد": 5,
        "شهریور": 6,
        "مهر": 7,
        "آبان": 8,
        "اذر": 9,
        "آذر": 9,
        "دی": 10,
        "بهمن": 11,
        "اسفند": 12,
    }

    DATE_PATTERN = re.compile(r"(?P<year>13\d{2}|14\d{2})[/-](?P<month>\d{1,2})[/-](?P<day>\d{1,2})")
    MONTH_YEAR_PATTERN = re.compile(r"(?P<month_name>فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|اذر|آذر|دی|بهمن|اسفند)\s+(?P<year>13\d{2}|14\d{2})")
    YEAR_PATTERN = re.compile(r"(?:سال\s+)?(?P<year>13\d{2}|14\d{2})")

    def __init__(self) -> None:
        self.persian_normalizer = PersianNormalizer()
        self.number_normalizer = NumberNormalizer()

    def normalize_text_dates(self, text: str) -> tuple[str, list[DateRange]]:
        normalized = self.persian_normalizer.normalize_text(text)
        normalized = self.number_normalizer.normalize_digits(normalized)

        ranges: list[DateRange] = []

        for match in self.DATE_PATTERN.finditer(normalized):
            year = int(match.group("year"))
            month = int(match.group("month"))
            day = int(match.group("day"))
            start = self.jalali_to_gregorian(year, month, day)
            end = start + timedelta(days=1)
            ranges.append(
                DateRange(
                    original_text=match.group(0),
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                    calendar="jalali",
                    granularity="day",
                )
            )

        for match in self.MONTH_YEAR_PATTERN.finditer(normalized):
            month_name = match.group("month_name")
            year = int(match.group("year"))
            month = self.MONTHS[month_name]
            start = self.jalali_to_gregorian(year, month, 1)

            if month == 12:
                next_year, next_month = year + 1, 1
            else:
                next_year, next_month = year, month + 1

            end = self.jalali_to_gregorian(next_year, next_month, 1)
            ranges.append(
                DateRange(
                    original_text=match.group(0),
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                    calendar="jalali",
                    granularity="month",
                )
            )

        return normalized, ranges

    def jalali_to_gregorian(self, year: int, month: int, day: int) -> date:
        if JalaliDate is None:
            raise RuntimeError("persiantools is required for Jalali date conversion.")
        return JalaliDate(year, month, day).to_gregorian()

    def gregorian_month_range(self, year: int, month: int) -> tuple[date, date]:
        last_day = calendar.monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, last_day) + timedelta(days=1)
        return start, end


def normalize_persian_dates(text: str) -> tuple[str, list[DateRange]]:
    return PersianDateNormalizer().normalize_text_dates(text)
''')


# ---------------------------------------------------------------------
# src/db/schema_inspector.py
# ---------------------------------------------------------------------

write_file("src/db/schema_inspector.py", r'''
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from src.config.paths import DEFAULT_DB_PATH, DEFAULT_SCHEMA_SNAPSHOT_PATH, resolve_project_path


class SQLiteSchemaInspector:
    """
    Inspects a SQLite database and exports a schema snapshot usable by schema linking.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = resolve_project_path(db_path)

    def connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        return sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row[0] for row in rows]

    def inspect_table(self, table_name: str) -> dict[str, Any]:
        with self.connect() as conn:
            column_rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            fk_rows = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()

        columns: dict[str, Any] = {}
        primary_key: list[str] = []

        for cid, name, col_type, notnull, default_value, pk in column_rows:
            columns[name] = {
                "type": col_type or "UNKNOWN",
                "not_null": bool(notnull),
                "default": default_value,
                "primary_key_position": int(pk),
            }
            if pk:
                primary_key.append(name)

        foreign_keys = [
            {
                "column": row[3],
                "ref_table": row[2],
                "ref_column": row[4],
            }
            for row in fk_rows
        ]

        return {
            "description": "",
            "primary_key": primary_key,
            "foreign_keys": foreign_keys,
            "columns": columns,
        }

    def export_snapshot(self) -> dict[str, Any]:
        tables = {table: self.inspect_table(table) for table in self.list_tables()}
        return {
            "version": "generated_from_sqlite",
            "dialect": "sqlite",
            "database_path": str(self.db_path),
            "tables": tables,
        }

    def write_snapshot(self, output_path: str | Path = DEFAULT_SCHEMA_SNAPSHOT_PATH) -> Path:
        output = resolve_project_path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        snapshot = self.export_snapshot()
        output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--out", default=str(DEFAULT_SCHEMA_SNAPSHOT_PATH))
    args = parser.parse_args()

    inspector = SQLiteSchemaInspector(args.db)
    output = inspector.write_snapshot(args.out)
    print(f"Schema snapshot written to: {output}")


if __name__ == "__main__":
    main()
''')


# ---------------------------------------------------------------------
# src/schema/schema_loader.py
# ---------------------------------------------------------------------

write_file("src/schema/schema_loader.py", r'''
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config.paths import (
    DEFAULT_BUSINESS_GLOSSARY_PATH,
    DEFAULT_COLUMN_ALIASES_PATH,
    DEFAULT_METRIC_DEFINITIONS_PATH,
    DEFAULT_SCHEMA_GRAPH_PATH,
    DEFAULT_SCHEMA_SNAPSHOT_PATH,
    DEFAULT_SCHEMA_SQL_PATH,
    resolve_project_path,
)


class SchemaLoader:
    """
    Loads schema-related artifacts from data/schema and data/db.
    """

    def load_json(self, path: str | Path) -> dict[str, Any]:
        resolved = resolve_project_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"JSON file not found: {resolved}")
        return json.loads(resolved.read_text(encoding="utf-8"))

    def load_schema_snapshot(self, path: str | Path = DEFAULT_SCHEMA_SNAPSHOT_PATH) -> dict[str, Any]:
        return self.load_json(path)

    def load_schema_graph(self, path: str | Path = DEFAULT_SCHEMA_GRAPH_PATH) -> dict[str, Any]:
        return self.load_json(path)

    def load_column_aliases(self, path: str | Path = DEFAULT_COLUMN_ALIASES_PATH) -> dict[str, list[str]]:
        return self.load_json(path)

    def load_business_glossary(self, path: str | Path = DEFAULT_BUSINESS_GLOSSARY_PATH) -> dict[str, Any]:
        return self.load_json(path)

    def load_metric_definitions(self, path: str | Path = DEFAULT_METRIC_DEFINITIONS_PATH) -> dict[str, Any]:
        return self.load_json(path)

    def load_schema_sql(self, path: str | Path = DEFAULT_SCHEMA_SQL_PATH) -> str:
        resolved = resolve_project_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Schema SQL file not found: {resolved}")
        return resolved.read_text(encoding="utf-8")
''')


# ---------------------------------------------------------------------
# src/schema/schema_registry.py
# ---------------------------------------------------------------------

write_file("src/schema/schema_registry.py", r'''
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.schema.schema_loader import SchemaLoader


@dataclass
class SchemaRegistry:
    """
    In-memory registry for schema snapshot, schema graph, aliases, glossary, and metrics.
    """

    loader: SchemaLoader = field(default_factory=SchemaLoader)
    snapshot: dict[str, Any] = field(init=False)
    graph: dict[str, Any] = field(init=False)
    aliases: dict[str, list[str]] = field(init=False)
    glossary: dict[str, Any] = field(init=False)
    metrics: dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        self.snapshot = self.loader.load_schema_snapshot()
        self.graph = self.loader.load_schema_graph()
        self.aliases = self.loader.load_column_aliases()
        self.glossary = self.loader.load_business_glossary()
        self.metrics = self.loader.load_metric_definitions()

    @property
    def tables(self) -> dict[str, Any]:
        return self.snapshot.get("tables", {})

    def has_table(self, table: str) -> bool:
        return table in self.tables

    def get_table(self, table: str) -> dict[str, Any]:
        if table not in self.tables:
            raise KeyError(f"Unknown table: {table}")
        return self.tables[table]

    def get_columns(self, table: str) -> dict[str, Any]:
        return self.get_table(table).get("columns", {})

    def has_column(self, table: str, column: str) -> bool:
        return self.has_table(table) and column in self.get_columns(table)

    def all_fq_columns(self) -> list[str]:
        cols: list[str] = []
        for table, table_info in self.tables.items():
            for column in table_info.get("columns", {}):
                cols.append(f"{table}.{column}")
        return cols

    def split_fq_column(self, fq_column: str) -> tuple[str, str]:
        if "." not in fq_column:
            raise ValueError(f"Expected fully-qualified column, got: {fq_column}")
        table, column = fq_column.split(".", 1)
        return table, column

    def resolve_alias(self, term: str) -> list[str]:
        return self.aliases.get(term, [])

    def table_ddl_context(self, tables: list[str], columns: list[str] | None = None) -> str:
        """
        Build compact schema context for prompting.
        """
        selected_columns = set(columns or [])
        lines: list[str] = []

        for table in tables:
            if not self.has_table(table):
                continue

            table_info = self.get_table(table)
            lines.append(f"TABLE {table}:")

            for column, meta in table_info.get("columns", {}).items():
                fq = f"{table}.{column}"
                if selected_columns and fq not in selected_columns:
                    continue
                col_type = meta.get("type", "UNKNOWN")
                desc = meta.get("description", "")
                lines.append(f"  - {column} ({col_type}): {desc}")

        return "\n".join(lines)

    def join_hints_for_tables(self, tables: list[str]) -> list[str]:
        table_set = set(tables)
        hints: list[str] = []

        for edge in self.graph.get("edges", []):
            source = edge.get("source")
            target = edge.get("target")
            if source in table_set and target in table_set:
                hints.append(edge.get("join_sql", ""))

        return [h for h in hints if h]
''')


# ---------------------------------------------------------------------
# src/schema/schema_linker.py
# ---------------------------------------------------------------------

write_file("src/schema/schema_linker.py", r'''
from __future__ import annotations

from collections import defaultdict

from src.core.types import ColumnRef, LinkedSchema, TableRef
from src.nlu.persian_normalizer import PersianNormalizer
from src.schema.schema_registry import SchemaRegistry

try:
    from rapidfuzz import fuzz, process
except Exception:  # pragma: no cover
    fuzz = None
    process = None


class SchemaLinker:
    """
    Persian-aware schema linker.

    Strategy:
    1. Normalize question.
    2. Match explicit aliases from column_aliases.fa.json.
    3. Match direct table/column names.
    4. Optional fuzzy matching for near-miss Persian terms.
    5. Return compact schema context and join hints.
    """

    def __init__(self, registry: SchemaRegistry | None = None, fuzzy_threshold: int = 85) -> None:
        self.registry = registry or SchemaRegistry()
        self.normalizer = PersianNormalizer()
        self.fuzzy_threshold = fuzzy_threshold

    def link(self, question: str) -> LinkedSchema:
        normalized = self.normalizer.normalize_for_search(question)

        column_scores: dict[str, float] = {}
        column_sources: dict[str, str] = {}
        unresolved_terms: list[str] = []

        # 1) Exact alias matching
        for alias, fq_columns in self.registry.aliases.items():
            alias_norm = self.normalizer.normalize_for_search(alias)
            if alias_norm and alias_norm in normalized:
                for fq in fq_columns:
                    column_scores[fq] = max(column_scores.get(fq, 0.0), 1.0)
                    column_sources[fq] = f"alias:{alias}"

        # 2) Direct column/table name matching
        for fq in self.registry.all_fq_columns():
            table, column = self.registry.split_fq_column(fq)
            if column.lower() in normalized:
                column_scores[fq] = max(column_scores.get(fq, 0.0), 0.95)
                column_sources[fq] = "direct_column_name"

            if table.lower() in normalized:
                for col in self.registry.get_columns(table):
                    table_fq = f"{table}.{col}"
                    column_scores[table_fq] = max(column_scores.get(table_fq, 0.0), 0.60)
                    column_sources[table_fq] = "direct_table_name"

        # 3) Fuzzy alias matching
        if process is not None and fuzz is not None:
            alias_keys = list(self.registry.aliases.keys())
            for token in normalized.split():
                if len(token) < 3:
                    continue

                match = process.extractOne(token, alias_keys, scorer=fuzz.WRatio)
                if match:
                    alias, score, _ = match
                    if score >= self.fuzzy_threshold:
                        for fq in self.registry.aliases[alias]:
                            column_scores[fq] = max(column_scores.get(fq, 0.0), score / 100.0)
                            column_sources[fq] = f"fuzzy_alias:{alias}"

        table_scores: dict[str, float] = defaultdict(float)

        columns: list[ColumnRef] = []
        for fq, score in sorted(column_scores.items(), key=lambda item: item[1], reverse=True):
            table, column = self.registry.split_fq_column(fq)
            if self.registry.has_column(table, column):
                columns.append(
                    ColumnRef(
                        table=table,
                        column=column,
                        score=score,
                        source=column_sources.get(fq, "unknown"),
                    )
                )
                table_scores[table] = max(table_scores[table], score)

        # Always include base table when joins may be needed
        if columns and "individuals_core" not in table_scores:
            table_scores["individuals_core"] = 0.50

        tables = [
            TableRef(table=table, score=score, source="derived_from_columns")
            for table, score in sorted(table_scores.items(), key=lambda item: item[1], reverse=True)
            if self.registry.has_table(table)
        ]

        table_names = [t.table for t in tables]
        fq_columns = [c.fqdn for c in columns]

        join_hints = self.registry.join_hints_for_tables(table_names)
        schema_context = self.registry.table_ddl_context(table_names, fq_columns)

        return LinkedSchema(
            tables=tables,
            columns=columns,
            join_hints=join_hints,
            schema_context=schema_context,
            unresolved_terms=unresolved_terms,
        )
''')


print("\n✅ Foundation files generated successfully.")
print("Next:")
print("  python -m src.db.schema_inspector --db data/db/vtd_health_research_v1.db --out data/schema/schema_snapshot.generated.json")
print("  python - <<'PY'")
print("  from src.schema.schema_linker import SchemaLinker")
print("  print(SchemaLinker().link('میانگین نمره افسردگی دانشجویان زن چقدر است؟').model_dump())")
print("  PY")
