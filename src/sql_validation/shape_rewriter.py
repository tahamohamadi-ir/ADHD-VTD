from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import sqlglot
from sqlglot import exp

from src.core.query_ir import QueryIR
from src.sql_validation.validation_result import ValidationIssue


_SHAPE_ERROR_CODES = {
    "ANALYTICAL_SHAPE_MISSING_GROUP_BY",
    "ANALYTICAL_SHAPE_MISSING_RATE_FORMULA",
    "ANALYTICAL_SHAPE_SINGLE_SIDED_COMPARISON",
    "ANALYTICAL_SHAPE_MISSING_MULTI_DIMENSION_GROUPING",
    "ANALYTICAL_SHAPE_GROUP_BY_DIMENSION_MISMATCH",
}

_BINARY_RATE_COLUMNS = (
    "depression_flag",
    "depression_diagnosis",
    "seeks_treatment",
    "treatment",
    "treatment_seeking",
    "part_time_job",
)


@dataclass(frozen=True)
class ShapeRewriteResult:
    sql: str | None
    action: str

    @property
    def rewritten(self) -> bool:
        return bool(self.sql)


def rewrite_analytical_shape(
    sql: str,
    *,
    question: str,
    qir: QueryIR | None,
    schema: dict[str, Any] | None,
    issues: list[ValidationIssue],
) -> ShapeRewriteResult:
    """Repair simple aggregate shape errors using QIR/schema, not benchmark IDs.

    This is deliberately narrow: only single-table SELECT statements are rewritten.
    Complex joins, CTEs, subqueries and UNIONs remain LLM/reflexion territory.
    """

    codes = {issue.code for issue in issues}
    if not (codes & _SHAPE_ERROR_CODES):
        return ShapeRewriteResult(None, "shape_surgeon_invoked=false")

    parsed = _parse_single_table_select(sql)
    if parsed is None:
        return ShapeRewriteResult(
            None, "shape_surgeon_invoked=true; shape_surgeon_skipped=not_single_table_select"
        )

    tree, table = parsed
    table_columns = _columns_for_table(schema, table)
    if not table_columns:
        return ShapeRewriteResult(
            None, "shape_surgeon_invoked=true; shape_surgeon_skipped=no_schema_columns"
        )

    dimensions = _requested_dimensions(qir, table_columns)
    remove_binary_filter = "ANALYTICAL_SHAPE_SINGLE_SIDED_COMPARISON" in codes
    if not dimensions and remove_binary_filter:
        dimensions = _binary_filter_columns(tree, table_columns)
    if not dimensions:
        return ShapeRewriteResult(
            None, "shape_surgeon_invoked=true; shape_surgeon_skipped=no_qir_dimensions"
        )

    asks_rate = "ANALYTICAL_SHAPE_MISSING_RATE_FORMULA" in codes or _asks_rate(question, qir)
    metric = _rate_metric(qir, table_columns, dimensions, question) if asks_rate else None
    where_sql = _where_without_group_filters(tree, dimensions if remove_binary_filter else [])
    where_sql = _append_not_null_filters(where_sql, [*dimensions, *([metric] if metric else [])])

    if asks_rate and metric:
        rewritten = _build_rate_sql(table, dimensions, metric, where_sql)
        return ShapeRewriteResult(
            rewritten,
            f"shape_surgeon_invoked=true; shape_surgeon_patch_applied=true; rate_metric={metric}; dimensions={','.join(dimensions)}",
        )

    aggregates = _aggregate_projections(tree)
    if not aggregates:
        aggregates = [("COUNT(*)", "count")]
    rewritten = _build_grouped_aggregate_sql(table, dimensions, aggregates, where_sql)
    return ShapeRewriteResult(
        rewritten,
        f"shape_surgeon_invoked=true; shape_surgeon_patch_applied=true; dimensions={','.join(dimensions)}",
    )


