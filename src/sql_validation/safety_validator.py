from __future__ import annotations

import re
from typing import Any

try:
    import sqlglot
    from sqlglot import exp
except Exception:  # pragma: no cover
    sqlglot = None  # type: ignore[assignment]
    exp = None  # type: ignore[assignment]

try:
    from src.sql_validation.validation_result import ValidationIssue, ValidationResult
except Exception:  # pragma: no cover
    from validation_result import ValidationIssue, ValidationResult


class SQLSafetyValidator:
    """Deterministic safety guard for generated SQL.

    Policy:
    - Only SELECT / WITH ... SELECT is allowed.
    - Mutating/administrative SQL is rejected.
    - Multiple statements and SQL comments are rejected.
    - Top-level raw `SELECT *` and `SELECT table.*` are rejected for privacy.
    - `COUNT(*)` is allowed because it is an aggregate expression, not raw row exposure.
    - Internal CTE `SELECT *` is allowed when the final top-level projection is explicit.

    This validator is intentionally conservative for user-visible outputs, while
    still allowing benchmark/gold SQL patterns that use CTEs internally.
    """

    FORBIDDEN = {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "truncate",
        "replace",
        "merge",
        "attach",
        "detach",
        "pragma",
        "vacuum",
        "reindex",
        "exec",
        "execute",
        "call",
    }
    IDENTIFIER_COLUMN_NAMES = {
        "id",
        "student_id",
        "email",
        "phone",
        "phone_number",
        "address",
    }
    IDENTIFIER_SUFFIXES = ("_id",)
    SENSITIVE_COLUMN_TERMS = (
        "suicid",
        "depression",
        "anxiety",
        "stress",
        "risk",
        "diagnosis",
        "treatment",
        "mental_health",
        "family_history",
    )

    def __init__(
        self,
        allow_select_star: bool = False,
        require_limit_for_raw: bool = True,
        default_limit: int = 100,
    ) -> None:
        self.allow_select_star = allow_select_star
        self.require_limit_for_raw = require_limit_for_raw
        self.default_limit = default_limit

    def _strip_sql(self, sql: str) -> str:
        return (sql or "").strip().rstrip(";").strip()

    def _top_level_select_has_star_fallback(self, sql: str) -> bool:
        """Fallback when sqlglot is unavailable.

        This catches only raw top-level SELECT-star projections. It must not
        reject aggregate COUNT(*). It intentionally does not reject CTE-internal
        SELECT * in `WITH x AS (SELECT * ...) SELECT ...`.
        """
        s = self._strip_sql(sql)
        lower = s.lower()
        if lower.startswith("with"):
            return False
        return bool(re.match(r"^\s*select\s+([a-zA-Z_][\w]*\.)?\*\b", lower))

    def _is_projection_star(self, projection: Any) -> bool:
        """Return True only when the top-level projection itself exposes raw *.

        Important distinction:
        - SELECT *                  -> True
        - SELECT table.*            -> True
        - SELECT * AS x             -> True, unusual but raw
        - SELECT COUNT(*) AS n      -> False
        - SELECT SUM(CASE ...)      -> False
        """
        if exp is None:
            return False

        # SELECT *
        if isinstance(projection, exp.Star):
            return True

        # SELECT table.* is typically represented as an exp.Column with Star as `this`.
        if isinstance(projection, exp.Column) and isinstance(
            getattr(projection, "this", None), exp.Star
        ):
            return True

        # SELECT * AS alias, or SELECT table.* AS alias. Do not inspect generic
        # Alias.this recursively, otherwise COUNT(*) would be incorrectly blocked.
        if isinstance(projection, exp.Alias):
            inner = getattr(projection, "this", None)
            if isinstance(inner, exp.Star):
                return True
            if isinstance(inner, exp.Column) and isinstance(getattr(inner, "this", None), exp.Star):
                return True

        return False

    def _top_level_select_has_star(self, parsed: Any, sql: str) -> bool:
        if self.allow_select_star:
            return False
        if sqlglot is None or exp is None or parsed is None:
            return self._top_level_select_has_star_fallback(sql)

        # sqlglot parses WITH ... SELECT as an exp.Select whose expressions are
        # the final output projection. CTE body projections should not be used
        # for the top-level privacy decision.
        select_expr = parsed if isinstance(parsed, exp.Select) else parsed.find(exp.Select)
        if select_expr is None:
            return False

        for projection in getattr(select_expr, "expressions", []) or []:
            if self._is_projection_star(projection):
                return True
        return False

    def _top_level_select(self, parsed: Any) -> Any:
        if exp is None or parsed is None:
            return None
        return parsed if isinstance(parsed, exp.Select) else parsed.find(exp.Select)

    def _projection_column_names(self, projection: Any) -> set[str]:
        if exp is None:
            return set()
        return {
            str(column.name).lower() for column in projection.find_all(exp.Column) if column.name
        }

    def _projection_is_aggregate(self, projection: Any) -> bool:
        if exp is None:
            return False
        return any(
            isinstance(node, (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max))
            for node in projection.walk()
        )

    def _select_has_aggregate(self, select_expr: Any) -> bool:
        if exp is None or select_expr is None:
            return False
        return any(
            isinstance(node, (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max))
            for node in select_expr.walk()
        )

    def _select_has_group_by(self, select_expr: Any) -> bool:
        return bool(select_expr is not None and select_expr.args.get("group"))

    def _is_identifier_column(self, column_name: str) -> bool:
        name = column_name.lower()
        return name in self.IDENTIFIER_COLUMN_NAMES or name.endswith(self.IDENTIFIER_SUFFIXES)

    def _is_sensitive_column(self, column_name: str) -> bool:
        name = column_name.lower()
        return any(term in name for term in self.SENSITIVE_COLUMN_TERMS)

    def _privacy_projection_issues(self, parsed: Any) -> list[ValidationIssue]:
        if sqlglot is None or exp is None or parsed is None:
            return []

        select_expr = self._top_level_select(parsed)
        if select_expr is None:
            return []

        grouped_or_aggregated = self._select_has_group_by(
            select_expr
        ) or self._select_has_aggregate(select_expr)
        identifier_columns: set[str] = set()
        sensitive_row_columns: set[str] = set()

        for projection in getattr(select_expr, "expressions", []) or []:
            if self._projection_is_aggregate(projection):
                continue
            for column_name in self._projection_column_names(projection):
                if self._is_identifier_column(column_name):
                    identifier_columns.add(column_name)
                elif self._is_sensitive_column(column_name) and not grouped_or_aggregated:
                    sensitive_row_columns.add(column_name)

        issues: list[ValidationIssue] = []
        if identifier_columns:
            issues.append(
                ValidationIssue(
                    "PRIVACY_IDENTIFIER_PROJECTION",
                    "User-visible SQL must not project identifiers: "
                    + ", ".join(sorted(identifier_columns)),
                )
            )
        if sensitive_row_columns:
            issues.append(
                ValidationIssue(
                    "PRIVACY_SENSITIVE_ROW_LEVEL",
                    "Sensitive mental-health fields must be returned only as aggregate analysis, not row-level columns: "
                    + ", ".join(sorted(sensitive_row_columns)),
                )
            )
        return issues

    def validate(self, sql: str) -> ValidationResult:
        s = self._strip_sql(sql)
        issues: list[ValidationIssue] = []
        if not s:
            return ValidationResult.fail("EMPTY_SQL", "SQL is empty.")

        # Multiple statement check: semicolon inside remaining SQL is disallowed.
        if ";" in s:
            issues.append(
                ValidationIssue("MULTIPLE_STATEMENTS", "Multiple SQL statements are not allowed.")
            )

        lower = s.lower()
        if "--" in lower or "/*" in lower or "*/" in lower:
            issues.append(
                ValidationIssue("SQL_COMMENT", "SQL comments are not allowed in generated queries.")
            )

        for keyword in self.FORBIDDEN:
            if re.search(rf"\b{keyword}\b", lower):
                issues.append(
                    ValidationIssue("FORBIDDEN_KEYWORD", f"Forbidden SQL keyword: {keyword}")
                )

        if not re.match(r"^\s*(select|with)\b", lower):
            issues.append(
                ValidationIssue("NOT_SELECT", "Only SELECT or WITH ... SELECT queries are allowed.")
            )

        parsed = None
        if sqlglot is not None:
            try:
                parsed = sqlglot.parse_one(s, read="sqlite")
                if parsed is None:
                    issues.append(ValidationIssue("PARSE_ERROR", "sqlglot could not parse SQL."))
                elif not (isinstance(parsed, exp.Select) or parsed.find(exp.Select)):
                    issues.append(
                        ValidationIssue("NOT_SELECT_AST", "Parsed SQL is not a SELECT query.")
                    )
            except Exception as exc:
                issues.append(ValidationIssue("PARSE_ERROR", f"SQL parse failed: {exc}"))

        if self._top_level_select_has_star(parsed, s):
            issues.append(
                ValidationIssue(
                    "SELECT_STAR", "Top-level SELECT * is not allowed for privacy/safety reasons."
                )
            )
        issues.extend(self._privacy_projection_issues(parsed))

        return ValidationResult(not issues, issues, s)
