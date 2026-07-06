# Query Shape Contracts

## Purpose

The SQL generator must respect the expected output shape of the user's question.

Most semantic failures happen when the SQL is valid but answers the wrong analytical shape.

## Shape types

### 1. SCALAR

Question asks for one number or one KPI.

Examples:

- تعداد کل رکوردهای دیتاست چیست؟
- میانگین سن دانشجویان چقدر است؟
- چند درصد دانشجویان افسردگی دارند؟
- average sleep چنده؟

Rules:

- Return exactly one row.
- Usually one metric column.
- No GROUP BY unless explicitly requested.
- No hidden segmentation by gender, city, year, depression_flag, diagnosis, or category.
- No LIMIT unless raw rows are requested.
- Use COUNT, AVG, SUM, MIN, MAX, ROUND as needed.

Bad:

```sql
SELECT depression_flag, COUNT(*)
FROM student_depression
GROUP BY depression_flag;
```
for:

تعداد کل رکوردهای دیتاست افسردگی دانشجویان چقدر است؟

Good:

SELECT COUNT(*) AS total_records
FROM student_depression;
2. GROUPED

Question asks for distribution, breakdown, comparison by a dimension.

Examples:

توزیع افسردگی بر اساس جنسیت
میانگین خواب به تفکیک جنسیت
نرخ اضطراب برای هر کشور

Rules:

SELECT must include dimension.
GROUP BY must include dimension.
Aggregation must match metric.
Do not filter to one side when user asks comparison of both sides.
3. RANKING

Question asks for top, highest, lowest, best, worst.

Rules:

Must include ORDER BY.
Must include LIMIT if top-N is specified.
Must define ranking metric.
If ranking metric is missing, ask clarification.
Validator guard:

- `ANALYTICAL_SHAPE_MISSING_RANKING_ORDER_BY`
- `ANALYTICAL_SHAPE_MISSING_RANKING_LIMIT`

Prompt routing guard:

- `ranking_query` must use the generic SQL generation prompt with ranking hints, not the grouped prompt.
- If a ranking query asks for top/highest/lowest/best/worst/most/least without an explicit N, the prompt should steer to `LIMIT 15`.

4. TIMESERIES

Question asks for trend/change over time.

Rules:

Must include year/date dimension.
Must ORDER BY time.
For change/delta, use earliest/latest or LAG when appropriate.
Do not answer latest-year scalar unless user asks latest only.
5. MATRIX

Question asks for matrix, combination, two-dimensional breakdown.

Rules:

GROUP BY at least two dimensions.
Return table-like result.
Avoid joins unless schema graph allows.
6. RAW_ROWS

Question asks for list/show records.

Rules:

Must include LIMIT.
Must not expose sensitive individual information.
SELECT * is forbidden.
Prefer aggregate alternative for sensitive mental-health fields.
Validator guard:

- `ANALYTICAL_SHAPE_MISSING_RAW_ROW_LIMIT`
- `ANALYTICAL_SHAPE_RAW_ROWS_SHOULD_NOT_GROUP`

Prompt routing guard:

- `raw_retrieval_query` must use the generic SQL generation prompt with raw-row hints, not the grouped prompt.
- Raw-row prompt hints must require explicit columns, forbid `SELECT *`, and steer to `LIMIT 100` unless a smaller limit is requested.
- Metadata overview templates that project rows, such as `dim_source`, must also stay bounded with `LIMIT 100`; do not special-case them into unbounded raw output.

7. CLARIFICATION

Use when:

ranking metric missing,
domain ambiguous,
value ambiguous,
cross-domain join not allowed,
user asks causal proof,
user asks for clinical diagnosis,
user asks for personal information,
question depends on previous turn but context is missing.
Shape routing priority
Safety/privacy
Clarification need
Explicit no-SQL/meta/chart advice
Shape detection
Schema/value linking
Generation
Golden rule

Never add analytical dimensions that the user did not ask for.


---

# 5. Safety/privacy rules: `docs/context-hub/SAFETY_PRIVACY_RULES.md`

```md
# Safety and Privacy Rules

## Allowed SQL

Only:

- SELECT ...
- WITH ... SELECT ...

## Forbidden SQL

Always reject:

- INSERT
- UPDATE
- DELETE
- DROP
- ALTER
- CREATE
- TRUNCATE
- REPLACE
- MERGE
- ATTACH
- DETACH
- PRAGMA
- VACUUM
- REINDEX
- EXEC
- EXECUTE
- CALL

## Multiple statements

Reject multiple statements.

Bad:

```sql
SELECT COUNT(*) FROM student_depression; DROP TABLE student_depression;
SQL comments

Reject SQL comments in generated SQL:

--
/* ... */
SELECT star

Reject top-level:

SELECT *
SELECT table.*

Allow:

COUNT(*)
Sensitive mental-health fields

Sensitive topics include:

depression
anxiety
stress
suicidality
high-risk individuals
mental-health diagnosis
treatment seeking
personal identifiers
Sensitive data policy

Allowed:

