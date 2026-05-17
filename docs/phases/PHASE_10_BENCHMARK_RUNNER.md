# Phase 10 - Benchmark Runner and Trace Contract

**Status:** Completed for benchmark/trace infrastructure - quality, ablation and semantic judging continue in later phases  
**Updated:** 2026-05-17  
**Scope:** Reproducible terminal benchmark runs, balanced sampling, transparent logs, full prompt/response trace, model/ablation metadata, paper-ready artifacts, and the handoff point for semantic/business evaluation.

## Goal

Phase 10 turns the project from a demoable agent into a measurable research system. Every run must answer:

- Which dataset, model, config and ablation were used?
- Which modules were enabled or disabled?
- Which questions were selected and why?
- What exact prompt was sent to the model?
- What exact raw response came back from the model?
- Which SQL was parsed, validated, repaired and executed?
- Did the SQL execute correctly against gold SQL?
- Did the system choose the correct action for behavioral examples?
- What failed, why, and how can the case be replayed?

Phase 10 does not claim that a SQL is semantically/business-correct. It prepares the trace and artifact contract required for Phase 16 to judge that separately.

## Implemented Files

| File | Current role |
|---|---|
| `scripts/run_benchmark.py` | CLI entry point for `retrieval`, `gold`, and initial `agent` benchmark runs |
| `src/evaluation/dataset_loader.py` | Dataset loading and normalization |
| `src/evaluation/metrics.py` | EX, valid SQL, abstention and robustness metrics |
| `src/evaluation/reliability_metrics.py` | Reliability Score |
| `src/evaluation/report_generator.py` | Markdown benchmark summaries |
| `src/evaluation/retrieval_metrics.py` | Retrieval metric summary |
| `src/evaluation/error_analyzer.py` | Basic error grouping |
| `src/evaluation/export_utils.py` | CSV and paper table exports |
| `src/graph/state.py` | `VTDState` and `SQLAttempt` trace state |
| `src/graph/nodes/base_nodes.py` | Current graph node implementation and prompt/generation flow |

Implemented in current Phase 10 pass:

- `--samples-per-level`
- per-case progress logging
- prompt/raw-response fields in `SQLAttempt`
- prefixed artifact names with model slug and ablation id
- bootstrap CI for core metrics
- latency summary
- model/module metadata in config and summary
- `dataset_hash`, `selected_cases_hash` and selected `difficulty_counts`
- explicit `retrieval_backend`, `max_retries`, `prompt_template` and `trace_level`
- `--exclude-self` retrieval self-overlap mitigation for benchmark runs

## Required CLI Contract

All benchmark modes must be runnable by the developer from PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 20 --top-k 3
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset dev --sample 20
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --sample 20
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 5
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset test --samples-per-level 5 --config benchmark/configs/research_agent_v1.yaml
```

Supported dataset aliases:

- `dev`
- `test`
- `positive400`
- `behavior_dev`
- `behavior_test`
- `phase0`

Use `--path <dataset.json>` for a custom dataset.

For the practical day-to-day guide, use `docs/BENCHMARK_AND_TEST_GUIDE.md`. This phase document defines the contract; the guide shows the commands and debugging workflow.

## Local Model Smoke Gate

Latest status: passed on 2026-05-15 with `qwen2.5-coder-3b-instruct-q4_k_m.gguf`. The run produced valid JSON, parsed SQL, no validation errors, retry count `0`, and attempt count `1`.

Before running `--mode agent` benchmarks, validate the local model path and single-question agent flow:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\Qwen__Qwen2.5-Coder-3B-Instruct-GGUF\qwen2.5-coder-3b-instruct-q4_k_m.gguf"
.\.venv\Scripts\python.exe scripts\run_agent.py "درصد دانشجویان افسرده چقدر است؟" --verbose
```

This gate is not an accuracy claim. It only proves that the configured GGUF model, prompt builder, parser, validation path and graph wiring can run together. The smoke result must be copied into `task.md` with:

- model path and model slug;
- pass/fail status;
- generated SQL or controlled failure class;
- raw model response and parsed payload when `--verbose` is used;
- validation errors or explicit note that no validation failure was visible;
- whether parsing and validation were reached;
- command timestamp.

## Real Agent Balanced Smoke Gate

