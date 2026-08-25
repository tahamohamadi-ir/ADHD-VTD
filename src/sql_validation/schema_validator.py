from __future__ import annotations

import difflib

import sqlglot
from sqlglot import exp

from src.schema.schema_registry import SchemaRegistry
from src.sql_validation.validation_result import RepairHint, ValidationIssue, ValidationResult


def _closest(candidates: list[str], value: str) -> str | None:
    matches = difflib.get_close_matches(value, candidates, n=1, cutoff=0.6)
    return matches[0] if matches else None


class SQLSchemaValidator:
    OLD_TABLES = {
        "individuals_core",
        "student_metrics",
        "clinical_assessments",
        "lifestyle_risk_factors",
        "global_benchmarks",
    }

    def __init__(self, registry: SchemaRegistry | None = None) -> None:
        self.registry = registry or SchemaRegistry()

    def validate(self, sql: str) -> ValidationResult:
        normalized = (sql or "").strip().rstrip(";").strip()
        issues: list[ValidationIssue] = []
        hints: list[RepairHint] = []
        if sqlglot is None:
            return ValidationResult.pass_(normalized)
        try:
            tree = sqlglot.parse_one(normalized, read="sqlite")
        except Exception as exc:
            return ValidationResult.fail(
                "PARSE_ERROR", f"Cannot parse SQL for schema validation: {exc}"
            )

        # Get CTEs
        ctes = {cte.alias for cte in tree.find_all(exp.CTE)}

        # Get SELECT aliases
        select_aliases = {alias.alias for alias in tree.find_all(exp.Alias)}

        known_tables = [t.lower() for t in self.registry.table_names()]

        tables: dict[str, str] = {}
        for table in tree.find_all(exp.Table):
            table_name = table.name.lower()
            if table_name in ctes:
                continue
            alias = table.alias_or_name.lower()
            tables[alias] = table_name
            tables[table_name] = table_name
            if table_name in self.OLD_TABLES:
                issues.append(
                    ValidationIssue(
                        "OLD_TABLE_REFERENCE", f"Old/non-current table referenced: {table.name}"
                    )
                )
            elif not self.registry.has_table(table_name):
                issues.append(ValidationIssue("UNKNOWN_TABLE", f"Unknown table: {table.name}"))
                close = _closest(known_tables, table_name)
                if close:
                    hints.append(
                        RepairHint(
                            action="use_table",
                            target=table.name,
                            suggestion=close,
                            confidence=0.6,
                        )
                    )

        used_table_names = sorted(set(tables.values()))
        hinted_columns: set[tuple[str, str]] = set()
        for column in tree.find_all(exp.Column):
            col_name = column.name.lower()
            table_ref = column.table.lower() if column.table else ""
            if col_name == "*" or col_name in select_aliases:
                continue
            if table_ref:
                real_table = tables.get(table_ref, table_ref)
                if self.registry.has_table(real_table) and not self.registry.has_column(
                    real_table, col_name
                ):
                    issues.append(
                        ValidationIssue(
                            "UNKNOWN_COLUMN", f"Unknown column: {column.table}.{column.name}"
                        )
                    )
                    hint_key = (real_table, col_name)
                    if hint_key not in hinted_columns:
                        close = _closest(
                            [c.lower() for c in self.registry.columns_for_table(real_table)],
                            col_name,
                        )
                        if close:
                            hinted_columns.add(hint_key)
                            hints.append(
                                RepairHint(
                                    action="replace_column",
                                    target=f"{column.table}.{column.name}",
                                    suggestion=close,
                                    confidence=0.6,
                                )
                            )
            else:
                if not any(self.registry.has_column(t, col_name) for t in used_table_names):
                    issues.append(
                        ValidationIssue(
                            "UNKNOWN_COLUMN", f"Unknown unqualified column: {column.name}"
                        )
                    )
                    hint_key = ("*", col_name)
                    if hint_key not in hinted_columns:
                        for t in used_table_names:
                            if not self.registry.has_table(t):
                                continue
                            close = _closest(
                                [c.lower() for c in self.registry.columns_for_table(t)],
                                col_name,
                            )
                            if close:
                                hinted_columns.add(hint_key)
                                hints.append(
                                    RepairHint(
                                        action="replace_column",
                                        target=column.name,
                                        suggestion=close,
                                        confidence=0.6,
                                    )
                                )
                                break

        result = ValidationResult(not issues, issues, normalized)
        if hints:
            result = result.with_hints(tuple(hints))
        return result
