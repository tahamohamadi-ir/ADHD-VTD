# Failure Patterns

## Canonical Error Taxonomy (2026-07-05)

Use this taxonomy for development triage, benchmark summaries, and risk
tracking. Do not merge these families into one score. SQL-positive execution,
behavioral expected-action, semantic/business judge, safety/privacy, latency,
and artifact-governance outcomes have different denominators and must be
reported separately.

### SQL-Positive Execution Errors

| Code | Meaning | Typical owner | Required guard |
|---|---|---|---|
| `MISSING_SQL` | The model produced no executable SQL for a SQL-positive case. | generation, parser | output parser test, conservative denominator |
| `INVALID_SQL` | SQL failed syntax or structural validation. | generation, sql_validation | syntax/schema validator regression |
| `UNSAFE_SQL` | SQL violates read-only or privacy rules. | sql_validation, db | safety validator and read-only executor tests |
| `RESULT_MISMATCH` | SQL executes but result differs from gold result. | generation, schema, validation | artifact summary and failure taxonomy |
| `WRONG_SHAPE` | Scalar/grouped/ranking/timeseries/matrix shape does not match the user request. | query-shape router, prompts, shape validator | query-shape contract tests |
| `WRONG_DOMAIN` | The query uses the wrong table/domain. | NLU, schema linking | domain routing and schema graph tests |
| `WRONG_FILTER` | SQL adds, omits, or changes a filter not requested by the user. | prompts, value linking | hidden-filter and value-linking tests |
| `WRONG_AGGREGATION` | Aggregate function or denominator is wrong. | prompts, metrics definitions, shape validator | metric-definition and aggregate tests |
| `WRONG_JOIN` | Join is unsupported or cross-domain without a schema-graph edge. | join validator | schema graph and join validator tests |
| `UNBOUNDED_RAW_PROJECTION` | SQL returns raw rows without an explicit LIMIT, including metadata overview templates. | generation, sql_validation | raw-row safety tests and template regression tests |

### Behavioral Evaluation Errors

| Code | Meaning | Required guard |
|---|---|---|
| `WRONG_ACTION` | The system chose the wrong expected action: answer, clarify, refuse, or abstain. | action normalizer and behavioral metrics tests |
| `MISSED_CLARIFICATION` | Ambiguous input was answered instead of clarified. | ambiguity routing tests |
| `MISSED_REFUSAL` | Unsafe/sensitive row-level request was not refused. | safety/privacy tests |
| `OVER_REFUSAL` | Safe aggregate request was refused unnecessarily. | behavioral regression tests |

Behavioral cases are not strict execution-accuracy cases. Behavioral and
SQL-positive metric families have different denominators and must be reported
separately. Never put behavioral expected-action rows in the SQL-positive EX
denominator.

### Semantic/Business Judge Errors

| Code | Meaning | Required guard |
|---|---|---|
| `BUSINESS_INCORRECT` | Generated SQL does not answer the user's business question. | semantic/business judge or human review |
| `STRICT_REFERENCE_INCORRECT` | Generated SQL does not match the reference/gold expectation under strict policy. | strict judge policy |
| `ADJUDICATION_REQUIRED` | Authoritative judges disagree. | human review or predeclared third-judge protocol |
| `PROVIDER_ERROR` | Judge provider call failed. | rerun or replace with predeclared provider |
| `PROVIDER_PARSE_ERROR` | Judge response could not be parsed as an authoritative label. | parser hardening, targeted rerun, merge policy |

Provider errors and provider parse errors are provider-state outcomes, not
correctness labels. Do not infer semantic/business correctness from them.

### Candidate and Adaptive-Policy Diagnostics

| Code | Meaning | Required guard |
|---|---|---|
| `CANDIDATE_SELECTION_UNPROVEN` | Candidate adoption has diagnostic evidence only. | promotion registry and release gate |
| `CANDIDATE_DIVERSITY_LOW` | Candidates are too similar to provide useful verifier signal. | aggregate diversity summary |
| `LATENCY_BUDGET_EXCEEDED` | Candidate/adaptive mode violates explicit p95 or mean latency budget. | aggregate latency diagnostics |
| `GOLD_LEAKAGE_RISK` | Candidate scoring or review package includes gold SQL, case labels, or correctness fields. | no-gold-leakage tests and release gate |

Candidate diagnostics may support engineering triage. They do not create paper
metrics until the corresponding artifacts are authoritative and promoted.

### Artifact and Reporting Errors

