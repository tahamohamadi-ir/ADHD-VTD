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

- `docs/context-hub/ARTIFACT_RULES.md`
- `docs/BENCHMARK_AND_TEST_GUIDE.md` only if command-level detail is needed
- `src/evaluation/metrics.py`
- `src/evaluation/action_normalizer.py`
- `scripts/run_benchmark.py`

## Artifact/reproducibility task

Open:

- `docs/context-hub/ARTIFACT_RULES.md`
- `scripts/check_release_readiness.py`
- `scripts/verify_artifact.py`
- `scripts/package_dual_policy_evidence.py` when semantic/business evidence is in scope
- `scripts/judge_benchmark_artifact.py` when judge artifact evidence is in scope
- `scripts/plan_dual_policy_judge_ablation.py` when judge ablation planning is in scope
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

- `docs/context-hub/ARTIFACT_RULES.md`
- `docs/context-hub/FAILURE_PATTERNS.md`
- `docs/Risks.md`
- latest `paper_tables.md`
- latest artifact manifest

## Final development / risk cleanup planning task

Open:

- `docs/PARS_SQL_PAPER1_IMPLEMENTATION_PLAN.md`
- `docs/07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md`
- `docs/context-hub/FAILURE_PATTERNS.md`
- `docs/context-hub/ARTIFACT_RULES.md`
- `docs/Risks.md`
- `docs/11_SEMANTIC_BUSINESS_LOGIC_EVALUATION.md` when judge evidence,
  disagreement, or human adjudication is in scope

Do not open benchmark prediction files unless a specific artifact check or
failure investigation requires them.

## Rule

Load the smallest possible context.
Large context hurts coding-agent performance and increases the chance of over-editing.
