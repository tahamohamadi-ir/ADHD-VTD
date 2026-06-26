from __future__ import annotations

import re

from src.core.query_shape import QueryShape, QueryShapeContract
from src.sql_validation.validation_result import ValidationIssue, ValidationResult


def _compact(sql: str) -> str:
    return " ".join((sql or "").lower().replace("\n", " ").split())


def _has_group_by(sql: str) -> bool:
    return bool(re.search(r"\bgroup\s+by\b", sql))


def _has_order_by(sql: str) -> bool:
    return bool(re.search(r"\border\s+by\b", sql))


def _has_limit(sql: str) -> bool:
    return bool(re.search(r"\blimit\b", sql))


def _has_where(sql: str) -> bool:
    return bool(re.search(r"\bwhere\b", sql))


def _group_by_fragment(sql: str) -> str:
    match = re.search(
        r"\bgroup\s+by\b(?P<body>.*?)(\border\s+by\b|\bhaving\b|\blimit\b|$)", sql, re.S
    )
    if not match:
        return ""
    return match.group("body").strip()


def _group_by_count(sql: str) -> int:
    fragment = _group_by_fragment(sql)
    if not fragment:
        return 0
    return len([part for part in fragment.split(",") if part.strip()])


def _normalized_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "", value.lower())


def _add(issues: list[ValidationIssue], code: str, message: str) -> None:
    issues.append(ValidationIssue(code=code, message=message, severity="error"))


class SQLShapeContractValidator:
    """Validate SQL against an explicit analytical result-shape contract."""

    def validate(self, sql: str, contract: QueryShapeContract) -> ValidationResult:
        compact_sql = _compact(sql)
        issues: list[ValidationIssue] = []

        if not compact_sql:
            return ValidationResult.fail(
                "SHAPE_CONTRACT_EMPTY_SQL", "SQL is required for shape validation."
            )

        if contract.shape == QueryShape.CLARIFICATION:
            _add(
                issues,
                "SHAPE_CONTRACT_CLARIFICATION_HAS_SQL",
                "Clarification contracts should not emit SQL.",
            )

        if contract.forbid_group_by and _has_group_by(compact_sql):
            _add(
                issues,
                "SHAPE_CONTRACT_FORBIDS_GROUP_BY",
                "This query shape forbids GROUP BY because the user did not request grouped output.",
            )

        if contract.require_group_by and not _has_group_by(compact_sql):
            _add(
                issues,
                "SHAPE_CONTRACT_REQUIRES_GROUP_BY",
                "This query shape requires GROUP BY for the requested analytical dimension.",
            )

        if contract.forbid_where and _has_where(compact_sql):
            _add(
                issues,
                "SHAPE_CONTRACT_FORBIDS_WHERE",
                "This query shape forbids WHERE because the user did not request a filter.",
            )

        if contract.require_order_by and not _has_order_by(compact_sql):
            _add(
                issues,
                "SHAPE_CONTRACT_REQUIRES_ORDER_BY",
                "Ranking or timeseries shape requires ORDER BY.",
            )

        if contract.require_limit and not _has_limit(compact_sql):
            _add(
                issues,
                "SHAPE_CONTRACT_REQUIRES_LIMIT",
                "This query shape requires LIMIT.",
            )

        if contract.forbid_limit and _has_limit(compact_sql):
            _add(
                issues,
                "SHAPE_CONTRACT_FORBIDS_LIMIT",
                "This query shape forbids LIMIT unless raw rows are requested.",
            )

        min_dimensions = contract.min_group_by_dimensions
        if min_dimensions is not None and _group_by_count(compact_sql) < min_dimensions:
            _add(
                issues,
                "SHAPE_CONTRACT_INSUFFICIENT_GROUP_BY_DIMENSIONS",
                f"This query shape requires at least {min_dimensions} GROUP BY dimension(s).",
            )

        group_fragment = _group_by_fragment(compact_sql)
        missing_dimensions = [
            dimension
            for dimension in contract.required_dimensions
            if _normalized_identifier(dimension) not in _normalized_identifier(group_fragment)
        ]
        if missing_dimensions:
            _add(
                issues,
                "SHAPE_CONTRACT_MISSING_GROUP_BY_DIMENSION",
                "GROUP BY is missing required dimension(s): " + ", ".join(missing_dimensions),
            )

        missing_aliases = [
            alias
            for alias in contract.expected_aggregate_aliases
            if _normalized_identifier(alias) not in _normalized_identifier(compact_sql)
        ]
        if missing_aliases:
            _add(
                issues,
                "SHAPE_CONTRACT_MISSING_AGGREGATE_ALIAS",
                "SQL is missing expected aggregate alias(es): " + ", ".join(missing_aliases),
            )

        return ValidationResult(
            ok=not any(issue.severity == "error" for issue in issues),
            issues=issues,
            normalized_sql=compact_sql,
        )
