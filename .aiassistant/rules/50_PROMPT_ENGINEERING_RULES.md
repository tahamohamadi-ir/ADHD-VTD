# PARS-SQL — Prompt Engineering Rules

Apply this rule when editing:

- `src/generation/prompts/*.j2`
- `src/generation/prompt_builder.py`
- `src/generation/output_parser.py`
- semantic judge prompts,
- repair prompts,
- clarification prompts,
- answer generation prompts.

## Prompt goals

Prompts must reduce valid-but-wrong SQL, not just syntax errors.

## Required prompt constraints

Every SQL generation prompt must:

1. Require valid SQLite SQL.
2. Require JSON output compatible with `OutputParser`.
3. Forbid `SELECT *`.
4. Forbid destructive SQL.
5. Forbid hidden filters.
6. Forbid hidden grouping.
7. Say not to add `WHERE` unless the user explicitly specified a condition.
8. Include query shape requirements.
9. Include clarification path.
10. Avoid chain-of-thought exposure.
11. Use concise fields like `assumptions`, `shape`, and `rationale_short` if needed.

## Recommended output schema

```json
{
  "shape": "scalar|grouped|ranking|timeseries|matrix|raw_rows|clarification",
  "sql": "SELECT ...",
  "needs_clarification": false,
  "clarification_question": null,
  "assumptions": []
}
```

## Required negative examples

When editing prompts, include or preserve examples for:

- scalar question incorrectly using GROUP BY,
- hidden WHERE filter,
- wrong rate denominator,
- forbidden join,
- top-level SELECT *,
- two-sided comparison filtered to one side.

## Repair prompt rules

Repair prompts must:

- fix only reported errors,
- not rewrite the whole query unnecessarily,
- use only schema-provided tables/columns,
- preserve original user intent,
- return JSON.

## Required tests

- `tests/unit/test_output_parser.py`
- prompt snapshot tests if available,
- one generation smoke test for affected shape if available.
