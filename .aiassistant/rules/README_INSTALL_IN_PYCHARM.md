# How to Install These Rules in PyCharm AI Assistant

These files are designed for:

`Tools → AI Assistant → Rules → New Project Rules File...`

## Recommended import order

1. `00_GLOBAL_PARS_SQL_RULES.md`
2. `10_SQL_SAFETY_PRIVACY_RULES.md`
3. `20_QUERY_SHAPE_GENERATION_RULES.md`
4. `30_BENCHMARK_ARTIFACT_REPRO_RULES.md`
5. `40_PERSIAN_NLU_SCHEMA_LINKING_RULES.md`
6. `50_PROMPT_ENGINEERING_RULES.md`
7. `60_PAPER_CLAIM_GOVERNANCE_RULES.md`

## Suggested Apply Rule settings

If PyCharm offers an Always option:

- Set `00_GLOBAL_PARS_SQL_RULES.md` to Always.

For the other files, use automatic/path/context-based application if available.

## Suggested mapping

### `10_SQL_SAFETY_PRIVACY_RULES.md`

Apply to:

- `src/sql_validation/**`
- `src/db/**`
- `src/nlu/safety_intent_detector.py`
- `data/schema/schema_graph.json`

### `20_QUERY_SHAPE_GENERATION_RULES.md`

Apply to:

- `src/generation/**`
- `src/sql_validation/shape_*`
- `src/sql_validation/sql_rewriter.py`
- `src/core/query_ir.py`
- `src/graph/nodes/*generation*`
- `src/graph/nodes/*validation*`

### `30_BENCHMARK_ARTIFACT_REPRO_RULES.md`

Apply to:

- `scripts/**`
- `src/evaluation/**`
- `results/**`
- `data/questions/**`
- `docs/paper/**`

### `40_PERSIAN_NLU_SCHEMA_LINKING_RULES.md`

Apply to:

- `src/nlu/**`
- `src/schema/**`
- `data/schema/**`

### `50_PROMPT_ENGINEERING_RULES.md`

Apply to:

- `src/generation/prompts/**`
- `src/generation/prompt_builder.py`
- `src/generation/output_parser.py`
- judge or repair prompt files

### `60_PAPER_CLAIM_GOVERNANCE_RULES.md`

Apply to:

- `docs/**`
- `paper/**`
- `README*.md`
- `DATASET_CARD*.md`
- `limitations*.md`
- `paper_tables*.md`
- manuscript files

## If PyCharm does not allow path matching

Set:

- `00_GLOBAL_PARS_SQL_RULES.md`: Always
- others: Manual / Ask / Contextual if available

Then mention the exact rule name in your prompt, for example:

"Use the Query Shape Generation Rules."

## Recommended first prompt after installing

Ask AI Assistant:

"Read the project rules. Then summarize the non-negotiable constraints for PARS-SQL before making any code changes."

If it does not mention safety validation, read-only execution, strict EX and
behavioral metrics being reported separately with different denominators, and
query-shape rules, your rules are not being applied strongly enough.
