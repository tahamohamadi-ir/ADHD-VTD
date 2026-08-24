# 08 — Route-Specific Prompt Refactor

```text
Read AGENTS.md.
Read:
- docs/context-hub/QUERY_SHAPE_CONTRACTS.md
- docs/context-hub/FAILURE_PATTERNS.md
- src/generation/output_parser.py

Goal:
Refactor SQL generation into route-specific prompts.

Create or update:
- sql_generation_scalar.j2
- sql_generation_grouped.j2
- sql_generation_ranking.j2
- sql_generation_timeseries.j2
- sql_generation_matrix.j2
- sql_generation_raw_rows.j2

Start with only this shape:
[SCALAR/GROUPED/RANKING/TIMESERIES/MATRIX/RAW_ROWS]

Rules:
1. Do not change all prompts at once.
2. Preserve output parser compatibility.
3. Include negative examples.
4. Include JSON output format.
5. Include clarification path.
6. For scalar, explicitly forbid GROUP BY and hidden WHERE.

Add prompt snapshot/parser tests if available.

Return:
- prompt file changed
- new constraints
- parser compatibility
- tests
- risks
```

---
