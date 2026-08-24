# 19 — First Phase Implementation: Query Shape Core

```text
Read AGENTS.md and docs/context-hub/INDEX.md.
Read:
- docs/context-hub/QUERY_SHAPE_CONTRACTS.md
- docs/context-hub/FAILURE_PATTERNS.md

Implement Phase 1 only:
- create or update src/core/query_shape.py
- create or update src/sql_validation/shape_contract.py
- add unit tests under tests/unit/

Do not modify:
- retrieval
- judge
- paper files
- dataset files
- benchmark result files

Exit gate:
No scalar-intent test may emit or accept grouped SQL.

Required tests:
1. scalar COUNT(*) accepted
2. scalar AVG accepted
3. scalar GROUP BY rejected
4. scalar hidden WHERE rejected when not requested if contract marks filters forbidden
5. grouped query accepted when group_by required
6. ranking query requires ORDER BY
7. raw_rows requires LIMIT

Return:
- files changed
- tests added
- commands to run
- risks
```

---
