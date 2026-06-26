# PARS-SQL Paper 1 Current Results Summary

Last updated: 2026-06-26

This is a status summary, not the final paper results package. It records only artifact-backed results that currently exist in `results/`.

## What Is Done

### B0 Blockers

All B0 blockers in `docs/PARS_SQL_PAPER1_IMPLEMENTATION_PLAN.md` are closed:

- Dataset contract types.
- Central trace contract.
- Parse failure hardening.
- Graph routing consistency.
- Safety/privacy behavioral gate.
- Reranker CLI contract.

Tier 1 verification after B1.2 changes:

```text
411 passed, 3 warnings
```

### B1.1 Gold SQL Closeout

Artifact:

```text
results/benchmark/20260621_064906_gold_positive400_qwen2-5-coder-7b_paper1_gold_positive400
```

Result:

```text
total_evaluated = 400
execution_accuracy = 1.0
valid_sql_rate = 1.0
failures = 0
unsafe_sql = 0
trace_contract.validated = true
```

### B1.2 Behavioral Test

Artifact:

```text
results/benchmark/20260621_072711_agent_behavior_test_qwen2-5-coder-7b_paper1_behavior_test_b1_2_actionfix
```

Result:

```text
total_evaluated = 60
expected_action_accuracy = 52/60 = 0.8667
safety_rejection_accuracy = 10/10 = 1.0
clarification_accuracy = 13/14 = 0.9286
abstention_precision = 50/56 = 0.8929
abstention_recall = 50/50 = 1.0
unsafe_sql = 0
valid_sql_rate on SQL-positive behavioral cases = 6/10 = 0.6
execution_accuracy on SQL-positive behavioral cases = 0/10 = 0.0
trace_contract.validated = true
```

Interpretation:

- Safety, privacy refusal, clarification, and abstention behavior is now strong enough to be reported.
- Robust SQL generation for typo/Finglish/cross-source behavioral cases is still weak and should be discussed as a limitation or fixed in a later phase.

### B1.3 No-Template Local Agent Full Run

Full `positive400` no-template run is complete and artifact-backed.

Initial 5-case smoke artifact:

```text
results/benchmark/20260621_073923_agent_positive400_qwen2-5-coder-7b_paper1_main_local_no_templates_smoke
```

Result:

```text
sample = 5
execution_accuracy = 3/5 = 0.6
valid_sql_rate = 5/5 = 1.0
expected_action_accuracy = 5/5 = 1.0
trace_contract.validated = true
deterministic_templates = false
llm_context_window = 8192
```

Diagnostic full attempt:

```text
results/benchmark/20260621_104339_agent_positive400_qwen2-5-coder-7b_paper1_main_local_no_templates
```

Result:

```text
partial = 9/400
status = stopped manually as diagnostic only
reason = default max_retries=5 caused long repair/reflexion loops on failing average cases
paper_result = false
```

Bounded runtime support was added after this diagnostic run:

```text
features.max_retries in YAML -> VTDState.max_retries -> initialize_trace
summary/config artifacts record max_retries and max_retries_source
abstention is now reported as a locked runtime policy, not an unknown flag
```

Final bounded 10-case smoke artifact:

```text
results/benchmark/20260621_112756_paper1_main_local_no_templates_bounded_smoke
```

Result:

```text
sample = 10
execution_accuracy = 4/10 = 0.4
valid_sql_rate = 10/10 = 1.0
expected_action_accuracy = 7/10 = 0.7
max_retries = 1
max_retries_source = config
trace_contract.validated = true
ablation_runtime_contract.warnings = []
latency_ms_mean = 26375.4
```

Interpretation:

- The 5-case and 10-case smokes must not be reported as main performance.
- The full Paper 1 run used `experiments/configs/paper1_main_local_no_templates_bounded.yaml`.

Full artifact:

```text
results/benchmark/20260621_122748_paper1_main_local_no_templates_bounded
```

Full result:

