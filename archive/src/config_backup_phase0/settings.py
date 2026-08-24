from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config.paths import (
    DEFAULT_BUSINESS_GLOSSARY_PATH,
    RAG_DATA_DIR,
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
