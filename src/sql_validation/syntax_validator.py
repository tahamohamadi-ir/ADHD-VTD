from __future__ import annotations

try:
    import sqlglot
except Exception:  # pragma: no cover
    sqlglot = None

try:
    from src.sql_validation.validation_result import ValidationResult
except Exception:  # pragma: no cover
    from validation_result import ValidationResult

class SQLSyntaxValidator:
    def validate(self, sql: str) -> ValidationResult:
        normalized = (sql or "").strip().rstrip(";").strip()
        if not normalized:
            return ValidationResult.fail("EMPTY_SQL", "SQL is empty.")
        if sqlglot is None:
            # Fallback: syntax validator cannot deeply parse without sqlglot.
            return ValidationResult.pass_(normalized)
        try:
            expressions = sqlglot.parse(normalized, read="sqlite")
            if len(expressions) != 1:
                return ValidationResult.fail("MULTIPLE_STATEMENTS", "Exactly one SQL statement is required.")
            return ValidationResult.pass_(normalized)
        except Exception as exc:
            return ValidationResult.fail("PARSE_ERROR", f"SQL parse failed: {exc}")
