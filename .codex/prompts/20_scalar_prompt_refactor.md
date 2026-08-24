# 20 — First Prompt Refactor: Scalar Prompt Only

```text
Read AGENTS.md.
Read:
- docs/context-hub/QUERY_SHAPE_CONTRACTS.md
- docs/context-hub/FAILURE_PATTERNS.md
- src/generation/output_parser.py

Create or update only:
src/generation/prompts/sql_generation_scalar.j2

Do not touch non-scalar prompts.

The scalar prompt must enforce:
1. exactly one SQL query
2. one-row KPI result
3. no GROUP BY unless user explicitly asks grouped output
4. no latent subgroup dimensions
5. no hidden WHERE
6. COUNT(*) for simple count
7. ROUND(AVG(col), 2) for simple average
8. NULL handling for averages when needed
9. only supplied schema tables/columns
10. clarification for ambiguity or unsupported joins
11. JSON output compatible with OutputParser

Add one negative example:
Bad: turning "تعداد کل رکوردها" into GROUP BY depression_flag.

Return:
- prompt content
- parser compatibility notes
- tests to run
```

---