aggregate counts,
rates,
averages,
distributions,
anonymized group-level results.

Forbidden:

names,
student IDs,
emails,
phone numbers,
addresses,
exact person-level rows,
all high-risk individuals,
all suicidal individuals,
raw records for sensitive groups.
Cross-domain joins

Default:

Cross-domain joins are forbidden unless explicitly allowed in schema_graph.json.

If user asks a multi-domain question without an allowed edge:

ask clarification,
offer separate dashboard summaries,
do not fabricate joins.
Clinical policy

The system must not:

diagnose,
triage,
recommend treatment,
claim clinical validity,
identify individuals at risk.

Allowed wording:

"This result is for research analytics only and is not clinical advice."

Research integrity risks

Refuse or clarify when the user asks to:

cherry-pick supportive results,
fabricate numbers,
ignore ethical limits,
hide uncertainty,
modify data to confirm a hypothesis.


---

# 5. Safety/privacy rules: `docs/context-hub/SAFETY_PRIVACY_RULES.md`

```md
# Safety and Privacy Rules

## Allowed SQL

Only:

- SELECT ...
- WITH ... SELECT ...

## Forbidden SQL

Always reject:

- INSERT
- UPDATE
- DELETE
- DROP
- ALTER
- CREATE
- TRUNCATE
- REPLACE
- MERGE
- ATTACH
- DETACH
- PRAGMA
- VACUUM
- REINDEX
- EXEC
- EXECUTE
- CALL

## Multiple statements

Reject multiple statements.

Bad:

```sql
SELECT COUNT(*) FROM student_depression; DROP TABLE student_depression;

SQL comments

Reject SQL comments in generated SQL:

--
/* ... */
SELECT star

Reject top-level:

SELECT *
SELECT table.*

Allow:

COUNT(*)
Sensitive mental-health fields

Sensitive topics include:

depression
anxiety
stress
suicidality
high-risk individuals
mental-health diagnosis
treatment seeking
personal identifiers
Sensitive data policy

Allowed:

aggregate counts,
rates,
averages,
distributions,
anonymized group-level results.

Forbidden:

names,
student IDs,
emails,
phone numbers,
addresses,
exact person-level rows,
all high-risk individuals,
all suicidal individuals,
raw records for sensitive groups.
Cross-domain joins

Default:

Cross-domain joins are forbidden unless explicitly allowed in schema_graph.json.

If user asks a multi-domain question without an allowed edge:

ask clarification,
offer separate dashboard summaries,
do not fabricate joins.
Clinical policy

The system must not:

diagnose,
triage,
recommend treatment,
claim clinical validity,
identify individuals at risk.

Allowed wording:

"This result is for research analytics only and is not clinical advice."

Research integrity risks

Refuse or clarify when the user asks to:

cherry-pick supportive results,
fabricate numbers,
ignore ethical limits,
hide uncertainty,
modify data to confirm a hypothesis.



---

# 6. Benchmark and artifact protocol: `docs/context-hub/ARTIFACT_RULES.md`

```md
# Benchmark And Artifact Protocol

## Dataset separation

There are two evaluation families.

### SQL-positive

Used for strict SQL execution metrics.

Metrics:

- EX
- conservative EX
- valid SQL rate
- result hash match
- missing SQL rate
- execution error rate
- latency

Semantic/business correctness is a separate evaluation family and must not be
combined with strict EX.

### Behavioral

Used for expected action and reliability metrics.

Metrics:

- expected-action accuracy
- clarification accuracy
- safety rejection accuracy
- abstention precision
- abstention recall
- unsafe SQL generated

Behavioral cases must not be mixed into strict EX denominator.

## Denominators

Always report denominator explicitly.

Examples:

- EX = correct / executable-or-generated attempts
- conservative EX = correct / all SQL-positive cases
- valid SQL = valid / generated SQL attempts

If generated SQL is missing, report missing count separately.

## Main paper run

Main local no-template run must have:

- deterministic_templates=false
- no gold leakage
- self-overlap retrieval excluded
- config saved
- predictions saved
- summary saved
- manifest saved

## Gold run

Gold run is a sanity check.

It proves:

- database works,
- gold SQL executes,
- result hash computation works.

It must not be compared as a model.

## Ablation

Ablation must use:

- same dataset split,
- same selected cases hash,
- same model,
- same benchmark runner,
- same metric contract.

Report:

- A0 direct schema only
- A1 + Persian NLU
- A2 + schema linking
- A3 + value linking
- A4 + CAG examples
- A7 full stack
- candidate verifier if added
- reliability gate if added

## Semantic judge

Semantic/business judge must be reported separately from EX.

Allowed:

"Semantic/business correctness under LLM judge"

Forbidden:

"Human accuracy"

unless human audit exists.

## Required artifact fields

Every run must save:

- run_id
- timestamp
- git_commit
- model
- model_path
- dataset_path
- dataset_hash
- selected_cases_hash
- config_path
- prompt_version
- deterministic_templates
- max_retries
- context_window
- predictions_path
- failures_path
- summary_path
- metrics


