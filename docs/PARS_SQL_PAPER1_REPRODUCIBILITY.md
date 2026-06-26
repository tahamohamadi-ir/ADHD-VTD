# PARS-SQL Paper 1 Reproducibility Notes

Last updated: 2026-06-26

## Environment

```powershell
cd D:\Project\ADHD-VTD
.\.venv\Scripts\python.exe --version
```

The current local generation model used by the recent runs is:

```text
models/generation/qwen2.5-coder-7b-instruct-q4_k_m.gguf
```

## Unit Tests

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit -q
```

Latest recorded result:

```text
411 passed, 3 warnings
```

## Gold SQL Closeout

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --mode gold `
  --dataset positive400 `
  --sample 0 `
  --bootstrap-iterations 1000 `
  --trace-level compact `
  --ablation-id paper1_gold_positive400
```

Current artifact:

```text
results/benchmark/20260621_064906_gold_positive400_qwen2-5-coder-7b_paper1_gold_positive400
```

## Behavioral Test

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --mode agent `
  --dataset behavior_test `
  --sample 0 `
  --top-k 5 `
  --exclude-self `
  --bootstrap-iterations 1000 `
  --trace-level compact `
  --ablation-id paper1_behavior_test_b1_2_actionfix
```

Current artifact:

```text
results/benchmark/20260621_072711_agent_behavior_test_qwen2-5-coder-7b_paper1_behavior_test_b1_2_actionfix
```

## No-Template Local Agent Smoke

Run:

```powershell
$env:VTD_LLM_N_CTX="8192"
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --mode agent `
  --dataset positive400 `
  --sample 5 `
  --top-k 5 `
  --exclude-self `
  --bootstrap-iterations 200 `
  --trace-level compact `
  --ablation-id paper1_main_local_no_templates_smoke
```

Current artifact:

```text
results/benchmark/20260621_073923_agent_positive400_qwen2-5-coder-7b_paper1_main_local_no_templates_smoke
```

## Bounded No-Template Local Agent Smoke

Run:

```powershell
$env:VTD_LLM_N_CTX="8192"
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\paper1_main_local_no_templates_bounded_smoke.yaml
```

Current artifact:

```text
results/benchmark/20260621_112756_paper1_main_local_no_templates_bounded_smoke
```

Current result:

```text
sample = 10
execution_accuracy = 4/10 = 0.4
valid_sql_rate = 10/10 = 1.0
expected_action_accuracy = 7/10 = 0.7
max_retries = 1
max_retries_source = config
trace_contract.validated = true
ablation_runtime_contract.warnings = []
```

## Full No-Template Local Agent Run

Run:

```powershell
$env:VTD_LLM_N_CTX="8192"
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\paper1_main_local_no_templates_bounded.yaml
```

Important:

- Do not cite the 5-case or 10-case smokes as main performance.
- Confirm `module_flags.deterministic_templates=false` in the summary.
- Confirm `max_retries=1` and `max_retries_source=config` in the summary.
- Confirm `trace_contract.validated=true`.

Current artifact:

```text
results/benchmark/20260621_122748_paper1_main_local_no_templates_bounded
```

Current result:

```text
total_evaluated = 400
execution_accuracy = 102/394 = 0.2589
valid_sql_rate = 295/394 = 0.7487
failures = 298
trace_contract.validated = true
```

Diagnostic note:

```text
results/benchmark/20260621_104339_agent_positive400_qwen2-5-coder-7b_paper1_main_local_no_templates
```

This partial full attempt was stopped after `9/400` cases because the legacy command used the global retry setting (`max_retries=5`) and entered long repair/reflexion loops on failing cases. It is a diagnostic artifact only, not a paper result.

## Retrieval R0-R3 Full Dev

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_ablation.py `
  experiments\configs\R0_retrieval_bm25_dev_full.yaml `
  experiments\configs\R1_retrieval_vector_dev_full.yaml `
  experiments\configs\R2_retrieval_hybrid_dev_full.yaml `
  experiments\configs\R3_retrieval_hybrid_rerank_dev_full.yaml `
  --output-dir results\ablation\paper1_retrieval_final_dev_full `
  --execute