After the local model smoke, the first real benchmark must be small but balanced:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\Qwen__Qwen2.5-Coder-3B-Instruct-GGUF\qwen2.5-coder-3b-instruct-q4_k_m.gguf"
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --ablation-id full_trace
```

This gate checks the real artifact contract, not final quality. It must produce the full artifact set and preserve prompt/raw-response traces for each attempt. If the model makes bad SQL, keep the artifact and categorize the failure; do not hide it by changing the dataset or prompt before recording the result.

Latest result on 2026-05-15:

```text
output_dir: results/benchmark/20260515_095324_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace
selected_cases: 4
attempts: 8
missing_prompt/raw/parsed_payload: 0/0/0
execution_accuracy: 0.25
valid_sql_rate: 0.50
reliability_score: -0.5
unsafe_sql: 0
```

Pre-fix finding from the same gate: the first balanced smoke reached all four selected cases and printed progress, but artifact writing failed because `LinkedSchema` was not JSON serializable. The artifact writer now normalizes Pydantic models, dataclasses and paths before writing JSON/JSONL.

## Sampling Rules

| Flag | Meaning |
|---|---|
| `--sample N` | Evaluate N cases in deterministic dataset order |
| `--samples-per-level N` | Evaluate N cases per `difficulty` level |
| `--seed N` | Optional future flag for deterministic shuffled selection |

Rules:

1. `--sample` and `--samples-per-level` must not silently conflict.
2. Selection policy must be stored in `config.json`.
3. `summary.json` must include `difficulty_counts` for selected cases.
4. Missing difficulty labels should be grouped under `unknown` unless strict mode is enabled later.

## Terminal Progress Logging

Long local model runs must be observable. For every case, print:

```text
[3/20] id=VTD-237 difficulty=complex category=global_change_dashboard action=generate_sql status=fail latency=18342ms elapsed=00:01:02 eta=00:05:41
```

Required fields:

- current/total
- case id
- difficulty
- category
- expected action
- actual action
- ok/fail
- per-case latency
- total elapsed time
- ETA

The final terminal line must print the artifact folder path and high-level metrics.

Minimum final terminal summary:

- evaluated count
- failure count
- execution accuracy
- valid SQL rate
- reliability score if available
- unsafe SQL count if available
- latency mean/median/p95
- artifact folder path

## Modes

### `retrieval`

Measures evidence retrieval quality before full SQL generation. It reports retrieval hit rate and schema/intent/skeleton overlap. It is not an end-to-end SQL benchmark.

### `gold`

Runs a non-LLM sanity benchmark. It compares gold SQL against itself to validate executor, result hashing, summary generation and artifact writing.

### `agent`

Runs the LangGraph workflow end to end. It must record every prompt, raw model response, parsed SQL, validation issue, execution result hash, repair attempt and final action.

SQL-positive examples are scored with EX/Valid SQL/latency. Behavioral examples are scored with expected action and reliability, not EX.

## Full Trace Contract

`predictions.jsonl` must contain one row per benchmark case:

```json
{
  "id": "VTD-001",
  "question": "...",
  "normalized_question": "...",
  "difficulty": "easy",
  "category": "count",
  "expected_action": "generate_sql",
  "actual_action": "format_answer",
  "model_slug": "qwen25coder3b",
  "ablation_id": "A7_full",
  "enabled_modules": ["nlu", "schema_linking", "value_linking", "cag", "validation"],
  "disabled_modules": ["reflexion"],
  "qir": {},
  "linked_schema": {},
  "retrieved_examples": [],
  "retrieval_diagnostics": [],
  "generated_sql": "SELECT ...",
  "gold_sql": "SELECT ...",
  "valid_sql": true,
  "execution_correct": false,
  "semantic_business_correct": null,
  "result_hash": "...",
  "gold_result_hash": "...",
  "latency_ms": 1234,
  "error": "SEMANTIC_METRIC_ERROR"
}
```

`attempts.jsonl` must contain one row per generation/repair attempt:

```json
{
  "case_id": "VTD-001",
  "attempt_index": 0,
  "iteration": 0,
  "prompt": "... exact prompt sent to model ...",
  "raw_model_response": "... exact model output ...",
  "parsed_payload": {},
  "sql": "SELECT ...",
  "validation_passed": true,
  "execution_passed": true,
  "validation_errors": [],
  "execution_result_hash": "...",
  "critic_feedback": null,
  "repair_plan": null,
  "latency_ms": 1234
}
```

Prompt/response traces are required because they distinguish:

- model misunderstanding
- prompt/context bug
- parser bug
- SQL validation bug
- SQL execution mismatch
- business/semantic mismatch

## Artifact Layout

Every run must write:

```text
results/benchmark/<timestamp>_<mode>_<dataset>_<model_slug>_<ablation_id>/
  <prefix>_config.json
  <prefix>_predictions.jsonl
  <prefix>_attempts.jsonl
  <prefix>_failures.jsonl
  <prefix>_summary.json
  <prefix>_summary.md
  <prefix>_benchmark_results.csv
  <prefix>_reliability_summary.csv
  <prefix>_error_taxonomy.csv
  <prefix>_paper_tables.md
