# VTD / PARS-SQL Dataset Card

Last updated: 2026-06-21

## Dataset Name

VTD Health Intelligent Dashboard Persian NL2SQL Dataset

## Version and Scope

This card documents the dataset package used for Paper 1 of PARS-SQL:

- `positive400`: 400 SQL-positive Persian/Text-to-SQL examples.
- `behavioral100`: 100 behavioral/reliability examples split as `behavior_dev=40` and `behavior_test=60`.
- `vtd_total_500_dataset_package`: package view of the 400 + 100 examples.

The dataset is for research evaluation of Persian-aware, reliability-first Text-to-SQL over mental-health and student-lifestyle analytics.

## Database

```text
Database: vtd_health_research_v1.db
Dialect: SQLite
Evaluation mode: read-only SELECT execution
```

## Intended Use

- Persian Text-to-SQL evaluation.
- Local/open-weight LLM benchmarking.
- Schema/value linking evaluation.
- CAG/retrieval evaluation.
- Behavioral evaluation for ambiguity, unsafe requests, out-of-schema requests, no-SQL answers, chart advice, typo/Finglish, and multi-turn-like utterances.
- Reproducible research artifacts for PARS-SQL Paper 1.

## Not Intended For

- Clinical diagnosis.
- Treatment, triage, or individual medical decision-making.
- Re-identification or individual-level sensitive lookup.
- Deployment as a medical device or clinical assistant.
- Cloud/API evaluation with private or identifiable records.

## Composition

```text
SQL-positive examples: 400
Behavioral examples: 100
Total package size: 500
Positive split: train/dev/test = 280/60/60
Behavioral split: behavior_dev/behavior_test = 40/60
```

Behavioral examples must not be mixed into the denominator for SQL execution accuracy. They are evaluated with action/reliability metrics such as expected-action accuracy, safety rejection, clarification accuracy, and abstention precision/recall.

## Current Artifact-Backed Audit Status

- `positive400` gold SQL closeout is complete.
- Gold executor artifact:
  `results/benchmark/20260621_064906_gold_positive400_qwen2-5-coder-7b_paper1_gold_positive400`
- Result: `400/400` executed successfully, `execution_accuracy=1.0`, `valid_sql_rate=1.0`, `failures=0`.
- `behavior_test` full run is complete.
- Behavioral artifact:
  `results/benchmark/20260621_072711_agent_behavior_test_qwen2-5-coder-7b_paper1_behavior_test_b1_2_actionfix`
- Result: `expected_action_accuracy=52/60=0.8667`, `unsafe_sql=0`, `safety_rejection_accuracy=1.0`, `abstention_recall=1.0`.
- Full `behavior_dev=40` has not yet been run as a final artifact; only a 20-case smoke exists.

## Annotation and Audit Notes

The benchmark is primarily author-created and research-oriented. The paper should explicitly report:

- Gold SQL execution audit status.
- Any single-annotator limitations.
- Whether a second reviewer or LLM-as-judge subset was used.
- Agreement percentage or Cohen's kappa if second-review annotation is completed.
- Known failures and limitations for typo/Finglish/cross-source behavioral SQL-positive cases.

## Leakage and Split Policy

- `train/dev/test` reconstruct `positive400`.
- `behavior_dev/behavior_test` reconstruct `behavioral100`.
- Debug subsets such as `phase18_7b_failed154`, `phase18_7c0_failed266`, and `phase18_7c0_lost119` are debug-only and must not be cited as clean holdout evidence.
- Because some debug failure subsets previously touched test cases, a future clean anti-overfit claim should use an independent paraphrase holdout.

## Safety and Privacy Policy

The benchmark is aggregate-analytics oriented. The system must refuse or abstain on:

- Destructive SQL or prompt-injection requests.
- Individual-level sensitive mental-health lookup.
- Out-of-schema medical/clinical fields.
- Requests to fabricate, cherry-pick, or hide unsupported mappings.

## Known Limitations

- The dataset is not a clinical benchmark.
- Persian colloquial, Finglish, typo-heavy, and Jalali coverage is useful but not exhaustive.
- `behavior_test` shows strong safety/abstention behavior but weak execution correctness on SQL-positive behavioral robustness cases.
- A model-backed reranker is not yet part of the final retrieval claim; current R3 verifies identity-reranker wiring only.
- Full no-template local agent evaluation over `positive400` is still pending.

