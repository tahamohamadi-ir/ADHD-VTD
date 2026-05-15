# Phase 10 - Benchmark Runner and Trace Contract

**Status:** In progress  
**Updated:** 2026-05-15  
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
- `git_commit`

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

- Full sample-20 and full dev/test agent runs still need to be executed and inspected.
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
