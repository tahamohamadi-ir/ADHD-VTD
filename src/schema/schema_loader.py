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
