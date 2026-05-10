from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from textwrap import dedent


ROOT = Path.cwd()
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def write_file(rel_path: str, content: str) -> None:
    path = ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        old = path.read_text(encoding="utf-8", errors="ignore")
        if old.strip():
            backup = path.with_suffix(path.suffix + f".bak_{STAMP}")
            shutil.copy2(path, backup)
            print(f"Backup created: {backup}")

    path.write_text(dedent(content).lstrip(), encoding="utf-8")
    print(f"Wrote: {rel_path}")


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
''')


write_file("src/schema/schema_linker.py", r'''
from __future__ import annotations

import re
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
    4. Use controlled fuzzy matching only for meaningful tokens.
    5. Return compact schema context and join hints.
    """

    STOPWORDS = {
        "است",
        "هست",
        "هستن",
        "هستند",
        "بود",
        "بوده",
        "باشد",
        "باشند",
        "را",
        "رو",
        "به",
        "در",
        "از",
        "با",
        "برای",
        "تا",
        "که",
        "چه",
        "چی",
        "چیه",
        "چند",
        "چقدر",
        "کدام",
        "کدوم",
        "آیا",
        "ایا",
        "لطفا",
        "لطفاً",
        "بده",
        "نشان",
        "نمایش",
        "کن",
        "کنم",
        "کنید",
        "میانگین",
        "متوسط",
        "تعداد",
        "افراد",
        "فرد",
        "کمتر",
        "بیشتر",
        "بالای",
        "زیر",
        "برابر",
        "دارند",
        "دارد",
        "داشته",
        "های",
        "هایی",
        "ها",
        "؟",
        "?",
    }

    TOKEN_PATTERN = re.compile(r"[\w\u0600-\u06FF\-]+")

    def __init__(self, registry: SchemaRegistry | None = None, fuzzy_threshold: int = 88) -> None:
        self.registry = registry or SchemaRegistry()
        self.normalizer = PersianNormalizer()
        self.fuzzy_threshold = fuzzy_threshold

    def _tokens(self, text: str) -> list[str]:
        normalized = self.normalizer.normalize_for_search(text)
        tokens = self.TOKEN_PATTERN.findall(normalized)

        cleaned: list[str] = []
        for token in tokens:
            token = token.strip().lower()

            if len(token) < 3:
                continue

            if token in self.STOPWORDS:
                continue

            cleaned.append(token)

        return cleaned

    def _update_column(
        self,
        column_scores: dict[str, float],
        column_sources: dict[str, str],
        fq_column: str,
        score: float,
        source: str,
    ) -> None:
        previous_score = column_scores.get(fq_column, -1.0)

        if score > previous_score:
            column_scores[fq_column] = score
            column_sources[fq_column] = source

        # If exact match already exists, do not overwrite it with fuzzy match.
        if score == previous_score and not column_sources.get(fq_column, "").startswith("alias:"):
            column_sources[fq_column] = source

    def _alias_exact_match(self, alias_norm: str, normalized: str, tokens: set[str]) -> bool:
        if not alias_norm:
            return False

        if " " in alias_norm:
            return alias_norm in normalized

        return alias_norm in tokens

    def _can_fuzzy_match(self, token: str, alias: str) -> bool:
        alias_norm = self.normalizer.normalize_for_search(alias)

        if not alias_norm:
            return False

        if token in self.STOPWORDS or alias_norm in self.STOPWORDS:
            return False

        if len(token) < 4 or len(alias_norm) < 4:
            return False

        # Prevent matches like "است" -> "استان".
        if token[0] != alias_norm[0]:
            return False

        return True

    def link(self, question: str) -> LinkedSchema:
        normalized = self.normalizer.normalize_for_search(question)
        tokens = set(self._tokens(question))

        column_scores: dict[str, float] = {}
        column_sources: dict[str, str] = {}
        unresolved_terms: list[str] = []

        # 1) Exact alias matching
        for alias, fq_columns in self.registry.aliases.items():
            alias_norm = self.normalizer.normalize_for_search(alias)

            if self._alias_exact_match(alias_norm, normalized, tokens):
                for fq in fq_columns:
                    self._update_column(
                        column_scores,
                        column_sources,
                        fq,
                        1.0,
                        f"alias:{alias}",
                    )

        # 2) Direct column/table name matching
        for fq in self.registry.all_fq_columns():
            table, column = self.registry.split_fq_column(fq)
            column_lower = column.lower()
            table_lower = table.lower()

            if column_lower in tokens or column_lower in normalized:
                self._update_column(
                    column_scores,
                    column_sources,
                    fq,
                    0.95,
                    "direct_column_name",
                )

            if table_lower in normalized:
                for col in self.registry.get_columns(table):
                    table_fq = f"{table}.{col}"
                    self._update_column(
                        column_scores,
                        column_sources,
                        table_fq,
                        0.60,
                        "direct_table_name",
                    )

        # 3) Controlled fuzzy alias matching
        if process is not None and fuzz is not None:
            alias_keys = list(self.registry.aliases.keys())

            for token in tokens:
                candidates = [
                    alias for alias in alias_keys
                    if self._can_fuzzy_match(token, alias)
                ]

                if not candidates:
                    continue

                match = process.extractOne(token, candidates, scorer=fuzz.WRatio)
                if not match:
                    continue

                alias, score, _ = match

                if score >= self.fuzzy_threshold:
                    for fq in self.registry.aliases[alias]:
                        self._update_column(
                            column_scores,
                            column_sources,
                            fq,
                            score / 100.0,
                            f"fuzzy_alias:{alias}",
                        )

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

        # Include base table when more than one non-base table is involved or joins need identity context.
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

print("✅ Schema linker v2 patch applied.")
