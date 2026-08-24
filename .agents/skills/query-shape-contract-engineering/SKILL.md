---
name: query-shape-contract-engineering
description: Use this skill when fixing valid-but-wrong SQL, scalar, grouped, ranking, timeseries, matrix errors, or prompt over-grouping.
---

# Skill: Query Shape Contract Engineering

## Purpose

Use this skill when fixing valid-but-wrong SQL, scalar/grouped/ranking/timeseries/matrix errors, or prompt over-grouping.

## Required context

Read:

- `AGENTS.md`
- `docs/context-hub/QUERY_SHAPE_CONTRACTS.md`
- `docs/context-hub/FAILURE_PATTERNS.md`
- `src/core/query_ir.py`
- `src/sql_validation/shape_validator.py`
- relevant prompt file

## Main objective

Prevent SQL that is syntactically valid but analytically wrong.

## Shape classes

- scalar
- grouped
- ranking
- timeseries
- matrix
- raw_rows
- clarification

## Rules

1. Scalar questions must not produce GROUP BY.
2. Scalar questions must return one row.
3. Grouped questions must include the grouping dimension in SELECT and GROUP BY.
4. Ranking questions must include ORDER BY and LIMIT.
5. Timeseries questions must include time/year/date dimension.
6. Matrix questions must group by at least two dimensions.
7. Raw row queries must include LIMIT and must not expose sensitive fields.
8. If shape cannot be determined, ask clarification.

## Tests required

Add or update:

- `tests/unit/test_query_shape.py`
- `tests/unit/test_shape_contract_scalar.py`
- `tests/unit/test_shape_contract_grouped.py`
- `tests/unit/test_shape_contract_rate.py`
- `tests/integration/test_generation_scalar_easy.py`

## Acceptance criteria

- no scalar easy test emits GROUP BY
- no hidden filter is added
- rate formula uses correct numerator/denominator
- two-sided comparison is not filtered to one side

## Output format

Return:

1. Shape detected
2. Contract enforced
3. SQL examples before/after
4. Tests added
5. Risks