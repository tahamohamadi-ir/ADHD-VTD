# PARS-SQL Context Hub

Use this file to decide which context to load. Do not load all docs for every task.

## SQL generation quality task

Open:

- `docs/context-hub/QUERY_SHAPE_CONTRACTS.md`
- `docs/context-hub/FAILURE_PATTERNS.md`
- relevant prompt file under `src/generation/prompts/`

Do not open unrelated benchmark artifacts unless needed.

## Safety/privacy task

Open:

- `docs/context-hub/SAFETY_PRIVACY_RULES.md`
- `data/schema/schema_graph.json`
- `data/schema/business_glossary.fa.json`
- `src/sql_validation/safety_validator.py`
- `src/db/read_only_executor.py`

## Benchmark/evaluation task

Open:

- `docs/context-hub/BENCHMARK_PROTOCOL.md`
- `docs/context-hub/ARTIFACT_RULES.md`
- `src/evaluation/metrics.py`
- `src/evaluation/action_normalizer.py`
- `scripts/run_benchmark.py`

## Artifact/reproducibility task

Open:

- `docs/context-hub/ARTIFACT_RULES.md`
- `scripts/verify_artifact.py`
- `scripts/make_paper_tables.py`
- latest manifest file

## Persian NLU/schema-linking task

Open:

- `docs/context-hub/QUERY_SHAPE_CONTRACTS.md`
- `data/schema/column_aliases.fa.json`
- `data/schema/business_glossary.fa.json`
- `data/schema/metric_definitions.json`
- `src/nlu/`
- `src/schema/`

## Paper claim task

Open:

- `docs/context-hub/BENCHMARK_PROTOCOL.md`
- `docs/context-hub/ARTIFACT_RULES.md`
- `docs/context-hub/FAILURE_PATTERNS.md`
- latest `paper_tables.md`
- latest artifact manifest

## Rule

Load the smallest possible context.
Large context hurts coding-agent performance and increases the chance of over-editing.