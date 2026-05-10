from __future__ import annotations

try:
    import sqlglot
    from sqlglot import exp
except Exception:  # pragma: no cover
    sqlglot = None
    exp = None

try:
    from src.schema.schema_registry import SchemaRegistry
    from src.sql_validation.validation_result import ValidationIssue, ValidationResult
except Exception:  # pragma: no cover
    from schema_registry import SchemaRegistry
    from validation_result import ValidationIssue, ValidationResult

class SQLSchemaValidator:
    OLD_TABLES = {"individuals_core", "student_metrics", "clinical_assessments", "lifestyle_risk_factors", "global_benchmarks"}

    def __init__(self, registry: SchemaRegistry | None = None) -> None:
        self.registry = registry or SchemaRegistry()

    def validate(self, sql: str) -> ValidationResult:
        normalized = (sql or "").strip().rstrip(";").strip()
        issues: list[ValidationIssue] = []
        if sqlglot is None:
            return ValidationResult.pass_(normalized)
        try:
            tree = sqlglot.parse_one(normalized, read="sqlite")
        except Exception as exc:
            return ValidationResult.fail("PARSE_ERROR", f"Cannot parse SQL for schema validation: {exc}")

        tables: dict[str, str] = {}
        for table in tree.find_all(exp.Table):
            table_name = table.name
            alias = table.alias_or_name
            tables[alias] = table_name
            tables[table_name] = table_name
            if table_name in self.OLD_TABLES:
                issues.append(ValidationIssue("OLD_TABLE_REFERENCE", f"Old/non-current table referenced: {table_name}"))
            elif not self.registry.has_table(table_name):
                issues.append(ValidationIssue("UNKNOWN_TABLE", f"Unknown table: {table_name}"))

        used_table_names = sorted(set(tables.values()))
        for column in tree.find_all(exp.Column):
            col_name = column.name
            table_ref = column.table
            if col_name == "*":
                continue
            if table_ref:
                real_table = tables.get(table_ref, table_ref)
                if self.registry.has_table(real_table) and not self.registry.has_column(real_table, col_name):
                    issues.append(ValidationIssue("UNKNOWN_COLUMN", f"Unknown column: {real_table}.{col_name}"))
            else:
                if not any(self.registry.has_column(t, col_name) for t in used_table_names):
                    issues.append(ValidationIssue("UNKNOWN_COLUMN", f"Unknown unqualified column: {col_name}"))

        return ValidationResult(not issues, issues, normalized)