```text
total_evaluated = 400
execution_accuracy = 102/394 = 0.2589
valid_sql_rate = 295/394 = 0.7487
expected_action_accuracy = 216/400 = 0.54
failures = 298
RESULT_MISMATCH = 199
INVALID_SQL = 93
MISSING_GENERATED_SQL = 6
max_retries = 1
max_retries_source = config
deterministic_templates = false
trace_contract.validated = true
latency_ms_mean = 29385.6
```

Interpretation:

- This is the main local no-template result for Paper 1.
- Performance is low but defensible as a local/private Persian-first reliability baseline if framed honestly.
- Error analysis should lead the discussion: most failures require semantic review or better SQL/result alignment.

### Behavioral100 Full

Behavior test artifact:

```text
results/benchmark/20260621_072711_agent_behavior_test_qwen2-5-coder-7b_paper1_behavior_test_b1_2_actionfix
```

Behavior dev artifact:

```text
results/benchmark/20260621_205133_agent_behavior_dev_qwen2_5-coder-7b-instruct-q4_k_m_paper1_behavior_dev_full
```

Combined result:

```text
total_evaluated = 100
expected_action_accuracy = 76/100 = 0.76
safety_rejection_accuracy = 16/16 = 1.0
clarification_accuracy = 22/25 = 0.88
abstention_precision = 80/90 = 0.8889
abstention_recall = 80/83 = 0.9639
SQL-positive valid_sql_rate = 11/17 = 0.6471
SQL-positive execution_accuracy = 0/17 = 0.0
unsafe_sql = 0
```

Interpretation:

- Behavioral100 is now fully evaluated.
- Safety and abstention are strong.
- Expected-action accuracy is below the recommended 80% target because behavior_dev adds out-of-schema/no-SQL/action mismatch failures.
- SQL-positive robustness in behavioral cases remains weak.

### B1.4 Retrieval R0-R3 Full Dev

Manifest:

```text
results/ablation/paper1_retrieval_final_dev_full/ablation_manifest.json
```

Artifacts:

```text
results/benchmark/20260621_074119_r0_retrieval_bm25_dev_full
results/benchmark/20260621_074120_r1_retrieval_vector_dev_full
results/benchmark/20260621_074127_r2_retrieval_hybrid_dev_full
results/benchmark/20260621_074133_r3_retrieval_hybrid_rerank_dev_full
```

Result:

```text
cases per run = 60
failures per run = 0
selected_cases_hash = d83596c1a3f32e1bf4e27a7db38cd7cab0c27632ca77ba0da91ee0d8a40721fa
retrieval_hit_rate = 60/60 = 1.0
retrieval_miss_rate = 0/60 = 0.0
trace_contract.validated = true
```

Latency mean:

```text
R0 BM25 = 2.85ms
R1 vector = 83.38ms
R2 hybrid = 81.45ms
R3 hybrid-rerank identity = 77.23ms
```

Limitation:

- R3 currently uses an identity reranker placeholder. It verifies wiring, not a model-backed reranker claim.

### B1.5 A0-A4/A7 Ablation Smoke

Manifest:

```text
results/ablation/paper1_A0_A4_A7_dev/ablation_manifest.json
```

Analysis:

```text
results/ablation/paper1_A0_A4_A7_dev/ablation_comparison.md
results/ablation/paper1_A0_A4_A7_dev/ablation_comparison.json
```

Result:

```text
jobs_completed = 6/6
same_selected_cases_hash = true
cases_per_config = 8
A0 execution_accuracy = 0.1429, valid_sql_rate = 0.5714
A1 execution_accuracy = 0.1429, valid_sql_rate = 0.7143
A2 execution_accuracy = 0.1429, valid_sql_rate = 0.5714
A3 execution_accuracy = 0.1429, valid_sql_rate = 0.5714
A4 execution_accuracy = 0.2857, valid_sql_rate = 0.5714
A7 execution_accuracy = 0.4286, valid_sql_rate = 0.8571
```

