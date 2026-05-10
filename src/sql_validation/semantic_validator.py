from __future__ import annotations

try:
    from src.sql_validation.schema_validator import SQLSchemaValidator
    from src.sql_validation.validation_result import ValidationIssue, ValidationResult
except Exception:  # pragma: no cover
    from schema_validator import SQLSchemaValidator
    from validation_result import ValidationIssue, ValidationResult

class SQLSemanticValidator:
    """Lightweight semantic alignment validator for benchmark cases.

    This is intentionally conservative. It does not prove semantic correctness; it catches obvious
    mismatches between generated SQL and expected benchmark metadata.
    """

    def __init__(self) -> None:
        self.schema_validator = SQLSchemaValidator()

    def validate_against_case(self, sql: str, case: dict) -> ValidationResult:
        base = self.schema_validator.validate(sql)
        issues = list(base.issues)
        lower = sql.lower()

        for table in case.get("expected_tables", []) or case.get("tables", []):
            if table and table.lower() not in lower:
                issues.append(ValidationIssue("MISSING_EXPECTED_TABLE", f"Expected table not referenced: {table}", "warning"))
        for column in case.get("expected_columns", []) or case.get("columns", []):
            col_name = str(column).split(".")[-1]
            if col_name and col_name.lower() not in lower:
                issues.append(ValidationIssue("MISSING_EXPECTED_COLUMN", f"Expected column not referenced: {column}", "warning"))

        hard_errors = [i for i in issues if i.severity == "error"]
        return ValidationResult(not hard_errors, issues, base.normalized_sql)
