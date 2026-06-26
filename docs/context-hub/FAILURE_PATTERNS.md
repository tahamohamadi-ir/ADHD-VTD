# Failure Patterns

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
7. Behavioral SQL-positive noisy cases fail

Typo/Finglish/multi-turn SQL-positive cases currently need stronger normalization, context handling, and paraphrase retrieval.

Fix:

colloquial mapper,
Finglish aliases,
term expansion,
route-specific prompts.


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