Limitation:

- This is an artifact-backed diagnostic smoke, not paper-grade ablation. The sample is too small for a strong ablation claim.

Full positive400 bounded ablation:

```text
results/ablation/paper1_A0_A4_A7_positive400_split/merged/ablation_manifest.json
results/ablation/paper1_A0_A4_A7_positive400_split/merged/ablation_comparison.md
results/ablation/paper1_A0_A4_A7_positive400_split/merged/ablation_comparison.json
```

Result:

```text
jobs_completed = 6/6
same_dataset_hash = true
same_selected_cases_hash = true
cases_per_config = 400
A0 EX = 41/394 = 0.1041, valid_sql = 269/394 = 0.6827, reliability = -165.25
A1 EX = 42/394 = 0.1066, valid_sql = 269/394 = 0.6827, reliability = -168.25
A2 EX = 42/394 = 0.1066, valid_sql = 264/394 = 0.6701, reliability = -161.50
A3 EX = 41/394 = 0.1041, valid_sql = 266/394 = 0.6751, reliability = -163.00
A4 EX = 101/394 = 0.2563, valid_sql = 274/394 = 0.6954, reliability = -56.50
A7 EX = 101/394 = 0.2563, valid_sql = 276/394 = 0.7005, reliability = -61.25
unsafe_sql = 0 for all configs
```

Interpretation:

- The largest performance change appears when CAG examples are enabled: A3 `41/394` to A4 `101/394`.
- A7 ties A4 on EX and slightly improves valid SQL rate, but does not improve execution accuracy over A4 on positive400.
- This supersedes the full-dev ablation for the main ablation claim.

Full-dev bounded ablation:

```text
results/ablation/paper1_A0_A4_A7_dev_full_bounded/ablation_manifest.json
results/ablation/paper1_A0_A4_A7_dev_full_bounded/ablation_comparison.md
results/ablation/paper1_A0_A4_A7_dev_full_bounded/ablation_comparison.json
```

Configs:

```text
experiments/configs/A0_direct_schema_only_dev_full_bounded.yaml
experiments/configs/A1_persian_nlu_dev_full_bounded.yaml
experiments/configs/A2_schema_linking_dev_full_bounded.yaml
experiments/configs/A3_value_linking_dev_full_bounded.yaml
experiments/configs/A4_cag_examples_dev_full_bounded.yaml
experiments/configs/A7_full_phase10_system_dev_full_bounded.yaml
```

Result:

```text
jobs_completed = 6/6
same_dataset_hash = true
same_selected_cases_hash = true
cases_per_config = 60
max_retries = 1
trace_level = compact
deterministic_templates = false
A0 EX = 4/58 = 0.0690, valid_sql = 40/58 = 0.6897, reliability = -25.5
A1 EX = 4/58 = 0.0690, valid_sql = 38/58 = 0.6552, reliability = -24.0
A2 EX = 4/58 = 0.0690, valid_sql = 40/58 = 0.6897, reliability = -25.5
A3 EX = 4/58 = 0.0690, valid_sql = 39/58 = 0.6724, reliability = -25.5
A4 EX = 15/58 = 0.2586, valid_sql = 42/58 = 0.7241, reliability = -4.25
A7 EX = 17/58 = 0.2931, valid_sql = 40/58 = 0.6897, reliability = 1.25
unsafe_sql = 0 for all configs
```

Interpretation:

- The largest performance change appears when CAG examples are enabled: A3 `4/58` to A4 `15/58`.
- A7 is the best full-dev configuration by EX and reliability score, but it remains low in absolute execution accuracy and has higher latency.
- This is a full-dev ablation result, not a full positive400 ablation result.

### Error Analysis

Artifact:

```text
results/error_analysis/paper1_main_local_bounded/error_report.md
results/error_analysis/paper1_main_local_bounded/analysis_summary.json
```

Result:

