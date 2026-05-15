# Phase 4: SQL Validation Stack

## Overview
Phase 4 introduces a rigorous, multi-layered SQL validation stack designed to act as an unyielding gatekeeper between generated SQL queries (whether from an LLM, a rules engine, or the `QueryPlanner`) and the execution engine. This ensures absolute deterministic safety, prevents cross-domain data hallucination, and enforces correct statistical aggregations.

## Architecture

The validation pipeline (`ValidationPipeline`) orchestrates six sequential steps:

1. **AST-Based Rewriter (`SQLRewriter`)**
   - Parses the incoming SQL using `sqlglot`.
   - Cleans markdown fences and trailing semicolons.
   - Fixes known column-level typos deterministically using the AST (e.g., `gpa` -> `cgpa`).
   - Ensures a `LIMIT` clause is added to raw SELECT queries that don't have aggregations.

2. **Syntax Validator (`SQLSyntaxValidator`)**
   - Ensures the query is valid SQLite syntax.
   - Uses `sqlglot` to catch syntax errors before any other logic runs.

3. **Safety Validator (`SQLSafetyValidator`)**
   - Protects against destructive operations (DROP, DELETE, UPDATE, INSERT).
   - Blocks prompt injection attempts embedded in SQL.
   - Rejects unconstrained `SELECT *` without explicit limits or filtering.

4. **Schema Validator (`SQLSchemaValidator`)**
   - Verifies that all referenced tables and columns exist in the active `schema_snapshot.json`.

5. **Join Validator (`SQLJoinValidator`)**
   - Validates all `JOIN` paths (both explicit `JOIN` and implicit `CROSS JOIN` via multi-table `FROM`) against the `schema_graph.json`.
   - Prevents cross-domain hallucination by blocking joins that lack a defined, semantic edge in the graph.

6. **Aggregation Validator (`SQLAggregationValidator`)**
   - Enforces logical aggregation rules.
   - Ensures all non-aggregated columns in a SELECT list are included in a `GROUP BY` clause.
   - Prevents applying `AVG` or `SUM` to categorical (`TEXT`) columns.

## Testing & Verification
The stack is fully covered by unit tests in `tests/tier1_unit/`, ensuring regression safety and enforcing the strict validation rules.
