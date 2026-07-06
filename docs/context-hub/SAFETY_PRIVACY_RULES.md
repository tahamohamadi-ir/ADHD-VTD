# Safety And Privacy Rules

This is the canonical short context for SQL safety, privacy, and read-only
execution work. Use `docs/THREAT_MODEL.md` only when broader threat-model detail
is needed.

## SQL Allowlist

Allowed SQL:

- `SELECT ...`
- `WITH ... SELECT ...`

Forbidden SQL:

- `INSERT`
- `UPDATE`
- `DELETE`
- `DROP`
- `ALTER`
- `CREATE`
- `TRUNCATE`
- `MERGE`
- `ATTACH`
- `DETACH`
- `PRAGMA`
- `VACUUM`
- `REINDEX`
- `EXEC`
- `CALL`

Also reject multiple statements, SQL comments, and prompt-injection attempts.

## Projection Rules

- Do not allow top-level `SELECT *` in user-visible final projections.
- `COUNT(*)` is allowed.
- Prefer explicit column names and aggregate outputs.

## Execution Rules

- Execute SQL only through `src/db/read_only_executor.py`.
- Use read-only SQLite connections.
- Do not add direct SQLite execution paths in scripts or tests.
- Keep row limits and timeout/guard behavior explicit.
- Default safety validation rejects raw row-level projections without `LIMIT`
  using `RAW_ROW_LIMIT_REQUIRED`; the read-only executor may disable this only
  for already-validated internal execution paths.

## Join Rules

- Do not create synthetic cross-domain joins.
- Cross-domain joins are allowed only when `data/schema/schema_graph.json`
  explicitly allows the edge.
- Validate join paths with the join validator before execution.

## Sensitive Data Rules

For mental-health fields, suicidality, high-risk individuals, or personal
information:

- Prefer aggregate analysis.
- Refuse or abstain on row-level disclosure.
- Never expose names, IDs, emails, phone numbers, or individual rows.
- Do not provide clinical diagnosis, treatment, triage, or individual medical
  decision support.
- Country/year prevalence tables are public aggregate sources; they can expose
  prevalence time series, but not row identifiers.
- Deterministic template SQL must abstain rather than emit row-level sensitive
  student or individual risk rankings.

## Reporting Rules

- Report unsafe SQL count separately.
- Keep behavioral safety outcomes separate from SQL-positive strict EX.
- Do not claim privacy guarantees; use careful wording such as
  "privacy-aware", "local/private", and "read-only execution".

## Required Focused Tests

- destructive SQL rejection
- multiple statement rejection
- comment rejection
- top-level `SELECT *` rejection
- `COUNT(*)` acceptance
- illegal join rejection
- sensitive row-level request refusal
- read-only mutation attempt rejection