```text
total_predictions = 400
total_attempts = 394
total_failures_analyzed = 20
SEMANTIC_REVIEW_REQUIRED = 17
SHAPE_CONTRACT_ERROR = 2
INVALID_SQL = 1
```

### Semantic Judge Attempt

Artifact:

```text
results/judgments/paper1_main_semantic_openrouter
```

Result:

```text
provider = openrouter
model = qwen/qwen3.6-plus
total_judged = 50
failures_only = false
redaction_applied = true
provider_error = 50/50
provider_error_reason = HTTP 402 Payment Required
authoritative = false
semantic_business_counts.unjudged = 50
```

Interpretation:

- This run verifies the redacted judge artifact path, but it does not provide semantic correctness evidence.
- Do not cite semantic judge accuracy from this artifact.

Mock sanity run:

```text
results/judgments/paper1_main_semantic_mock_s50
```

Mock result:

```text
provider = mock
model = deterministic_exact_match_v0
total_judged = 50
exact_sql_match = 19
invalid_sql = 2
requires_semantic_review = 11
unjudged = 18
authoritative = false
```

Interpretation:

- The mock run confirms the judge pipeline can produce artifacts.
- The mock run is not semantic/business correctness evidence and must not be used as an authoritative paper claim.

Successful OpenRouter probe:

```text
results/judgments/paper1_main_semantic_openrouter_s3_probe
```

Probe result:

```text
provider = openrouter
model = qwen/qwen3.6-plus
total_judged = 3
authoritative = true
authoritative_judgments = 3
business_correct = 2
business_incorrect = 1
redaction_applied = true
```

Interpretation:

- The OpenRouter provider path is working after the previous `HTTP 402` failure.
- This 3-case probe is not enough for paper claims; it only gated the later semantic/business judge reruns.

Authoritative 50-case OpenRouter semantic/business judge:

```text
results/judgments/paper1_main_semantic_openrouter_s50_rerun
```

Result:

```text
provider = openrouter
model = qwen/qwen3.6-plus
prompt_version = phase16_sql_business_logic_v1
judge_policy = semantic_user_question
sample_size = 50
total_judged = 50
authoritative = true
authoritative_judgments = 50
business_correct = 39/50 = 0.78
business_incorrect = 11/50 = 0.22
provider_error = 0
provider_parse_error = 0
redaction_applied = true
raw_rows_sent = false
result_previews_sent = false
prompt_response_trace_sent = false
input_tokens = 36142
output_tokens = 64304
estimated_cost_usd = 0.0
```

Interpretation:

- This was the first successful semantic/business judge subset.
- It is superseded by the full 400-case authoritative judge below for the current paper package.

Authoritative full 400-case OpenRouter semantic/business judge:

```text
results/judgments/paper1_main_semantic_openrouter_s400_split/merged_authoritative
```

Result:

```text
provider = openrouter
model = qwen/qwen3.6-plus
prompt_version = phase16_sql_business_logic_v1
judge_policy = semantic_user_question
total_judged = 400
authoritative = true
authoritative_judgments = 400
non_authoritative_judgments = 0
business_correct = 161/400 = 0.4025
business_incorrect = 239/400 = 0.5975
invalid_sql = 20
missing_sql = 6
provider_error = 0
provider_parse_error = 0
redaction_applied = true
raw_rows_sent = false
result_previews_sent = false
prompt_response_trace_sent = false
input_tokens = 347343
output_tokens = 731993
estimated_cost_usd = 0.0
```

Interpretation:

- This is the current semantic/business correctness audit for Paper 1.
- It must be reported separately from strict execution accuracy.
- The result is lower than the earlier 50-case subset and should be treated as the stronger, more representative evidence.

## What Is Still Missing

1. Optional clean paraphrase holdout for a stronger anti-overfit claim.
2. Optional human spot-check of a sample of the 400 OpenRouter semantic/business judgments before final paper submission.

Current table pack:

```text
results/reports/paper_tables.md
```

Current final artifact manifest:

```text
results/reports/final_artifact_manifest.json
```
