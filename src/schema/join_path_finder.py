from __future__ import annotations

from dataclasses import dataclass, field

try:
    from src.schema.schema_graph import SchemaGraph
except Exception:  # pragma: no cover
    from schema_graph import SchemaGraph


@dataclass(frozen=True)
class JoinPathResult:
    found: bool
    tables: list[str] = field(default_factory=list)
    join_sql: list[str] = field(default_factory=list)
    reason: str | None = None


class JoinPathFinder:
    """Find only explicitly allowed join paths. No inferred cross-dataset joins."""

    def __init__(self, graph: SchemaGraph | None = None) -> None:
        self.graph = graph or SchemaGraph()

    def find_path(self, tables: list[str]) -> JoinPathResult:
        unique = list(dict.fromkeys(tables))
        if len(unique) <= 1:
            return JoinPathResult(True, unique, [], "Single-table query does not require joins.")
        if len(unique) == 2:
            edge = self.graph.find_direct_join(unique[0], unique[1])
            if edge and edge.join_sql:
                return JoinPathResult(True, unique, [edge.join_sql], "Direct manual join path.")
        return JoinPathResult(
            False,
            unique,
            [],
            "No explicit safe join path exists. Treat datasets as independent semantic domains.",
        )
