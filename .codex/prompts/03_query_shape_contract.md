# 03 — Fix Low EX / Query Shape Contract

```text
Read AGENTS.md.
Read:
- docs/context-hub/QUERY_SHAPE_CONTRACTS.md
- docs/context-hub/FAILURE_PATTERNS.md

Goal:
Reduce valid-but-wrong SQL caused by wrong output shape, especially scalar questions being converted into grouped SQL.

Work only on:
[LIST TARGET FILES, e.g. src/core/query_ir.py, src/sql_validation/shape_validator.py, src/generation/prompts/sql_generation.j2]

Do not modify:
- retrieval modules
- dataset files
- benchmark result files
- paper tables; if a separate task touches generated paper tables, they must
  include `dataset_hash`, `selected_cases_hash`, and artifact provenance

Required behavior:
1. Scalar questions must not produce GROUP BY.
2. Scalar questions must not add hidden WHERE filters.
3. Rate questions must compute numerator/denominator correctly.
4. Two-sided comparisons must group by the binary/category column, not filter one side.
5. Ambiguous shape must ask clarification.

Add/update tests:
- scalar count
- scalar average
- scalar rate
- grouped distribution
- two-sided comparison
- hidden filter rejection

Return:
- shape contract changes
- examples before/after
- tests added
- commands to run
- risks
```

---