```

Current manifest:

```text
results/ablation/paper1_retrieval_final_dev_full/ablation_manifest.json
```

## Behavioral Dev Full

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --mode agent `
  --dataset behavior_dev `
  --sample 0 `
  --top-k 5 `
  --exclude-self `
  --bootstrap-iterations 1000 `
  --trace-level compact `
  --ablation-id paper1_behavior_dev_full
```

Current artifact:

```text
results/benchmark/20260621_205133_agent_behavior_dev_qwen2_5-coder-7b-instruct-q4_k_m_paper1_behavior_dev_full
```

## A0-A4/A7 Ablation Smoke

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_ablation.py `
  experiments\configs\A0_direct_schema_only.yaml `
  experiments\configs\A1_persian_nlu.yaml `
  experiments\configs\A2_schema_linking.yaml `
  experiments\configs\A3_value_linking.yaml `
  experiments\configs\A4_cag_examples.yaml `
  experiments\configs\A7_full_phase10_system.yaml `
  --output-dir results\ablation\paper1_A0_A4_A7_dev `
  --execute
```

Analyze:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_ablation_manifest.py `
  results\ablation\paper1_A0_A4_A7_dev\ablation_manifest.json `
  --output-dir results\ablation\paper1_A0_A4_A7_dev
```

Current report:

```text
results/ablation/paper1_A0_A4_A7_dev/ablation_comparison.md
```

## A0-A4/A7 Full-Dev Bounded Ablation

Dry-run manifest already validated:

```text
results/ablation/paper1_A0_A4_A7_dev_full_bounded_dryrun/ablation_manifest.json
```

Run the paper-grade full-dev ablation:

```powershell
.\.venv\Scripts\python.exe scripts\run_ablation.py `
  experiments\configs\A0_direct_schema_only_dev_full_bounded.yaml `
  experiments\configs\A1_persian_nlu_dev_full_bounded.yaml `
  experiments\configs\A2_schema_linking_dev_full_bounded.yaml `
  experiments\configs\A3_value_linking_dev_full_bounded.yaml `
  experiments\configs\A4_cag_examples_dev_full_bounded.yaml `
  experiments\configs\A7_full_phase10_system_dev_full_bounded.yaml `
  --output-dir results\ablation\paper1_A0_A4_A7_dev_full_bounded `
  --execute
```

Analyze after completion:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_ablation_manifest.py `
  results\ablation\paper1_A0_A4_A7_dev_full_bounded\ablation_manifest.json `
  --output-dir results\ablation\paper1_A0_A4_A7_dev_full_bounded
```

Notes:

```text
dataset = dev
cases_per_config = 60
max_retries = 1
trace_level = compact
deterministic_templates = false
```

Current executed manifest:

```text
results/ablation/paper1_A0_A4_A7_dev_full_bounded/ablation_manifest.json
```

Current analysis:

```text
results/ablation/paper1_A0_A4_A7_dev_full_bounded/ablation_comparison.md
results/ablation/paper1_A0_A4_A7_dev_full_bounded/ablation_comparison.json
```

Current result:

```text
jobs_completed = 6/6
same_dataset_hash = true
same_selected_cases_hash = true
cases_per_config = 60
A0 EX = 4/58 = 0.0690, valid_sql = 40/58 = 0.6897
A1 EX = 4/58 = 0.0690, valid_sql = 38/58 = 0.6552
A2 EX = 4/58 = 0.0690, valid_sql = 40/58 = 0.6897
A3 EX = 4/58 = 0.0690, valid_sql = 39/58 = 0.6724
A4 EX = 15/58 = 0.2586, valid_sql = 42/58 = 0.7241
A7 EX = 17/58 = 0.2931, valid_sql = 40/58 = 0.6897
unsafe_sql = 0 for all configs
```

## A0-A4/A7 Full Positive400 Bounded Ablation

Run split jobs:

```powershell
.\.venv\Scripts\python.exe scripts\run_ablation.py experiments\configs\A0_direct_schema_only_positive400_bounded.yaml --output-dir results\ablation\paper1_A0_A4_A7_positive400_split\A0 --execute
.\.venv\Scripts\python.exe scripts\run_ablation.py experiments\configs\A1_persian_nlu_positive400_bounded.yaml --output-dir results\ablation\paper1_A0_A4_A7_positive400_split\A1 --execute
.\.venv\Scripts\python.exe scripts\run_ablation.py experiments\configs\A2_schema_linking_positive400_bounded.yaml --output-dir results\ablation\paper1_A0_A4_A7_positive400_split\A2 --execute
.\.venv\Scripts\python.exe scripts\run_ablation.py experiments\configs\A3_value_linking_positive400_bounded.yaml --output-dir results\ablation\paper1_A0_A4_A7_positive400_split\A3 --execute
.\.venv\Scripts\python.exe scripts\run_ablation.py experiments\configs\A4_cag_examples_positive400_bounded.yaml --output-dir results\ablation\paper1_A0_A4_A7_positive400_split\A4 --execute
.\.venv\Scripts\python.exe scripts\run_ablation.py experiments\configs\A7_full_phase10_system_positive400_bounded.yaml --output-dir results\ablation\paper1_A0_A4_A7_positive400_split\A7 --execute
```

Merge and analyze:

```powershell
.\.venv\Scripts\python.exe scripts\merge_ablation_manifests.py `
  results\ablation\paper1_A0_A4_A7_positive400_split\A0\ablation_manifest.json `
  results\ablation\paper1_A0_A4_A7_positive400_split\A1\ablation_manifest.json `
  results\ablation\paper1_A0_A4_A7_positive400_split\A2\ablation_manifest.json `
  results\ablation\paper1_A0_A4_A7_positive400_split\A3\ablation_manifest.json `
  results\ablation\paper1_A0_A4_A7_positive400_split\A4\ablation_manifest.json `
  results\ablation\paper1_A0_A4_A7_positive400_split\A7\ablation_manifest.json `
  --output-dir results\ablation\paper1_A0_A4_A7_positive400_split\merged

.\.venv\Scripts\python.exe scripts\analyze_ablation_manifest.py `
  results\ablation\paper1_A0_A4_A7_positive400_split\merged\ablation_manifest.json `
  --output-dir results\ablation\paper1_A0_A4_A7_positive400_split\merged
```

Current artifacts:

```text
results/ablation/paper1_A0_A4_A7_positive400_split/merged/ablation_manifest.json
results/ablation/paper1_A0_A4_A7_positive400_split/merged/ablation_comparison.md
results/ablation/paper1_A0_A4_A7_positive400_split/merged/ablation_comparison.json
```

Current result:

```text
jobs_completed = 6/6
same_dataset_hash = true
same_selected_cases_hash = true
cases_per_config = 400
A0 EX = 41/394 = 0.1041, valid_sql = 269/394 = 0.6827
A1 EX = 42/394 = 0.1066, valid_sql = 269/394 = 0.6827
A2 EX = 42/394 = 0.1066, valid_sql = 264/394 = 0.6701
A3 EX = 41/394 = 0.1041, valid_sql = 266/394 = 0.6751
A4 EX = 101/394 = 0.2563, valid_sql = 274/394 = 0.6954
A7 EX = 101/394 = 0.2563, valid_sql = 276/394 = 0.7005
unsafe_sql = 0 for all configs
```

## Main Error Analysis

Run:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_benchmark_artifact.py `
  results\benchmark\20260621_122748_paper1_main_local_no_templates_bounded `
  --output-dir results\error_analysis\paper1_main_local_bounded
```

Current report:

```text
results/error_analysis/paper1_main_local_bounded/error_report.md
```

## Semantic Judge Attempt

Run:

```powershell
$env:OPENROUTER_API_KEY="<key>"
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\20260621_122748_paper1_main_local_no_templates_bounded `
  --judge-provider openrouter `
  --judge-model qwen/qwen3.6-plus `
  --judge-policy semantic `
  --judge-sample-size 50 `
  --all-predictions `
  --output-dir results\judgments\paper1_main_semantic_openrouter
```

Current artifact:

```text
results/judgments/paper1_main_semantic_openrouter
```

Current status:

```text
provider_error = 50/50
reason = HTTP 402 Payment Required
authoritative = false
```

Mock sanity run, successful but non-authoritative:

```powershell
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\20260621_122748_paper1_main_local_no_templates_bounded `
  --judge-provider mock `
  --judge-policy semantic `
  --judge-sample-size 50 `
  --all-predictions `
  --output-dir results\judgments\paper1_main_semantic_mock_s50
