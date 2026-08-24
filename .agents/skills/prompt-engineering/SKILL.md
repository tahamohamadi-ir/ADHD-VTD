---
name: prompt-engineering
description: Use this skill when editing Jinja prompt templates for SQL generation, repair, clarification, answer generation, or semantic judge.
---

# Skill: Prompt Engineering for PARS-SQL

## Purpose

Use this skill when editing Jinja prompt templates for SQL generation, repair, clarification, answer generation, or semantic judge.

## Required context

Read:

- `AGENTS.md`
- `docs/context-hub/QUERY_SHAPE_CONTRACTS.md`
- `docs/context-hub/SAFETY_PRIVACY_RULES.md`
- relevant prompt file only
- relevant failing examples if provided

## Prompt rules

1. Prompts must be shape-specific where possible.
2. Prompt must forbid hidden filters.
3. Prompt must forbid hidden grouping.
4. Prompt must say not to add WHERE if user did not specify a filter.
5. Prompt must use SQLite only.
6. Prompt must require JSON output.
7. Prompt must include refusal/clarification path.
8. Prompt must not expose chain-of-thought.
9. Prompt must include compact reasoning fields only if needed, such as assumptions or rationale_short.

## Required output schema

For SQL generation:

```json
{
  "shape": "scalar|grouped|ranking|timeseries|matrix|raw_rows",
  "sql": "...",
  "needs_clarification": false,
  "clarification_question": null,
  "assumptions": []
}
```
Negative examples required

Every prompt must include at least one negative example for:

hidden GROUP BY,
hidden WHERE,
wrong rate formula,
forbidden join,
SELECT *.
Tests required
prompt snapshot test if available
output parser test
one generation smoke test for affected shape
Output format

Return:

prompt changed
old failure addressed
negative example added
parser compatibility
test commands