| Code | Meaning | Required guard |
|---|---|---|
| `ARTIFACT_INCOMPLETE` | Missing config, predictions, summary, manifest, hash, or model metadata. | artifact verifier |
| `PROMOTION_BLOCKED` | Artifact is diagnostic, pending review, smoke, shadow, SPL, failed, or otherwise not paper-final. | promotion registry |
| `METRIC_FAMILY_MIXED` | SQL-positive, behavioral, semantic/business, or latency metrics are combined incorrectly instead of being reported separately with different denominators. | release-gate doc scan |
| `STALE_REFERENCE` | Docs or prompts point to removed/renamed paths or obsolete flags. | release-gate stale-reference checks |

Paper-facing results must be regenerated from verified artifacts. Do not edit
final tables or metrics by hand.

## Known major failure classes

### 1. Scalar question converted to grouped analysis

Example:

User asks:

```text
تعداد کل رکوردهای دیتاست چیست؟
```

Bad SQL:

SELECT depression_flag, COUNT(*)
FROM student_depression
GROUP BY depression_flag;

Correct SQL:

SELECT COUNT(*) AS total_records
FROM student_depression;

Fix:

query shape router,
scalar prompt,
shape validator forbids GROUP BY.
2. Extra hidden filter

User asks for total dataset count.

Bad SQL adds:

WHERE depression_flag = 1

Fix:

prompt rule: do not add WHERE if user did not specify filter.
shape/unit test: no extra filter.
3. Wrong rate denominator

User asks rate/percentage.

Bad:

COUNT(depression_flag)

Good:

ROUND(100.0 * SUM(depression_flag) / COUNT(*), 2)

or:

ROUND(100.0 * AVG(depression_flag), 2)

if binary flag is 0/1.

4. Two-sided comparison filtered to one side

User asks:

مقایسه دانشجویان افسرده و غیرافسرده

Bad:

WHERE depression_flag = 1

Good:

GROUP BY depression_flag
5. Wrong domain/table

User asks country-level prevalence but model uses student_depression.

Fix:

domain classifier,
schema linker role labels,
glossary routing.

6. Forbidden synthetic join

Model joins tables without graph edge.

Fix:

join validator,
schema graph context,
clarification if multi-domain.

7. Noisy robustness SQL-positive cases fail

Typo/Finglish/multi-turn SQL-positive cases currently need stronger normalization, context handling, and paraphrase retrieval.
Behavioral action metrics and SQL-positive robustness use different denominators and must be reported separately.

Fix:

colloquial mapper,
Finglish aliases,
term expansion,
route-specific prompts.

8. Unbounded raw or metadata projection

User asks for a list or overview of records.

Bad:

SELECT source_name, file_name, row_count
FROM dim_source
ORDER BY row_count DESC;

Good:

SELECT source_name, file_name, row_count
FROM dim_source
ORDER BY row_count DESC
LIMIT 100;

Fix:

raw-row safety validator,
template regression test,
prompt hint requiring explicit columns and LIMIT.


---

# 9. Codex Skills

حالا skills اصلی. هر skill را در مسیر خودش بگذار.

---

## Skill 1: `.codex/skills/pars_sql_architecture/SKILL.md`

```md
# Skill: PARS-SQL Architecture

## Purpose

Use this skill when changing architecture, module boundaries, graph workflow, or repository structure.

## Required context

Read:

- `AGENTS.md`
- `docs/context-hub/PROJECT_RULES.md`
- `docs/context-hub/INDEX.md`
- `src/graph/workflow.py`
- `src/graph/state.py`
- `src/graph/routes.py`

## Rules

1. Do not add new architecture without connecting it to benchmark/evaluation.
2. Do not bypass validation or read-only execution.
3. Do not create hidden dependencies between modules.
4. Do not move files without updating imports and tests.
5. Keep graph nodes small and testable.
6. If splitting `base_nodes.py`, preserve behavior first, then refactor.

## Preferred architecture

Pipeline order:

1. normalize
2. safety intent
3. ambiguity detection
4. intent/shape routing
5. QIR construction
6. schema linking
7. value linking
8. retrieval/CAG
9. prompt building
10. SQL generation
11. output parsing
12. validation
13. shape contract validation
14. read-only execution
15. reliability decision
16. final answer formatting
17. trace/artifact logging

## Deliverables

When using this skill, return:

- architecture change summary
- files changed
- backward compatibility risks
- tests needed
- migration notes