```

For long-running agent benchmarks, partial artifacts must be refreshed after every case:

```text
  <prefix>_partial_predictions.jsonl
  <prefix>_partial_failures.jsonl
  <prefix>_partial_attempts.jsonl
```

Partial artifacts are interruption/debug artifacts. Final paper metrics must still come from completed runs and final summary files.

When `--use-judge` is enabled in Phase 16:

```text
  <prefix>_judgments.jsonl
  <prefix>_judge_reasoning.md
  <prefix>_judge_costs.json
  <prefix>_semantic_business_summary.csv
```

## Config Metadata

`config.json`, `summary.json`, `summary.md` and `paper_tables.md` must include:

- `model_name`
- `model_slug`
- `model_path`
- `config_id`
- `ablation_id`
- `enabled_modules`
- `disabled_modules`
- `dataset`
- `dataset_path`
- `selection_policy`
- `sample` or `samples_per_level`
- `top_k`
- `retrieval_backend`
- `max_retries`
- `prompt_template`
- `trace_level`
- `dataset_hash`
- selected `difficulty_counts`
- retrieval self-overlap policy
- `git_commit`

## Leakage Mitigation Contract

For benchmark runs over dev/test/behavior splits, retrieved examples must not include the evaluated case itself. The runner and graph must be able to exclude retrieval records by:

- exact/base id match, including `fs_` and `idx_` prefixes;
- exact normalized question match.

Every run must store whether self-overlap exclusion was enabled and how many retrieved examples were removed. This mitigates direct leakage in RAG/CAG context but does not prove there is no broader dataset or prompt overfit.

Implementation status:

- `scripts/run_benchmark.py --exclude-self` filters retrieval-mode examples and forwards the same policy into agent graph state.
- `src/graph/nodes/base_nodes.py` applies the policy before building CAG context.
- `src/retrieval/self_overlap.py` centralizes base-id and normalized-question matching.
- `config.json` stores `retrieval_self_overlap_policy`.
- `predictions.jsonl` stores `exclude_self_retrieval`, `self_overlap_removed` and `self_overlap_removed_ids`.

Manual verification required:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier2_integration\test_agent_benchmark_trace.py -vv --tb=short
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 5 --top-k 3 --exclude-self --ablation-id manual_exclude_self_smoke
```

Latest verification on 2026-05-16:

```text
pytest: tests/tier2_integration/test_agent_benchmark_trace.py -> 4 passed, 1 warning
retrieval_output_dir: results/benchmark/20260516_075846_retrieval_dev_qwen2-5-coder-7b_manual_exclude_self_smoke
retrieval evaluated/failures: 5/0
retrieval_hit_rate: 1.0
latency mean/median/p95: 2.4/1.0/8.0 ms
config fields verified: dataset_hash, selected_cases_hash, retrieval_self_overlap_policy
self_overlap_removed_total: 0
```

Agent smoke verification on 2026-05-16:

```text
agent_output_dir: results/benchmark/20260516_080120_agent_dev_qwen2-5-coder-7b_manual_agent_exclude_self_spl1
evaluated/failures: 4/3
execution_accuracy: 0.25
valid_sql_rate: 0.75
reliability_score: -1.25
unsafe_sql: 0
error_taxonomy: RESULT_MISMATCH=2, MISSING_GENERATED_SQL=1
self_overlap_removed_total: 1
```

Post-run metadata fix: when `VTD_DEFAULT_MODEL_PATH` is not set, `scripts/run_benchmark.py` now records the fallback GGUF path in `config.model_path` instead of leaving it empty.

Metadata fix verification:

```text
gold_output_dir: results/benchmark/20260516_081002_gold_dev_qwen2-5-coder-7b_metadata_model_path_fix_smoke
model_name: qwen2.5-coder-7b-instruct-q4_k_m
model_path: D:\Project\ADHD-VTD\models\generation\qwen2.5-coder-7b-instruct-q4_k_m.gguf
execution_accuracy: 1.0
valid_sql_rate: 1.0
```

Ambiguity fix verification:

```text
tests:
  tests/tier1_unit/test_ambiguity_detector.py -> 16 passed
  tests/tier1_unit/test_intent_classifier.py -> 1 passed
  tests/tier1_unit/test_graph_routes.py + tests/tier2_integration/test_agent_benchmark_trace.py -> 6 passed, 1 warning
agent_output_dir: results/benchmark/20260516_081645_agent_dev_qwen2-5-coder-7b_manual_agent_after_ambiguity_fix_spl1
evaluated/failures: 4/3
execution_accuracy: 0.25
valid_sql_rate: 1.0
reliability_score: -2.0
unsafe_sql: 0
error_taxonomy: RESULT_MISMATCH=3
```

Interpretation: the benchmark runner now reaches generation for all selected SQL-positive cases in this smoke; the remaining Phase 10 quality bottleneck is result mismatch, especially dashboard/storytelling prompts where the intent/QIR under-specifies the required analytical shape.

Dashboard/storytelling intent follow-up:

```text
implemented: src/nlu/intent_classifier.py maps dashboard/storytelling SQL-capable requests to grouping_query instead of non_sql_request.
test_updated: tests/tier1_unit/test_intent_classifier.py asserts a VTD-237-style dashboard/eating_disorder request generates SQL and routes as grouping_query.
verification_pending:
  python -m pytest tests\tier1_unit\test_intent_classifier.py -vv --tb=short
  python -m pytest tests\tier1_unit\test_ambiguity_detector.py -vv --tb=short
  python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_dashboard_intent_fix_spl1
expected_trace_change: VTD-237 intent should no longer be non_sql_request; if it still fails, the failure should be inspected as RESULT_MISMATCH/prompt-QIR quality, not routing/abstention.
```

Dashboard/storytelling intent verification:

```text
tests:
  tests/tier1_unit/test_intent_classifier.py -> 1 passed
  tests/tier1_unit/test_ambiguity_detector.py -> 16 passed
  tests/tier1_unit/test_graph_routes.py + tests/tier2_integration/test_agent_benchmark_trace.py -> 6 passed, 1 warning
agent_output_dir: results/benchmark/20260516_120437_agent_dev_qwen2-5-coder-7b_manual_agent_after_dashboard_intent_fix_spl1
evaluated/failures: 4/3
execution_accuracy: 0.25
valid_sql_rate: 1.0
reliability_score: -2.0
unsafe_sql: 0
error_taxonomy: RESULT_MISMATCH=3
VTD-237: intent=grouping_query, valid_sql=True, execution_correct=False
```

Interpretation: routing is fixed. The remaining failures in this smoke are valid-SQL result-shape mismatches. The next Phase 10 work item is prompt/QIR guidance for analytical result shape, without leaking gold SQL or benchmark-only answers into runtime.

Result-shape hint implementation:

```text
implemented:
  src/generation/prompt_builder.py derives runtime-safe analysis_hints from question text, intent and schema tables.
  src/generation/prompts/sql_generation.j2 prints Analysis Shape Guidance before examples.
  tests/tier1_unit/test_prompt_builder.py covers grouped rate, dashboard/change/quartile and risk-above-average hints.
guardrail:
  hints must not include gold SQL or benchmark-only expected answers.
verification_pending:
  python -m pytest tests\tier1_unit\test_prompt_builder.py -vv --tb=short
  python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_shape_hints_spl1
```

Result-shape hint verification:

```text
tests:
  tests/tier1_unit/test_prompt_builder.py -> 3 passed
  tests/tier1_unit/test_prompt_builder.py + tests/tier1_unit/test_intent_classifier.py + tests/tier1_unit/test_ambiguity_detector.py -> 20 passed
agent_output_dir: results/benchmark/20260516_122431_agent_dev_qwen2-5-coder-7b_manual_agent_after_shape_hints_spl1
evaluated/failures: 4/4
execution_accuracy: 0.0
valid_sql_rate: 0.5
reliability_score: -2.5
unsafe_sql: 0
error_taxonomy: INVALID_SQL=2, RESULT_MISMATCH=2
```

