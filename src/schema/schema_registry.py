from __future__ import annotations

import json
from pathlib import Path

try:
    from src.config.paths import SCHEMA_SNAPSHOT_PATH, SCHEMA_GRAPH_PATH, SCHEMA_DIR
except Exception:  # pragma: no cover
    SCHEMA_SNAPSHOT_PATH = Path("data/schema/schema_snapshot.json")
    SCHEMA_GRAPH_PATH = Path("data/schema/schema_graph.json")
    SCHEMA_DIR = Path("data/schema")

class SchemaRegistry:
    """Current-schema registry. Source of truth: schema_snapshot.json."""

    def __init__(self, snapshot_path: str | Path | None = None, schema_dir: str | Path | None = None) -> None:
        self.snapshot_path = Path(snapshot_path or SCHEMA_SNAPSHOT_PATH)
        self.schema_dir = Path(schema_dir or SCHEMA_DIR)
        self.snapshot = self._load_json(self.snapshot_path)
        self.tables = self._table_map()
        self.aliases = self._load_json(self.schema_dir / "column_aliases.fa.json")
        self.metrics = self._load_json(self.schema_dir / "metric_definitions.json")

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _table_map(self) -> dict[str, dict]:
        return {t["name"]: t for t in self.snapshot.get("tables", []) if t.get("name")}

    def has_table(self, table: str) -> bool:
        return table in self.tables

    def has_column(self, table: str, column: str) -> bool:
        return column in self.columns_for_table(table)

    def columns_for_table(self, table: str) -> set[str]:
        t = self.tables.get(table, {})
        return {c["name"] for c in t.get("columns", []) if c.get("name")}

    def all_columns(self) -> set[str]:
        return {f"{t}.{c}" for t in self.tables for c in self.columns_for_table(t)}

    def validate_fq_column(self, fq: str) -> bool:
        if "." not in fq:
            return False
        table, column = fq.split(".", 1)
        return self.has_column(table, column)

    def resolve_aliases(self, text: str) -> list[str]:
        matches: list[str] = []
        lower = text.lower()
        for alias, cols in self.aliases.items():
            if alias.lower() in lower:
                matches.extend(cols)
        return [c for c in dict.fromkeys(matches) if self.validate_fq_column(c)]

    def ddl_context(self, tables: list[str], columns: list[str] | None = None) -> str:
        selected_cols = set(columns or [])
        chunks: list[str] = []
        for table in tables:
            if not self.has_table(table):
                continue
            t = self.tables[table]
            chunks.append(f"TABLE {table}")
            for col in t.get("columns", []):
                fq = f"{table}.{col['name']}"
                if not selected_cols or fq in selected_cols or col.get("primary_key"):
                    chunks.append(f"- {col['name']} {col.get('type','')}")
        return "\n".join(chunks)
