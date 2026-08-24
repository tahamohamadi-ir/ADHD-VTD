# 04 — Safety / Privacy Hardening

```text
Read AGENTS.md.
Read:
- docs/context-hub/SAFETY_PRIVACY_RULES.md
- data/schema/schema_graph.json

Task:
Audit and improve SQL safety/privacy for:

[TARGET FILES]

Required checks:
1. Only SELECT and WITH ... SELECT allowed.
2. Destructive SQL rejected.
3. Multiple statements rejected.
4. SQL comments rejected.
5. Top-level SELECT * rejected.
6. COUNT(*) allowed.
7. Illegal joins rejected.
8. Read-only executor cannot mutate the database.
9. Sensitive mental-health row-level disclosure refused or blocked.

Do not weaken any safety rule.

Add/update tests:
- destructive SQL
- multiple statement
- comments
- SELECT *
- COUNT(*)
- illegal join
- sensitive row-level request
- read-only mutation attempt

Return:
- safety issues found
- patch summary
- tests
- commands
- residual risks
```

---