Interpretation: the first shape hints were visible in the prompt but too broad. They improved the target shape for `VTD-300`, but caused schema mixing for `VTD-237` (`country_prevalence_wide` with long-table columns) and exposed few-shot column copying for `VTD-027` (`family_history` copied where only `family_history_mental_illness` exists). The next refinement must add schema-fidelity guardrails and table-specific prevalence guidance.

Refined result-shape hint implementation:

```text
implemented:
  no-cross-table-column-copy guardrail for few-shot examples.
  explicit country_prevalence_long vs country_prevalence_wide column guidance.
  risk-summary guidance requiring GROUP BY mental_health_risk, COUNT(*) AS n, avg_stress and avg_sleep where supported.
  rate guidance requiring positives/rate_pct; gold-only context columns must not be enforced unless requested.
  family-history guidance mapping student_depression questions to family_history_mental_illness.
verification_pending:
  python -m pytest tests\tier1_unit\test_prompt_builder.py -vv --tb=short
  python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_refined_shape_hints_spl1
```

Refined result-shape hint verification:

```text
tests:
  tests/tier1_unit/test_prompt_builder.py -> 4 passed
  tests/tier1_unit/test_prompt_builder.py + tests/tier1_unit/test_intent_classifier.py + tests/tier1_unit/test_ambiguity_detector.py -> 21 passed
agent_output_dir: results/benchmark/20260517_010715_agent_dev_qwen2-5-coder-7b_manual_agent_after_refined_shape_hints_spl1
evaluated/failures: 4/3
execution_accuracy: 0.25
valid_sql_rate: 0.75
reliability_score: -1.25
unsafe_sql: 0
```

Interpretation: the refinement fixed `VTD-027` by selecting `student_depression.family_history_mental_illness`. Remaining issues are narrower: `VTD-237` used SQLite-unsupported `PERCENTILE_CONT` and still preferred a wide-table percentile path; `VTD-343` ignored grouped risk-summary shape; `VTD-300` is close to the natural-language rate request but exact-gold differs on an extra context column. The next patch must ensure schema-specific hints appear for live dict-style schema entries and must explicitly prohibit unsupported SQLite percentile functions.

Refined result-shape hint v2 implementation:

```text
implemented:
  schema column reader supports object-style entries, dict column lists and dict column maps.
  prompt explicitly forbids SQLite-unsupported PERCENTILE_CONT/WITHIN GROUP.
  named-disorder change/quartile guidance says MUST use country_prevalence_long.
  student_depression rate guidance requires sleep_duration_category AS group_value, null filtering and depression_flag positives/rate_pct; gold-only context columns are not enforced.
verification_pending:
  python -m pytest tests\tier1_unit\test_prompt_builder.py -vv --tb=short
  python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_refined_shape_hints_v2_spl1
```

Refined result-shape hint v2 verification:

```text
tests:
  tests/tier1_unit/test_prompt_builder.py -> 5 passed
  tests/tier1_unit/test_prompt_builder.py + tests/tier1_unit/test_intent_classifier.py + tests/tier1_unit/test_ambiguity_detector.py -> 22 passed
agent_output_dir: results/benchmark/20260517_013053_agent_dev_qwen2-5-coder-7b_manual_agent_after_refined_shape_hints_v2_spl1
evaluated/failures: 4/3
execution_accuracy: 0.25
valid_sql_rate: 1.0
reliability_score: -2.0
unsafe_sql: 0
```

Interpretation: v2 restored full valid-SQL rate and kept `VTD-027` exact-correct. Remaining errors are not syntax/schema failures: `VTD-237` is a valid but under-shaped latest-year scalar; `VTD-343` is a valid but under-shaped row-level risk list; `VTD-300` is close to the natural-language request but exact-gold mismatch remains because gold includes `avg_cgpa_10`, which is not explicit in the question. To avoid overfitting, do not force gold-only extra columns in prompt or validators. The next step is a runtime shape validator for defensible SQL dialect and question/schema-derived shape contracts.

Shape contract validator implementation:

