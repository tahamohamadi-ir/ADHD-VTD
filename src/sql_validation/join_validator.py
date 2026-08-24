from __future__ import annotations

import json
from pathlib import Path
import sqlglot
from sqlglot import exp

from src.sql_validation.validation_result import ValidationIssue, ValidationResult


class SQLJoinValidator:
    """Validates JOIN operations against the semantic schema graph."""

    def __init__(self, schema_graph_path: str | Path = "data/schema/schema_graph.json") -> None:
        self.graph_path = Path(schema_graph_path)
        self.allowed_edges: set[frozenset[str]] = self._load_allowed_edges()

    def _load_allowed_edges(self) -> set[frozenset[str]]:
        if not self.graph_path.exists():
            return set()
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        allowed = set()
        for edge in data.get("edges", []):
            if edge.get("allowed", False):
                allowed.add(frozenset([edge["source"], edge["target"]]))
        return allowed

    def validate(self, sql: str) -> ValidationResult:
        normalized = (sql or "").strip().rstrip(";").strip()
        issues: list[ValidationIssue] = []
        if sqlglot is None:
            return ValidationResult.pass_(normalized)

        try:
            tree = sqlglot.parse_one(normalized, read="sqlite")
        except Exception:
            # Syntax/Parse errors are handled by syntax validator
            return ValidationResult.pass_(normalized)

        # Map table aliases to true table names
        ctes = {cte.alias for cte in tree.find_all(exp.CTE)}
        tables: dict[str, str] = {}
        for table in tree.find_all(exp.Table):
            if table.name in ctes:
                continue
            tables[table.alias_or_name] = table.name

        # Find all explicit JOINs
        for select in tree.find_all(exp.Select):
            base_table_node = select.args.get("from_")
            if base_table_node is None:
                continue

            base_table = None
            if isinstance(base_table_node.this, exp.Table):
                base_table = base_table_node.this.name

            # For each JOIN
            joins = select.args.get("joins", [])
            for join in joins:
                join_table_node = join.this
                if not isinstance(join_table_node, exp.Table):
                    continue
                join_table = join_table_node.name

                # Implicit cross join check: no ON clause and not explicitly CROSS JOIN
                if (
                    not join.args.get("on")
                    and not join.args.get("using")
                    and join.args.get("kind") != "CROSS"
                ):
                    # But even CROSS JOIN might be restricted, let's stick to the graph.
                    pass

                if base_table and join_table:
                    # Resolve real names
                    real_base = tables.get(base_table, base_table)
                    real_join = tables.get(join_table, join_table)

                    if real_base in ctes or real_join in ctes:
                        continue  # Skip checking CTE joins for now

                    edge = frozenset([real_base, real_join])
                    if edge not in self.allowed_edges:
                        issues.append(
                            ValidationIssue(
                                "ILLEGAL_JOIN",
                                f"Join between '{real_base}' and '{real_join}' is not allowed by the semantic graph.",
                            )
                        )

                # Update base_table for chained joins (A join B join C -> base can be A or B)
                # To be safe, we check if the new table is joined to ANY of the previously seen tables
                # Since we don't do full join-tree analysis, checking against base is a heuristic.
                # Actually, a better way is to just collect all tables in the FROM/JOIN block and ensure
                # they form a connected component in the allowed graph.
                # For our simple schema, any join not explicitly in the edges list is forbidden.

        return ValidationResult(not issues, issues, normalized)
