---
apply: always
---

# PARS-SQL — SQL Safety and Privacy Rules

Apply this rule when working on:

- `src/sql_validation/**`
- `src/db/**`
- `src/nlu/safety_intent_detector.py`
- `data/schema/schema_graph.json`
- any code that executes, rewrites, validates, repairs, or formats SQL

## SQL allowlist

Only allow:

```sql
SELECT ...
WITH ... SELECT ...
```

## SQL blocklist

Always reject:

```text
INSERT UPDATE DELETE DROP ALTER CREATE TRUNCATE REPLACE MERGE
ATTACH DETACH PRAGMA VACUUM REINDEX EXEC EXECUTE CALL
```

## Statement safety

Reject:

- multiple SQL statements,
- SQL comments (`--`, `/* ... */`),
- top-level `SELECT *`,
- top-level `SELECT table.*`,
- unsafe system/admin access,
- destructive or mutating operations.

Allow:

```sql
COUNT(*)
```

because it is an aggregate expression, not raw row exposure.

## Privacy policy

For mental-health and sensitive fields:

- depression,
- anxiety,
- stress,
- suicidality,
- high-risk status,
- treatment seeking,
- diagnosis-related fields,
- personal information,

prefer aggregate results or refuse/clarify.

Allowed outputs:

- counts,
- rates,
- averages,
- distributions,
- anonymized group-level summaries.

Forbidden outputs:

- names,
- IDs,
- emails,
- phone numbers,
- addresses,
- exact individual rows,
- all high-risk individuals,
- all suicidal individuals,
- raw sensitive records.

## Cross-domain joins

Default policy:

- Cross-domain joins are forbidden.
- Only allow joins explicitly permitted by `data/schema/schema_graph.json`.
- If a user asks for an unsupported multi-domain join, ask clarification or offer separate aggregate summaries.

## Required tests

When changing safety/execution code, add or update:

- `tests/unit/test_safety_validator.py`
- `tests/unit/test_schema_validator.py`
- `tests/unit/test_join_validator.py`
- `tests/unit/test_read_only_executor.py`
- `tests/integration/test_privacy_guardrails.py`

## Acceptance criteria

- destructive SQL rejected,
- multiple statements rejected,
- SQL comments rejected,
- top-level `SELECT *` rejected,
- `COUNT(*)` accepted,
- illegal joins rejected,
- read-only executor cannot mutate the database,
- sensitive row-level output refused or blocked.