```text
implemented:
  src/sql_validation/shape_validator.py validates SQLite dialect and question/schema-derived analytical shape without reading gold SQL.
  src/graph/nodes/base_nodes.py runs shape validation after syntax/schema validation and before execution.
  tests/tier1_unit/test_shape_validator.py covers unsupported percentile functions, global change dashboards, grouped risk summaries and grouped sleep-rate shape.
anti_overfit_guardrail:
  avg_cgpa_10 is not enforced for VTD-300 because it is not explicit in the user question.
verification_pending:
  python -m pytest tests\tier1_unit\test_prompt_builder.py tests\tier1_unit\test_shape_validator.py -vv --tb=short
  python -m pytest tests\tier1_unit\test_graph_retry_and_config.py tests\tier1_unit\test_graph_attempt_trace.py -vv --tb=short
  python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_shape_contract_spl1
```

Shape contract validator verification:

```text
tests:
  tests/tier1_unit/test_prompt_builder.py + tests/tier1_unit/test_shape_validator.py -> 10 passed
  tests/tier1_unit/test_graph_retry_and_config.py + tests/tier1_unit/test_graph_attempt_trace.py -> 8 passed
agent_output_dir: results/benchmark/20260517_015651_agent_dev_qwen2-5-coder-7b_manual_agent_after_shape_contract_spl1
evaluated/failures: 4/3
execution_accuracy: 0.25
valid_sql_rate: 0.75
reliability_score: -1.25
unsafe_sql: 0
```

Interpretation: the validator correctly blocks under-shaped SQL before execution. `VTD-237` is rejected with analytical-shape errors until it computes change and binning over `country_prevalence_long`. `VTD-343` is forced away from row-level risk output, but the repaired SQL still misses above/below-average filters. `VTD-300` passes the defensible shape contract and should be treated as an exact-EX mismatch pending semantic/business review rather than forced to include gold-only `avg_cgpa_10`.

Closeout analysis:

```text
report: results/error_analysis/20260517_phase10_shape_contract/error_report.md
decision: exact execution correctness and semantic/business correctness remain separate.
anti_overfit_decision: do not force gold-only avg_cgpa_10 for VTD-300-style rate questions.
follow_up_fix: risk stress/sleep average-threshold questions now require the requested average filters before grouping.
new_issue_code: ANALYTICAL_SHAPE_MISSING_RISK_AVERAGE_FILTERS
verification: test_shape_validator.py + test_prompt_builder.py -> 12 passed
remaining_gate: run and inspect --samples-per-level 2 local-agent smoke before marking Phase 10 done.
```

Larger shape-contract smoke verification:

```text
run: python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 2 --bootstrap-iterations 200 --exclude-self --trace-level full --ablation-id manual_agent_shape_contract_spl2
output_dir: results/benchmark/20260517_030238_agent_dev_qwen2-5-coder-7b_manual_agent_shape_contract_spl2
evaluated: 8
difficulty_counts: complex=2, easy=2, hard=2, medium=2
failures: 6
execution_accuracy: 0.25
valid_sql_rate: 0.75
reliability_score: -2.5
unsafe_sql: 0
self_overlap_removed_total: 1
artifact_contract: completed run with final artifact path
```

Findings that must be fixed before marking Phase 10 complete:

- `VTD-371` is a safe analytical matrix/dashboard request, but the safety detector routed it as `unsafe_query` because it treats the Persian verb "build/create" too broadly.
- `VTD-078` is a general grouped risk-profile average query, but the risk shape validator over-applies stress/sleep summary requirements. Stress/sleep averages and average-threshold filters should be required only when the question explicitly asks about stress/sleep threshold populations.

Follow-up fixes after the larger smoke:

```text
fixed:
  VTD-371-style analytical "build matrix/dashboard" requests are no longer unsafe unless the request is about creating/changing database objects.
  VTD-078-style general risk-profile average queries no longer require stress/sleep averages unless the question explicitly asks for stress/sleep threshold populations.
verification:
  test_safety_detector.py + test_intent_classifier.py + test_shape_validator.py + test_prompt_builder.py -> 34 passed
rerun_after_fixes:
  output_dir: results/benchmark/20260517_031221_agent_dev_qwen2-5-coder-7b_manual_agent_shape_contract_spl2_after_fixes
  evaluated: 8
  difficulty_counts: complex=2, easy=2, hard=2, medium=2
  failures: 6
  execution_accuracy: 0.25
  valid_sql_rate: 0.875
  reliability_score: -3.25
  unsafe_sql: 0
  self_overlap_removed_total: 1
regression_checks:
  VTD-371 is no longer unsafe_query; it reaches generation and fails only as RESULT_MISMATCH.
  VTD-078 is no longer invalidated by over-broad shape validation; it is valid SQL and fails only as RESULT_MISMATCH.
status:
  Phase 10 benchmark/trace infrastructure is complete.
  Remaining low EX and reliability are Phase 11/13/16 work, not Phase 10 infrastructure blockers.
```

