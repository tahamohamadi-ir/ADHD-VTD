from __future__ import annotations

import sqlglot
from sqlglot import exp

from src.schema.schema_registry import SchemaRegistry
from src.sql_validation.validation_result import ValidationIssue, ValidationResult

class SQLAggregationValidator:
    """Validates aggregation logic in SQL (e.g., GROUP BY, AVG on correct types)."""

    def __init__(self, registry: SchemaRegistry | None = None) -> None:
        self.registry = registry or SchemaRegistry()

    def validate(self, sql: str) -> ValidationResult:
        normalized = (sql or "").strip().rstrip(";").strip()
        issues: list[ValidationIssue] = []
        if sqlglot is None:
            return ValidationResult.pass_(normalized)
            
        try:
            tree = sqlglot.parse_one(normalized, read="sqlite")
        except Exception:
            return ValidationResult.pass_(normalized)

        # Build table alias map to resolve column types
        ctes = {cte.alias for cte in tree.find_all(exp.CTE)}
        tables: dict[str, str] = {}
        for table in tree.find_all(exp.Table):
            if table.name not in ctes:
                tables[table.alias_or_name] = table.name
                tables[table.name] = table.name

        # For checking column types
        def get_column_type(table_alias: str | None, col_name: str) -> str:
            candidates = [tables[table_alias]] if table_alias and table_alias in tables else list(set(tables.values()))
            for t in candidates:
                # We fetch type from snapshot
                t_info = self.registry.tables.get(t, {})
                for c in t_info.get("columns", []):
                    if c["name"].lower() == col_name.lower():
                        return c.get("type", "UNKNOWN").upper()
            return "UNKNOWN"

        for select in tree.find_all(exp.Select):
            # Find all selected expressions
            select_exprs = select.expressions
            
            agg_funcs = []
            non_agg_cols = []
            
            for expr in select_exprs:
                # Identify if expr is aggregate or contains aggregate
                has_agg = False
                for node in expr.walk():
                    if isinstance(node, (exp.Avg, exp.Sum, exp.Count, exp.Min, exp.Max)):
                        has_agg = True
                        break
                
                if has_agg:
                    agg_funcs.append(expr)
                else:
                    # If it's a plain column or alias, it should be in GROUP BY
                    # Let's collect plain columns
                    for col in expr.find_all(exp.Column):
                        non_agg_cols.append(col)

            # Check AVG/SUM on TEXT columns
            for agg in select.find_all(exp.Avg, exp.Sum):
                for col in agg.find_all(exp.Column):
                    c_type = get_column_type(col.table, col.name)
                    if c_type == "TEXT":
                        issues.append(ValidationIssue(
                            "INVALID_AGGREGATION",
                            f"Cannot compute {agg.key.upper()} over categorical/TEXT column: {col.name}"
                        ))

            # If there are aggregates, ensure non-aggregated columns are in GROUP BY
            if agg_funcs and non_agg_cols:
                group_by = select.args.get("group")
                if not group_by:
                    issues.append(ValidationIssue(
                        "MISSING_GROUP_BY",
                        "Query contains aggregate functions but is missing a GROUP BY clause for non-aggregated columns."
                    ))
                else:
                    # Check if all non_agg_cols are covered in GROUP BY
                    group_exprs = group_by.expressions
                    # Basic check: just see if the column names appear in group expressions
                    for col in non_agg_cols:
                        found = False
                        for g in group_exprs:
                            if col.name.lower() in [c.name.lower() for c in g.find_all(exp.Column)]:
                                found = True
                                break
                        if not found:
                            issues.append(ValidationIssue(
                                "UNGROUPED_COLUMN",
                                f"Column '{col.name}' must appear in the GROUP BY clause or be used in an aggregate function."
                            ))

        return ValidationResult(not issues, issues, normalized)
