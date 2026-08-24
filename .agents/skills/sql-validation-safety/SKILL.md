---
name: sql-validation-safety
description: Use this skill for safety validator, schema validator, join validator, aggregation validator, semantic validator, SQL rewriter, read-only executor, or privacy rules.
---

# Skill: SQL Validation and Safety

## Purpose

Use this skill for safety validator, schema validator, join validator, aggregation validator, semantic validator, SQL rewriter, read-only executor, or privacy rules.

## Required context

Read:

- `AGENTS.md`
- `docs/context-hub/SAFETY_PRIVACY_RULES.md`
- `data/schema/schema_graph.json`
- `src/sql_validation/`
- `src/db/read_only_executor.py`

## Non-negotiable safety rules

1. Only SELECT and WITH ... SELECT are allowed.
2. Reject destructive/admin SQL.
3. Reject multiple statements.
4. Reject SQL comments.
5. Reject top-level SELECT *.
6. Allow COUNT(*).
7. Use read-only SQLite connection.
8. Enforce max rows.
9. Sensitive mental-health data must remain aggregate.

## Validator order

1. rewrite
2. syntax
3. safety
4. schema
5. join
6. aggregation
7. shape
8. semantic benchmark checks if case is provided

## Tests required

- `tests/unit/test_safety_validator.py`
- `tests/unit/test_schema_validator.py`
- `tests/unit/test_join_validator.py`
- `tests/unit/test_aggregation_validator.py`
- `tests/unit/test_read_only_executor.py`
- `tests/integration/test_privacy_guardrails.py`

## Acceptance criteria

- destructive SQL rejected
- prompt injection SQL rejected
- SELECT * rejected
- COUNT(*) accepted
- illegal joins rejected
- read-only executor cannot mutate database

## Output format

Return:

- safety issue addressed
- validator changed
- tests added
- commands run
- residual risk