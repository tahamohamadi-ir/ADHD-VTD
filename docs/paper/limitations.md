# Paper 1 Limitations Draft

Last updated: 2026-07-01

## Clinical Scope

PARS-SQL is not a diagnostic, treatment, triage, or clinical decision system. The dataset and system are intended for aggregate research analytics over synthetic/de-identified mental-health and lifestyle-style data.

## Dataset and Annotation

- Some examples may be single-annotator.
- `positive400` gold SQL execution is fully validated, but behavioral examples evaluate expected action rather than SQL correctness.
- `behavior_test` and `behavior_dev` are both fully evaluated, but combined expected-action accuracy is `76/100`, below the recommended 80% target.
- Debug subsets must not be cited as clean holdout evidence.

## Generalization and Anti-Overfit

- Existing `train/dev/test` splits reconstruct `positive400`.
- Some historical debug subsets were derived from failure cases, so they are not clean final evidence.
- A clean paraphrase holdout is recommended for stronger anti-overfit claims.

## Local Model Performance

- The full no-template local run over `positive400` is complete, but performance is low: `execution_accuracy=102/394=0.2589` and `valid_sql_rate=295/394=0.7487`.
- The 5-case and 10-case no-template smokes verify runtime only and must not be reported as main performance.
- A legacy full-run attempt was stopped after `9/400` cases because `max_retries=5` led to long repair/reflexion loops on failing cases. The follow-up full run should use the bounded config with `max_retries=1`.
- Behavioral SQL-positive robustness cases currently show weak execution correctness, especially typo/Finglish/cross-source cases.
- The `positive400` SQL-positive metrics and behavioral robustness subset use different denominators and must be reported separately.

## Retrieval and Reranking

- R0-R3 full-dev retrieval wiring is artifact-backed.
- R3 currently uses an identity reranker placeholder; it is not a model-backed reranker result.

## Evaluation

- Execution accuracy and semantic/business correctness must remain separate.
- Expected-action accuracy is a behavioral policy metric, not SQL execution accuracy.
- The current A0-A4/A7 ablation includes full positive400 results, but it still omits A5/A6 intermediate variants.
- The positive400 ablation shows that CAG drives the main gain, while A7 does not improve EX over A4 on positive400.
- Cloud or LLM-as-judge evaluation should be used only on safe/synthetic/de-identified artifacts.
- The initial OpenRouter semantic judge attempt failed with `provider_error=50/50`, but later reruns are authoritative.
- The authoritative semantic/business judge now covers all 400 positive predictions in `paper1_main_semantic_openrouter_s400_split/merged_authoritative`.
- The full semantic/business judge result is an LLM-as-judge audit, not a human annotation study; a human spot-check is still recommended before final submission.
- The mock judge sanity run is not an authoritative semantic/business evaluation; it only validates the artifact pipeline.