def _parse_single_table_select(sql: str) -> tuple[exp.Select, str] | None:
    try:
        tree = sqlglot.parse_one((sql or "").strip().rstrip(";"), read="sqlite")
    except Exception:
        return None
    if not isinstance(tree, exp.Select):
        return None
    if tree.args.get("with") or tree.find(exp.Subquery) or tree.find(exp.Union):
        return None
    tables = list(tree.find_all(exp.Table))
    if len(tables) != 1:
        return None
    if list(tree.find_all(exp.Join)):
        return None
    return tree, tables[0].name


def _columns_for_table(schema: dict[str, Any] | None, table: str) -> set[str]:
    if not schema:
        return set()
    table_info = schema.get(table)
    if table_info is None:
        return set()
    columns = (
        table_info.get("columns", [])
        if isinstance(table_info, dict)
        else getattr(table_info, "columns", [])
    )
    if isinstance(columns, dict):
        return {str(name) for name in columns}
    names: set[str] = set()
    for column in columns:
        if isinstance(column, str):
            names.add(column)
        elif isinstance(column, dict):
            name = column.get("name") or column.get("column_name") or column.get("column")
            if name:
                names.add(str(name))
        else:
            name = getattr(column, "name", None)
            if name:
                names.add(str(name))
    return names


def _requested_dimensions(qir: QueryIR | None, table_columns: set[str]) -> list[str]:
    dimensions: list[str] = []
    for raw in getattr(qir, "dimensions", []) or []:
        name = str(raw).split(".")[-1]
        if name in table_columns and name not in dimensions:
            dimensions.append(name)
    return dimensions[:3]


def _rate_metric(
    qir: QueryIR | None,
    table_columns: set[str],
    dimensions: list[str],
    question: str,
) -> str | None:
    for raw in getattr(qir, "metrics", []) or []:
        name = str(raw).split(".")[-1]
        if name in table_columns and name not in dimensions and _is_binary_metric(name):
            return name

    lower_question = (question or "").lower()
    preferred = list(_BINARY_RATE_COLUMNS)
    if "treatment" in lower_question or "\u062f\u0631\u0645\u0627\u0646" in lower_question:
        preferred = ["seeks_treatment", "treatment", "treatment_seeking", *preferred]
    if (
        "depression" in lower_question
        or "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc" in lower_question
    ):
        preferred = ["depression_flag", "depression_diagnosis", *preferred]
    for name in preferred:
        if name in table_columns and name not in dimensions:
            return name
    return None


def _is_binary_metric(name: str) -> bool:
    return name in _BINARY_RATE_COLUMNS or name.endswith("_flag") or name.endswith("_diagnosis")


def _asks_rate(question: str, qir: QueryIR | None) -> bool:
    task_type = str(getattr(qir, "task_type", "") or "").lower()
    lower = (question or "").lower()
    return task_type == "rate_query" or any(
        term in lower
        for term in (
            "rate",
            "percent",
            "percentage",
            "\u0646\u0631\u062e",
            "\u062f\u0631\u0635\u062f",
        )
    )


def _binary_filter_columns(tree: exp.Select, table_columns: set[str]) -> list[str]:
    where = tree.args.get("where")
    if where is None:
        return []
    columns: list[str] = []
    for predicate in where.find_all(exp.EQ):
        left = predicate.left
        right = predicate.right
        if not isinstance(left, exp.Column):
            continue
        if not isinstance(right, exp.Literal) or str(right.this) not in {"0", "1"}:
            continue
        name = left.name
        if name in table_columns and name not in columns:
            columns.append(name)
    return columns


def _aggregate_projections(tree: exp.Select) -> list[tuple[str, str]]:
    aggregates: list[tuple[str, str]] = []
    for projection in tree.expressions:
        alias = projection.alias if isinstance(projection, exp.Alias) else ""
        expression = projection.this if isinstance(projection, exp.Alias) else projection
        if not any(
            isinstance(node, (exp.Count, exp.Avg, exp.Sum, exp.Min, exp.Max))
            for node in expression.walk()
        ):
            continue
        expression_sql = expression.sql(dialect="sqlite")
        if isinstance(expression, exp.Avg) and not isinstance(expression.parent, exp.Round):
            expression_sql = f"ROUND({expression_sql}, 2)"
        alias_name = alias or _default_alias(expression)
        aggregates.append((expression_sql, alias_name))
    return aggregates