```

Current mock artifact:

```text
results/judgments/paper1_main_semantic_mock_s50
```

Before rerunning a paid OpenRouter judge, probe with 3 cases after adding credits or selecting an available model:

```powershell
$env:OPENROUTER_API_KEY="<key>"
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\20260621_122748_paper1_main_local_no_templates_bounded `
  --judge-provider openrouter `
  --judge-model qwen/qwen3.6-plus `
  --judge-policy semantic `
  --case-ids VTD-001 VTD-002 VTD-003 `
  --all-predictions `
  --output-dir results\judgments\paper1_main_semantic_openrouter_s3_probe
```

Current probe artifact:

```text
results/judgments/paper1_main_semantic_openrouter_s3_probe
```

Current probe result:

```text
total_judged = 3
authoritative = true
authoritative_judgments = 3
business_correct = 2
business_incorrect = 1
redaction_applied = true
```

If the probe has `provider_error=0`, run the 50-case judge:

```powershell
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\20260621_122748_paper1_main_local_no_templates_bounded `
  --judge-provider openrouter `
  --judge-model qwen/qwen3.6-plus `
  --judge-policy semantic `
  --judge-sample-size 50 `
  --all-predictions `
  --output-dir results\judgments\paper1_main_semantic_openrouter_s50_rerun
```

Current 50-case artifact:

```text
results/judgments/paper1_main_semantic_openrouter_s50_rerun
```

Current 50-case result:

```text
total_judged = 50
authoritative = true
authoritative_judgments = 50
semantic_business_correct = 39/50 = 0.78
semantic_business_incorrect = 11/50 = 0.22
provider_error = 0
provider_parse_error = 0
redaction_applied = true
input_tokens = 36142
output_tokens = 64304
estimated_cost_usd = 0.0
```

Full 400-case split judge run:

```powershell
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\20260621_122748_paper1_main_local_no_templates_bounded `
  --judge-provider openrouter `
  --judge-model qwen/qwen3.6-plus `
  --judge-policy semantic `
  --case-ids VTD-001 VTD-002 ... VTD-050 `
  --all-predictions `
  --output-dir results\judgments\paper1_main_semantic_openrouter_s400_split\part01_001_050
```

Repeat the same command for `part02_051_100` through `part08_351_400`.

Provider-error retry that was needed in the completed run:

```powershell
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\20260621_122748_paper1_main_local_no_templates_bounded `
  --judge-provider openrouter `
  --judge-model qwen/qwen3.6-plus `
  --judge-policy semantic `
  --case-ids VTD-089 VTD-090 VTD-091 VTD-166 `
  --all-predictions `
  --output-dir results\judgments\paper1_main_semantic_openrouter_s400_split\retry_provider_errors_089_090_091_166
```

Final merge:

```powershell
.\.venv\Scripts\python.exe scripts\merge_judge_artifacts.py `
  results\judgments\paper1_main_semantic_openrouter_s400_split\part01_001_050 `
  results\judgments\paper1_main_semantic_openrouter_s400_split\part02_051_100 `
  results\judgments\paper1_main_semantic_openrouter_s400_split\part03_101_150 `
  results\judgments\paper1_main_semantic_openrouter_s400_split\part04_151_200 `
  results\judgments\paper1_main_semantic_openrouter_s400_split\part05_201_250 `
  results\judgments\paper1_main_semantic_openrouter_s400_split\part06_251_300 `
  results\judgments\paper1_main_semantic_openrouter_s400_split\part07_301_350 `
  results\judgments\paper1_main_semantic_openrouter_s400_split\part08_351_400 `
  results\judgments\paper1_main_semantic_openrouter_s400_split\retry_provider_errors_089_090_091_166 `
  --duplicate-policy keep-last `
  --output-dir results\judgments\paper1_main_semantic_openrouter_s400_split\merged_authoritative
```

Current full 400-case artifact:

```text
results/judgments/paper1_main_semantic_openrouter_s400_split/merged_authoritative
```

Current full 400-case result:

```text
total_judged = 400
authoritative = true
authoritative_judgments = 400
semantic_business_correct = 161/400 = 0.4025
semantic_business_incorrect = 239/400 = 0.5975
provider_error = 0
provider_parse_error = 0
redaction_applied = true
input_tokens = 347343
output_tokens = 731993
estimated_cost_usd = 0.0
```

## Pending Reproducibility Items

- Optional clean paraphrase holdout for stronger anti-overfit claims.
- Optional human spot-check of a sample of the 400 OpenRouter semantic/business judgments before final paper submission.
