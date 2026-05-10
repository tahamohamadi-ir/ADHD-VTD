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

    def _join_columns_for_table(self, table: str) -> set[str]:
        cols: set[str] = set()

        table_info = self.get_table(table)
        for pk_col in table_info.get("primary_key", []):
            cols.add(pk_col)

        for fk in table_info.get("foreign_keys", []):
            if fk.get("column"):
                cols.add(fk["column"])

        for edge in self.graph.get("edges", []):
            if edge.get("source") == table and edge.get("source_column"):
                cols.add(edge["source_column"])
            if edge.get("target") == table and edge.get("target_column"):
                cols.add(edge["target_column"])

        return cols

    def table_ddl_context(self, tables: list[str], columns: list[str] | None = None) -> str:
        """
        Build compact schema context for prompting.

        If a table is included only for joins and has no selected semantic columns,
        include its PK/FK join columns instead of rendering an empty table.
        """
        selected_columns = set(columns or [])
        lines: list[str] = []

        for table in tables:
            if not self.has_table(table):
                continue

            table_info = self.get_table(table)
            all_columns = table_info.get("columns", {})

            selected_for_table = {
                fq.split(".", 1)[1]
                for fq in selected_columns
                if fq.startswith(f"{table}.")
            }

            if selected_columns:
                cols_to_show = set(selected_for_table)

                if not cols_to_show:
                    cols_to_show.update(self._join_columns_for_table(table))

                if not cols_to_show:
                    cols_to_show.update(list(all_columns.keys())[:3])
            else:
                cols_to_show = set(all_columns.keys())

            lines.append(f"TABLE {table}:")

            for column, meta in all_columns.items():
                if column not in cols_to_show:
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
                hint = edge.get("join_sql", "")
                if hint:
                    hints.append(hint)

        return hints