def _default_alias(expression: exp.Expression) -> str:
    if any(isinstance(node, exp.Count) for node in expression.walk()):
        return "count"
    if any(isinstance(node, exp.Avg) for node in expression.walk()):
        col = _first_column_name(expression) or "value"
        return f"avg_{col}"
    if any(isinstance(node, exp.Sum) for node in expression.walk()):
        col = _first_column_name(expression) or "value"
        return f"sum_{col}"
    return "value"


def _first_column_name(expression: exp.Expression) -> str | None:
    column = next(expression.find_all(exp.Column), None)
    return column.name if column else None


def _where_without_group_filters(tree: exp.Select, dimensions_to_remove: list[str]) -> str:
    where = tree.args.get("where")
    if where is None:
        return ""
    condition_sql = where.this.sql(dialect="sqlite")
    if not dimensions_to_remove:
        return condition_sql
    parts = _split_and_conditions(condition_sql)
    kept = [part for part in parts if not _is_binary_filter_on_any(part, dimensions_to_remove)]
    return " AND ".join(kept)


def _split_and_conditions(condition_sql: str) -> list[str]:
    # Narrow helper for simple validator-repair output; complex boolean trees are skipped upstream.
    return [
        part.strip().strip("() ")
        for part in re.split(r"\s+AND\s+", condition_sql, flags=re.IGNORECASE)
        if part.strip()
    ]


def _is_binary_filter_on_any(condition: str, columns: list[str]) -> bool:
    for column in columns:
        if re.fullmatch(rf"{re.escape(column)}\s*=\s*[01]", condition, flags=re.IGNORECASE):
            return True
        if re.fullmatch(
            rf"[A-Za-z_][A-Za-z0-9_]*\.{re.escape(column)}\s*=\s*[01]",
            condition,
            flags=re.IGNORECASE,
        ):
            return True
    return False


def _append_not_null_filters(where_sql: str, columns: list[str | None]) -> str:
    conditions = [where_sql.strip()] if where_sql.strip() else []
    compact = f" {where_sql.lower()} "
    for column in [col for col in columns if col]:
        if re.search(rf"\b{re.escape(str(column).lower())}\b\s+is\s+not\s+null", compact):
            continue
        conditions.append(f"{column} IS NOT NULL")
    return " AND ".join(conditions)


def _build_grouped_aggregate_sql(
    table: str,
    dimensions: list[str],
    aggregates: list[tuple[str, str]],
    where_sql: str,
) -> str:
    select_parts = [*dimensions, *[f"{expr} AS {alias}" for expr, alias in aggregates]]
    first_alias = aggregates[0][1] if aggregates else "count"
    return _assemble_sql(
        select_parts=select_parts,
        table=table,
        where_sql=where_sql,
        group_by=dimensions,
        order_by=f"{first_alias} DESC",
    )


def _build_rate_sql(table: str, dimensions: list[str], metric: str, where_sql: str) -> str:
    select_parts = [
        *dimensions,
        "COUNT(*) AS total",
        f"SUM({metric}) AS positives",
        f"ROUND(100.0 * SUM({metric}) / COUNT(*), 2) AS rate_pct",
    ]
    return _assemble_sql(
        select_parts=select_parts,
        table=table,
        where_sql=where_sql,
        group_by=dimensions,
        order_by="rate_pct DESC",
    )


def _assemble_sql(
    *,
    select_parts: list[str],
    table: str,
    where_sql: str,
    group_by: list[str],
    order_by: str,
) -> str:
    sql = f"SELECT {', '.join(select_parts)} FROM {table}"
    if where_sql:
        sql += f" WHERE {where_sql}"
    sql += f" GROUP BY {', '.join(group_by)}"
    if order_by:
        sql += f" ORDER BY {order_by}"
    return sql