## Metrics

Static metrics:

- EX on SQL-positive examples only
- Valid SQL Rate
- EX@first_attempt
- EX@final_attempt
- Retry Success Rate
- Correct Action Rate for behavioral examples
- Correct Abstention Rate
- False Abstention Rate
- Unsafe Pass-through Rate, target `0`
- Reliability Score
- Latency mean/median/p95/min/max

Statistical reporting:

- Bootstrap 95% CI for EX, Valid SQL Rate, Reliability Score, Correct Abstention Rate and Unsafe Pass-through Rate.
- Later Phase 11 adds paired significance tests across ablations.

Semantic/business metrics are Phase 16:

- Semantic Business Correctness Score
- Logic-vs-Execution Gap
- Explanation-vs-SQL Consistency
- Judge agreement/cost summary

## Tests To Add

| Test file | Required coverage |
|---|---|
| `tests/tier1_unit/test_dataset_loader_sampling.py` | `--samples-per-level`, deterministic ordering, difficulty counts |
| `tests/tier1_unit/test_metrics_bootstrap.py` | Bootstrap CI bounds and deterministic seed |
| `tests/tier1_unit/test_benchmark_artifact_contract.py` | Model slug, ablation metadata, prompt/response fields |
| `tests/tier2_integration/test_agent_benchmark_trace.py` | Mocked agent benchmark writes predictions, attempts, summary and config without requiring a local LLM |

## Current Limitations

- Local model smoke must be re-run whenever the default model path, llama-cpp dependency or prompt/output parser changes.
- Terminal entry points must bootstrap the project root before importing `src`; otherwise the documented PowerShell commands are not reproducible from a clean shell.
- First bottleneck fixed on 2026-05-15: SQL-positive agent failures now use specific labels such as `INVALID_SQL` and `RESULT_MISMATCH` instead of the coarse `BEHAVIOR_MISMATCH`.
- Sample-20 first attempt exposed missing per-case exception containment: model context overflow stopped the whole benchmark before artifacts were finalized.
- Local generation context must be configurable through `VTD_LLM_N_CTX`; complex benchmark prompts can exceed a hardcoded `2048` token window.
- Agent benchmarks should reuse the local GGUF model instance within a process. Reloading the model for every generation/retry makes sample-20 and balanced runs unnecessarily slow.
- Behavior benchmark first attempt showed non-SQL cases can still enter the LLM generation/retry path. `should_generate_sql=false` must be persisted in graph state and routed before generation.
- Behavior routed run showed EX/Valid SQL metrics must exclude non-SQL records; action correctness and SQL execution correctness now remain separate in the metrics layer.
- Full paper-grade dev/test agent runs still need to be executed and inspected after Phase 11 quality/ablation setup; the Phase 10 artifact contract is already verified.
- Agent accuracy bottlenecks must be debugged from the new prompt/response traces.
- `src/evaluation/benchmark_runner.py` does not yet expose a reusable progress callback; progress currently lives in `scripts/run_benchmark.py`.
- EX@first/EX@final and retry success need more explicit attempt-level metric extraction.
- `src/output` is still placeholder and should not be treated as Phase 12-complete.
- Semantic/business correctness is not judged yet; Phase 16 owns that layer.

## Definition of Done

Phase 10 is done when:

- `--mode agent --dataset dev --sample 20` runs without manual intervention.
- `--mode agent --dataset dev --samples-per-level 5` runs and records selected difficulty counts.
- Terminal logs show progress, per-case latency, elapsed time and ETA.
- Every run stores config, predictions, attempts, failures, summary, CSVs and paper tables.
- Predictions and attempts include exact prompt and raw model response.
- Model slug and ablation id are visible in folder/file names and summaries.
- EX/action/reliability metrics have 95% CI where applicable.
- SQL execution correctness is reported separately from semantic/business correctness.
- Unsafe pass-through is reported and remains `0`.
- Dev/test benchmark commands can run with `--exclude-self` and record removed self-overlap counts in config, predictions and summary.

Status on 2026-05-17: done for infrastructure. Do not interpret this as a SOTA accuracy claim; the current local-agent quality remains weak and must be handled through Phase 11 ablations, Phase 13 reliability work and Phase 16 semantic/business judging.
