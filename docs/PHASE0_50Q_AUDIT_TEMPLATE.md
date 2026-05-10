# Phase 0 - 50 Question Audit Template

Recommended file path:

```text
data/audit/phase0_50q_audit.csv
```

CSV columns:

```csv
item_id,question_fa,difficulty,category,gold_sql_executes,schema_aligned,result_shape_ok,visual_ok,question_sql_aligned,needs_fix,fix_type,notes
```

Fix types:

```text
NO_FIX
SQL_FIX
SCHEMA_METADATA_FIX
QUESTION_REWRITE
VISUAL_METADATA_FIX
REMOVE_FROM_PHASE0
```

Summary report path:

```text
data/audit/phase0_50q_audit_report.md
```

Minimum summary:

```text
Total audited: 50
Executable gold SQL: N/50
Schema aligned: N/50
Question-SQL aligned: N/50
Items requiring fix: N/50
Decision: PASS / PASS_WITH_FIXES / FAIL
```
