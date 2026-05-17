# Phase 11 - Ablation, Error Analysis, and Research Metrics

**Status:** In progress - first artifact report and dry-run manifest complete  
**Updated:** 2026-05-17  
**Dependency:** Phase 10 benchmark/trace infrastructure is complete.  

## Non-Negotiable Rules

1. No fake results. A metric, table, or claim is valid only if it can be traced to a real benchmark artifact under `results/benchmark/`.
2. No overfit. Runtime prompts, validators, and ablation configs must not use hidden gold SQL, benchmark IDs, or case-specific answers.
3. No silent data substitution. Every report must store the exact artifact paths, dataset hashes, selected-case hashes, model name/path, ablation id, and module flags used.
4. Execution correctness and semantic/business correctness remain separate. Phase 11 can analyze the gap but must not invent judge labels.
5. Statistical claims need uncertainty estimates. Report bootstrap CI and paired tests only when the compared runs use the same case IDs.

## Goal

Phase 11 turns Phase 10 artifacts into research-grade evidence:

- ablation configuration matrix;
- artifact-backed metric comparison;
- paired statistical tests;
- detailed error taxonomy;
- representative failure analysis;
- paper-ready tables that cite source artifacts.

Phase 11 does not try to improve the model by hand-tuning to individual dev failures. Quality improvements must be validated through new runs and documented separately.

## First Implementation Slice

The first Phase 11 slice is artifact-only and offline:

1. Create statistical helpers for bootstrap confidence intervals and paired McNemar tests.
2. Create an artifact analyzer that reads real benchmark outputs and writes an error-analysis report.
3. Create ablation config templates, but mark them as execution configs, not results.
4. Add tests using small synthetic records only for the math/reporting functions, not for claiming model quality.

## Required Artifact Inputs

An analysis run must read:

```text
results/benchmark/<run>/*_summary.json
results/benchmark/<run>/*_predictions.jsonl
results/benchmark/<run>/*_attempts.jsonl
results/benchmark/<run>/*_failures.jsonl
```

If any required file is missing, the analyzer must fail or mark the report incomplete. It must not fill missing metrics with invented values.

## Ablation Matrix Policy

First-paper ablations:

| ID | Intent | Status |
|---|---|---|
| A0 | direct/full-schema or minimal context baseline | config only until run |
| A1 | + Persian normalization | config only until run |
| A2 | + schema linking | config only until run |
| A3 | + value linking | config only until run |
| A4 | + CAG examples/retrieval context | config only until run |
| A7 | current full Phase-10 system | config and smoke artifacts exist |

Some module flags are not yet fully wired as hard runtime disables. Reports must show `implemented_flags` and `declared_flags` separately when that matters.

## Statistical Testing Rules

Use paired tests only when two runs evaluated the same `case_id` set:

```text
same_case_ids = true
same_dataset_hash = preferred
same_selected_cases_hash = ideal
```

If case IDs differ, only descriptive metrics and unpaired confidence intervals are allowed.

McNemar counts:

```text
b = baseline wrong, system correct
c = baseline correct, system wrong
```

The report must include `b`, `c`, chi-square statistic, p-value approximation, and a warning when the sample is too small.

## Error Taxonomy

Primary categories:

- `INTENT_ERROR`
- `SAFETY_FALSE_POSITIVE`
- `FALSE_ABSTENTION`
- `INVALID_SQL`
- `RESULT_MISMATCH`
- `SCHEMA_LINKING_ERROR`
- `VALUE_LINKING_ERROR`
- `RETRIEVAL_ERROR`
- `AGGREGATION_ERROR`
- `FILTER_ERROR`
- `SHAPE_CONTRACT_ERROR`
- `REFLEXION_FAILURE`
- `SEMANTIC_REVIEW_REQUIRED`
- `UNKNOWN_ERROR`

The taxonomy is report-side analysis. It must not rewrite benchmark outcomes.

## First Closeout Target

Phase 11 first slice is done when:

- [x] `src/evaluation/statistical_tests.py` exists with tested bootstrap and McNemar helpers.
- [x] A script can create `results/error_analysis/<timestamp>/error_report.md` from a real benchmark artifact.
- [x] The report includes source artifact path, metrics, failure taxonomy, representative cases, and anti-overfit limitations.
- [x] `task.md` and `DEVELOPMENT_ROADMAP.md` point to the generated report and distinguish real metrics from planned ablations.
- [x] `scripts/run_ablation.py` creates a dry-run manifest by default and does not run benchmark jobs unless `--execute` is explicit.
- [x] `tests/tier1_unit/test_ablation_runner.py` verifies command/flag capture and `not_run` manifest status.
- [x] Runtime flag contract is recorded so ablation configs cannot silently claim unsupported component isolation.

## Verified Outputs

Focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_statistical_tests.py tests\tier1_unit\test_artifact_analysis.py tests\tier1_unit\test_ablation_runner.py -vv --tb=short
```

Result:

```text
7 passed; latest rerun after CLI Python-path fix: 7 passed in 0.13s
```

First artifact-backed report:

```text
results/error_analysis/20260517_phase11_spl2_after_fixes/error_report.md
```

Dry-run ablation manifest:

```text
results/ablation/20260517_phase11_dry_run_manifest/ablation_manifest.json
jobs: 6
result_status: not_run for all jobs
planned Python: D:\Project\ADHD-VTD\.venv\Scripts\python.exe
runtime_enforced: nlu, schema_linking, value_linking, cag, reflexion, repair
runtime_locked: safety, validation
metadata_only: none
```

This manifest is not an ablation result. Real ablation metrics require running the benchmark commands and citing the resulting `results/benchmark/...` artifact directories.

## Runtime Flag Contract

Current Phase 11 ablation flags are interpreted as follows:

| Flag | Status | Notes |
|---|---|---|
| `nlu` | runtime-enforced | `false` skips Persian normalization. |
| `schema_linking` | runtime-enforced | `false` uses full-schema context and marks `schema_linking_disabled`. |
| `value_linking` | runtime-enforced | `false` omits explicit value links; `true` resolves value links from schema-context candidate columns and injects them into prompt/state. |
| `cag` | runtime-enforced | `false` removes retrieved few-shot examples. |
| `reflexion` | runtime-enforced | `false` stops reflection after validation/execution errors. |
| `repair` | runtime-enforced | `false` stops repair routing even if reflexion is true. |
| `safety` | runtime-locked | Safety cannot be disabled for benchmark execution. |
| `validation` | runtime-locked | SQL validation cannot be disabled for benchmark execution. |

Value-linking isolation tests verify that `value_linking=true` includes resolved values such as `Female` in the prompt, while `value_linking=false` leaves the explicit value-link map empty.

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_value_linker.py tests\tier1_unit\test_ablation_runner.py tests\tier1_unit\test_graph_retry_and_config.py tests\tier1_unit\test_graph_routes.py -vv --tb=short
```

Result:

```text
19 passed
```
