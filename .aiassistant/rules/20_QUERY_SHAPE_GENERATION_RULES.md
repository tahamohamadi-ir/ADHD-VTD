# PARS-SQL — Query Shape and SQL Generation Rules

Apply this rule when working on:

- `src/generation/**`
- `src/generation/prompts/**`
- `src/sql_validation/shape_validator.py`
- `src/sql_validation/shape_rewriter.py`
- `src/sql_validation/sql_rewriter.py`
- `src/core/query_ir.py`
- `src/graph/nodes/*generation*`
- `src/graph/nodes/*validation*`

## Critical known failure

The system often turns scalar questions into grouped SQL. Do not introduce hidden `GROUP BY` or hidden `WHERE`.

## Always identify query shape first

Supported shapes:

1. scalar
2. grouped
3. ranking
4. timeseries
5. matrix
6. raw_rows
7. clarification/refusal

## Scalar rules

Scalar questions ask for one KPI or one number.

Examples:

- تعداد کل رکوردهای دیتاست چیست؟
- میانگین خواب دانشجویان چقدر است؟
- چند درصد دانشجویان افسردگی دارند؟
- average sleep چنده؟

Rules:

- Do not use `GROUP BY`.
- Return one row unless explicitly asked otherwise.
- Do not add hidden dimensions like gender, year, depression flag, country, category.
- Do not add hidden `WHERE` filters.
- Use `COUNT`, `AVG`, `SUM`, `MIN`, `MAX`, `ROUND` as needed.

## Grouped rules

Grouped questions ask for distribution, breakdown, comparison, or "به تفکیک / بر اساس / for each".

Rules:

- Include dimension in `SELECT`.
- Include dimension in `GROUP BY`.
- Use correct aggregation.
- Do not filter to one side when comparison requires both sides.

## Ranking rules

Ranking questions ask for top, bottom, highest, lowest, best, worst.

Rules:

- Must include `ORDER BY`.
- Must include `LIMIT` if top-N/bottom-N is specified.
- If ranking metric is missing, ask clarification.

## Rate/percentage rules

For binary flags:

```sql
ROUND(AVG(binary_flag) * 100.0, 2)
```

or:

```sql
ROUND(SUM(binary_flag) * 100.0 / COUNT(*), 2)
```

Do not use only `COUNT(binary_flag)` as a percentage.

## Two-sided comparison rules

If the user asks for "with and without", "افسرده و غیرافسرده", "دارای و بدون", do not filter to one side.

Bad:

```sql
WHERE depression_flag = 1
```

Good:

```sql
GROUP BY depression_flag
```

## Timeseries rules

Timeseries questions must include:

- time/year/date dimension,
- `ORDER BY` time,
- delta/LAG logic if asking change.

## Matrix rules

Matrix/combo questions must group by at least two dimensions.

## Raw row rules

Raw row queries:

- must include `LIMIT`,
- must not use `SELECT *`,
- must not expose sensitive personal/mental-health rows.

## Clarification rules

Ask clarification if:

- metric is missing,
- value is ambiguous,
- table/domain is ambiguous,
- join is unsupported,
- user asks for causality/clinical diagnosis,
- user asks for personal data,
- question depends on previous context not available.

## Required tests

When changing query-shape behavior, add or update:

- `tests/unit/test_shape_validator.py`
- `tests/unit/test_sql_rewriter.py`
- `tests/unit/test_query_shape_contracts.py`
- `tests/integration/test_generation_scalar_easy.py`
- `tests/integration/test_generation_grouped_rate.py`
