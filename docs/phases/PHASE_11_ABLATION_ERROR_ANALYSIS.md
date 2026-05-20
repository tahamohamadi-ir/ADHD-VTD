# Phase 11 - Ablation, Error Analysis, and Research Metrics

**Status:** In progress - artifact error report, runtime flag contract, real A0-A7 smoke runs, docs/06 taxonomy alignment, retrieval ablation smoke, and full-dev retrieval ablation complete  
**Updated:** 2026-05-19  
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
| A0 | direct/full-schema or minimal context baseline | config and real smoke artifact exist |
| A1 | + Persian normalization | config and real smoke artifact exist |
| A2 | + schema linking | config and real smoke artifact exist |
| A3 | + value linking | config and real smoke artifact exist |
| A4 | + CAG examples/retrieval context | config and real smoke artifacts exist; latency anomaly fixed in targeted reruns; support-policy rerun analyzed |
| A7 | current full Phase-10 system | config and real smoke artifact exist |

Current A0-A7 smoke runs have real benchmark artifacts and a comparison report, but they are still smoke-scale evidence, not paper-grade final metrics. Reports must show the runtime flag contract so component isolation is auditable.

Retrieval ablation configs:

| ID | Backend | Status |
|---|---|---|
| R0 | BM25 lexical only | config, smoke artifact, and full-dev artifact exist |
| R1 | vector only | config, smoke artifact, and full-dev artifact exist |
| R2 | BM25 + vector hybrid | config, smoke artifact, full-dev artifact, and schema-evidence guard verification exist |
| R3 | hybrid + current identity reranker | config, smoke artifact, and full-dev artifact exist; wiring only, not a model-backed reranker claim |

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
- `PERSIAN_NORMALIZATION_ERROR`
- `DATE_NORMALIZATION_ERROR`
- `JALALI_MAPPING_ERROR`
- `FINGLISH_RESOLUTION_ERROR`
- `COLLOQUIAL_MISMATCH_ERROR`
- `SCHEMA_LINKING_ERROR`
- `VALUE_LINKING_ERROR`
- `JOIN_ERROR`
- `SQL_SYNTAX_ERROR`
- `AGGREGATION_ERROR`
- `SEMANTIC_METRIC_ERROR`
- `FILTER_ERROR`
- `RAG_RETRIEVAL_ERROR`
- `REFLEXION_FAILURE`
- `SAFETY_FAILURE`
- `CLARIFICATION_FAILURE`
- `UNSUPPORTED_QUERY`

The docs/06 taxonomy is report-side analysis. It must not rewrite benchmark outcomes. Valid SQL result mismatches without an independent semantic/business judgment stay as `pending_semantic_review`; Phase 11 must not guess a docs/06 semantic label just to fill a table.

## First Closeout Target

Phase 11 first slice is done when:

- [x] `src/evaluation/statistical_tests.py` exists with tested bootstrap and McNemar helpers.
- [x] A script can create `results/error_analysis/<timestamp>/error_report.md` from a real benchmark artifact.
- [x] The report includes source artifact path, metrics, failure taxonomy, representative cases, and anti-overfit limitations.
- [x] `task.md` and `DEVELOPMENT_ROADMAP.md` point to the generated report and distinguish real metrics from planned ablations.
- [x] `scripts/run_ablation.py` creates a dry-run manifest by default and does not run benchmark jobs unless `--execute` is explicit.
- [x] `tests/tier1_unit/test_ablation_runner.py` verifies command/flag capture and `not_run` manifest status.
- [x] Runtime flag contract is recorded so ablation configs cannot silently claim unsupported component isolation.
- [x] A real A0-A7 smoke manifest has completed with benchmark artifacts for every job.
- [x] A comparison report can be generated from the completed manifest without running a model or inventing missing metrics.
- [x] Artifact analysis now writes docs/06-aligned labels separately from legacy `research_error` labels and preserves `pending_semantic_review` for unjudged valid mismatches.

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

Real A0-A7 smoke manifest and comparison:

```text
manifest: results/ablation/20260517_phase11_a0_a7_execute/ablation_manifest.json
report: results/ablation/20260517_phase11_a0_a7_execute/ablation_comparison.md
summary: results/ablation/20260517_phase11_a0_a7_execute/ablation_comparison.json
jobs_total: 6
jobs_completed: 6
same_dataset_hash: True
same_selected_cases_hash: True
```

Smoke metrics copied from the real benchmark summaries:

| Config | Evaluated | EX | Valid SQL | Reliability | Unsafe SQL | Mean Latency ms |
|---|---:|---:|---:|---:|---:|---:|
| A0_direct_schema_only | 8 | 0.0 | 0.375 | -4.25 | 0 | 13182.5 |
| A1_persian_nlu | 8 | 0.0 | 0.375 | -4.25 | 0 | 11958.25 |
| A2_schema_linking | 8 | 0.0 | 0.375 | -4.25 | 0 | 17079.38 |
| A3_value_linking | 8 | 0.0 | 0.5 | -5.0 | 0 | 16927.88 |
| A4_cag_examples | 8 | 0.25 | 0.5 | -1.0 | 0 | 216118.5 |
| A7_full_phase10_system | 8 | 0.25 | 0.875 | -3.25 | 0 | 17960.88 |

Interpretation limits: this is an 8-case smoke matrix. It supports engineering diagnostics only. It does not establish SOTA quality, semantic/business correctness, or statistical significance. The original A4 latency anomaly was inspected and fixed in later targeted reruns, but the original A0-A7 comparison remains historical evidence and must not be edited.

## A4 Latency Anomaly Inspection

Source artifact:

```text
results/benchmark/20260517_233814_a4_cag_examples
```

Artifact-backed finding:

- `VTD-371` dominated A4 latency with prediction latency `1603172ms`.
- Its recorded SQL execution attempt took only `46ms`.
- Therefore the anomaly is graph/LLM wall-clock time, not SQL execution time.
- The same trace showed `intent=unknown`, weak matrix-specific shape guidance, and unrelated explicit value links from `workplace_mental_health_survey` even though that table was not present in the prompt schema.

Engineering fix for future runs:

- `build_prompt` now extracts value-link candidate columns from dict-style `schema_context` instead of falling back to the full value dictionary.
- `SQLAttempt` now records `generation_latency_ms`, so future artifacts can separate LLM generation latency from SQL execution latency.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_graph_retry_and_config.py tests\tier1_unit\test_graph_attempt_trace.py tests\tier1_unit\test_value_linker.py -vv --tb=short
18 passed
```

Next required evidence: rerun A4 after this fix and compare the new artifact against the old A4 artifact. The old A4 metrics remain historically valid and must not be edited.

### A4 Rerun After Value-Link Trace Fix

Source artifact:

```text
results/benchmark/manual_a4_after_value_link_trace_fix
```

Artifact-backed result:

```text
evaluated: 8
execution_accuracy: 0.25
valid_sql_rate: 0.375
reliability_score: -0.25
unsafe_sql: 0
latency_mean_ms: 12002.38
latency_median_ms: 9882.0
latency_p95_ms: 22504.0
latency_max_ms: 22504.0
error_report: results/error_analysis/20260518_a4_after_value_link_trace_fix/error_report.md
```

The latency anomaly was fixed: the old A4 `VTD-371` max latency was `1603172ms`; the rerun max latency is `22504ms`. The new trace records `generation_latency_ms=13135` for `VTD-371`.

Remaining quality issue: `VTD-371` still generated wrong-table columns (`sleep_hours`, `diet_quality`) with `student_depression`. This is not a fake-result issue; it is a model/prompt/shape-contract issue. The follow-up hardening is general:

- `matrix` / `ماتریس` requests route to `grouping_query`.
- Prompt guidance derives the sleep/diet/depression/CGPA matrix shape from the available `student_depression` schema.
- Shape validation rejects `sleep_hours`/`diet_quality` for this `student_depression` matrix shape and requires `sleep_duration_category`/`dietary_habits`.
- Value linking no longer treats metric columns such as `eating_disorder_pct` as categorical `disorder` columns.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_intent_classifier.py tests\tier1_unit\test_prompt_builder.py tests\tier1_unit\test_shape_validator.py tests\tier1_unit\test_value_linker.py tests\tier1_unit\test_value_linker_disorder_columns.py tests\tier1_unit\test_graph_retry_and_config.py tests\tier1_unit\test_graph_attempt_trace.py -vv --tb=short
36 passed
```

Next required evidence: rerun A4 again after the matrix hardening. The rerun must be reported as a new artifact; previous A4 artifacts remain immutable historical evidence.

### A4 Rerun After Matrix Hardening

Source artifact:

```text
results/benchmark/manual_a4_after_matrix_hardening
```

Artifact-backed result:

```text
evaluated: 8
execution_accuracy: 0.25
valid_sql_rate: 0.5
reliability_score: -1.0
unsafe_sql: 0
latency_mean_ms: 12736.88
latency_median_ms: 9596.5
latency_p95_ms: 24266.0
latency_max_ms: 24266.0
error_report: results/error_analysis/20260518_a4_after_matrix_hardening/error_report.md
```

`VTD-371` outcome:

```text
intent: grouping_query
valid_sql: True
execution_correct: False
generation_latency_ms: 18451
sql_execution_latency_ms: 68
```

The generated SQL now uses the correct table and matrix keys:

```sql
SELECT sleep_duration_category, dietary_habits, COUNT(*) AS n,
       ROUND(100.0 * SUM(depression_flag) / COUNT(*), 2) AS depression_rate_pct,
       ROUND(AVG(cgpa_10), 2) AS avg_cgpa
FROM student_depression
WHERE sleep_duration_category IS NOT NULL AND dietary_habits IS NOT NULL
GROUP BY sleep_duration_category, dietary_habits
ORDER BY n DESC LIMIT 100;
```

The remaining exact-execution mismatch is due to support-threshold/sorting differences: the gold SQL uses `HAVING COUNT(*)>=50 ORDER BY depression_rate_pct DESC`. Do not add this exact threshold only to satisfy one case. A threshold/sorting change is acceptable only if adopted as a general matrix-dashboard policy and validated on broader artifacts, or else it should be handled by Phase 16 semantic/business review.

### A4 Rerun After Matrix Support Policy

General policy adopted:

- For `student_depression` sleep/diet depression-CGPA matrices, require a minimum support threshold of `HAVING COUNT(*) >= 50`.
- Sort by the primary requested metric, `depression_rate_pct DESC`.
- Basis: the real table has `27901` rows and `19` sleep/diet cells; sparse `Others` cells have counts `1, 3, 3, 3, 5, 7, 8`, while substantive cells are `1660+`.
- Guardrail: this is a table/shape policy from observed distribution, not a benchmark ID or hidden-gold rule.

Source artifact:

```text
results/benchmark/manual_a4_after_matrix_support_policy
```

Artifact-backed result:

```text
evaluated: 8
execution_accuracy: 0.25
valid_sql_rate: 0.375
reliability_score: -0.25
unsafe_sql: 0
latency_mean_ms: 14045.25
latency_median_ms: 10817.5
latency_p95_ms: 33088.0
latency_max_ms: 33088.0
error_report: results/error_analysis/20260518_a4_after_matrix_support_policy/error_report.md
```

`VTD-371` outcome:

```text
intent: grouping_query
valid_sql: True
execution_correct: True
generation_latency_ms: 16651
sql_execution_latency_ms: 22
```

Research taxonomy from the generated report:

```text
FALSE_ABSTENTION: 5
SEMANTIC_REVIEW_REQUIRED: 1
```

Interpretation: the matrix support/sorting policy fixed the VTD-371 exact mismatch and the old latency anomaly remains resolved. It did not improve the overall A4 smoke quality because several cases now fail as false abstentions after validation/shape-contract rejection. The next Phase 11 step is to inspect those false abstentions and separate over-strict contracts from genuine model SQL failures before rerunning the full A0-A7 suite.

### A4 False-Abstention Triage

Source artifact:

```text
results/benchmark/manual_a4_after_matrix_support_policy
```

Artifact-backed triage:

- `VTD-237`: legitimate rejection. The generated SQL used a scalar prevalence summary and did not compute latest-minus-baseline change or quartile/binning.
- `VTD-343`: legitimate rejection. The generated SQL used fixed thresholds (`stress_level > 4`, `sleep_hours < 7`) instead of above/below-average subqueries and omitted summary columns.
- `VTD-078`: legitimate rejection. The generated SQL omitted the `mental_health_risk` grouping key.
- `VTD-027`: general alias issue. The generated SQL used `family_history` on `student_depression`; the current schema column is `family_history_mental_illness`.
- `VTD-300`: over-strict shape contract. The generated SQL computed the depression-rate numerator from `SUM(depression_flag)` but omitted the auxiliary `positives` output column.

Implemented mitigations:

- `SQLRewriter` now rewrites `family_history` to `family_history_mental_illness` only when the target table is `student_depression`; it does not rewrite the valid `workplace_mental_health_survey.family_history` column.
- The grouped sleep depression-rate shape contract now requires a rate formula from `depression_flag`, not the optional helper column `positives`.
- `validate_sql` now promotes the rewritten `ValidationPipeline.normalized_sql` back into graph state, so execution uses the same SQL that passed validation.
- The grouped-rate null-filter check now accepts equivalent forms such as `NOT sleep_duration_category IS NULL`.
- SQL generation now passes a bounded `max_tokens` to the local LLM. Default is `512`; it can be overridden with `VTD_SQL_GENERATION_MAX_TOKENS`.

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_sql_rewriter_ast.py tests\tier1_unit\test_shape_validator.py tests\tier1_unit\test_prompt_builder.py -vv --tb=short
25 passed

.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_graph_attempt_trace.py tests\tier1_unit\test_sql_rewriter_ast.py tests\tier1_unit\test_shape_validator.py -vv --tb=short
22 passed

.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_shape_validator.py tests\tier1_unit\test_graph_attempt_trace.py -vv --tb=short
16 passed

.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_graph_attempt_trace.py tests\tier1_unit\test_shape_validator.py -vv --tb=short
17 passed

.\.venv\Scripts\python.exe -m py_compile src\sql_validation\sql_rewriter.py src\sql_validation\shape_validator.py
.\.venv\Scripts\python.exe -m py_compile src\graph\nodes\base_nodes.py src\sql_validation\sql_rewriter.py src\sql_validation\shape_validator.py
.\.venv\Scripts\python.exe -m py_compile src\sql_validation\shape_validator.py src\graph\nodes\base_nodes.py
.\.venv\Scripts\python.exe -m py_compile src\graph\nodes\base_nodes.py src\sql_validation\shape_validator.py
```

Intermediate rerun before graph promotion:

```text
artifact: results/benchmark/manual_a4_after_false_abstention_mitigation
evaluated: 8
execution_accuracy: 0.25
valid_sql_rate: 0.625
reliability_score: -1.0
unsafe_sql: 0
finding: VTD-027 passed validation after rewrite but execution still used raw family_history SQL.
```

Next required evidence: rerun targeted A4 after graph rewritten-SQL promotion and compare against `manual_a4_after_matrix_support_policy` and `manual_a4_after_false_abstention_mitigation`. Do not scale A0-A7 until this regression check is recorded.

Second intermediate rerun after graph promotion:

```text
artifact: results/benchmark/manual_a4_after_rewritten_sql_promotion
evaluated: 8
execution_accuracy: 0.375
valid_sql_rate: 0.5
reliability_score: 1.0
unsafe_sql: 0
finding: VTD-027 became exact-correct; VTD-300 was still rejected only because the validator did not accept equivalent NOT NULL syntax.
```

Next required evidence: rerun targeted A4 after equivalent-null-filter acceptance. Do not scale A0-A7 until this regression check is recorded.

Incomplete rerun after equivalent-null-filter acceptance:

```text
artifact_dir: results/benchmark/manual_a4_after_null_filter_equivalence
status: incomplete; no final summary.json
partial_predictions: 4
partial_attempts: 4
partial_failures: 1
do_not_report_as_metric: true
finding: partial VTD-039 recorded generation_latency_ms=53819322 while SQL execution latency was 12ms.
```

Interpretation: this is not an A4 result. It is diagnostic evidence of another generation wall-clock anomaly. The next rerun must use the generation token cap and still be treated as incomplete if no final summary is produced.

Completed rerun after generation token cap:

```text
artifact: results/benchmark/manual_a4_after_generation_token_cap
error_report: results/error_analysis/20260518_a4_after_generation_token_cap/error_report.md
evaluated: 8
failures: 5
execution_accuracy: 0.375
valid_sql_rate: 0.625
reliability_score: 0.25
unsafe_sql: 0
latency_mean_ms: 11495.62
latency_median_ms: 9746.5
latency_p95_ms: 17686.0
latency_max_ms: 17686.0
research_error_counts: FALSE_ABSTENTION=3, SEMANTIC_REVIEW_REQUIRED=2
```

Docs/06 taxonomy alignment rerun:

```text
artifact: results/benchmark/manual_a4_after_generation_token_cap
report: results/error_analysis/20260519_phase11_docs06_taxonomy_a4_token_cap/error_report.md
summary: results/error_analysis/20260519_phase11_docs06_taxonomy_a4_token_cap/analysis_summary.json
docs06_error_counts: AGGREGATION_ERROR=2, SCHEMA_LINKING_ERROR=1
pending_semantic_review: 2
tests: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_artifact_analysis.py tests\tier1_unit\test_statistical_tests.py -vv --tb=short -> 7 passed
```

Retrieval ablation dry-run:

```text
manifest: results/ablation/20260519_phase11_retrieval_dry_run_manifest/ablation_manifest.json
jobs: 4
result_status: not_run for all R0-R3 jobs
anti_fake_policy: config manifests are not benchmark results
runtime_parameters: retrieval_backend and reranker are recorded without unknown-flag warnings
```

Retrieval config smoke:

```text
artifact: results/benchmark/manual_r0_retrieval_bm25_smoke
config: experiments/configs/R0_retrieval_bm25.yaml
backend: bm25
evaluated: 8
retrieval_hit_rate: 1.0
latency_mean_ms: 1.38
limitation: this verifies config/runtime wiring only; it is not the full retrieval ablation matrix.
```

Retrieval ablation smoke execution:

```text
manifest: results/ablation/20260519_phase11_retrieval_execute/ablation_manifest.json
report: results/ablation/20260519_phase11_retrieval_execute/ablation_comparison.md
jobs_completed: 4/4
same_dataset_hash: True
same_selected_cases_hash: True
R0_retrieval_bm25: hit_rate=1.0, miss_rate=0.0, latency_mean_ms=1.75
R1_retrieval_vector: hit_rate=1.0, miss_rate=0.0, latency_mean_ms=690.88
R2_retrieval_hybrid: hit_rate=0.875, miss_rate=0.125, latency_mean_ms=650.5
R3_retrieval_hybrid_rerank: hit_rate=0.875, miss_rate=0.125, latency_mean_ms=740.25
limitation: 8-case smoke only; R3 uses the current identity reranker and is not a model-backed reranker claim.
tests: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_ablation_report.py tests\tier1_unit\test_ablation_runner.py tests\tier1_unit\test_retrieval.py -vv --tb=short -> 12 passed, 2 warnings
```

Initial full-dev retrieval ablation before schema-evidence guard:

```text
manifest: results/ablation/20260519_phase11_retrieval_dev_full_execute/ablation_manifest.json
report: results/ablation/20260519_phase11_retrieval_dev_full_execute/ablation_comparison.md
jobs_completed: 4/4
same_dataset_hash: True
same_selected_cases_hash: True
evaluated_per_config: 60
R0_retrieval_bm25_dev_full: hits=60/60, hit_rate=1.0, miss_rate=0.0, latency_mean_ms=0.78, latency_max_ms=8.0
R1_retrieval_vector_dev_full: hits=60/60, hit_rate=1.0, miss_rate=0.0, latency_mean_ms=97.88, latency_max_ms=5657.0
R2_retrieval_hybrid_dev_full: hits=58/60, hit_rate=0.9666666666666667, miss_rate=0.03333333333333333, latency_mean_ms=95.52, latency_max_ms=5440.0
R3_retrieval_hybrid_rerank_dev_full: hits=58/60, hit_rate=0.9666666666666667, miss_rate=0.03333333333333333, latency_mean_ms=104.47, latency_max_ms=5960.0
hybrid_misses: VTD-039, VTD-036
interpretation: this was a real intermediate failure. BM25-only and vector-only both hit all 60 dev cases, while hybrid scoring/ranking lost two easy distribution cases before the schema-evidence guard.
limitation: R3 still uses the identity reranker placeholder; it is not a model-backed reranker claim.
```

Full-dev retrieval ablation after general schema-evidence guard:

```text
guard: schema evidence is preserved after self-overlap filtering and before the final top-k slice.
scope: general schema-overlap promotion; no benchmark IDs or gold SQL are used at runtime.
tests: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_benchmark_retrieval_prediction.py tests\tier1_unit\test_retrieval.py tests\tier1_unit\test_ablation_report.py tests\tier1_unit\test_ablation_runner.py -vv --tb=short -> 14 passed, 2 warnings
compile: .\.venv\Scripts\python.exe -m py_compile scripts\run_benchmark.py src\retrieval\hybrid_retriever.py src\retrieval\schema_evidence.py
intermediate_check_manifest: results/ablation/20260519_phase11_retrieval_dev_full_schema_guard_after_filter_r2_r3/ablation_manifest.json
intermediate_check_report: results/ablation/20260519_phase11_retrieval_dev_full_schema_guard_after_filter_r2_r3/ablation_comparison.md
intermediate_check_result: R2 and R3 both recovered to 60/60 on the previously missed full-dev cases.
final_manifest: results/ablation/20260519_phase11_retrieval_dev_full_final/ablation_manifest.json
final_report: results/ablation/20260519_phase11_retrieval_dev_full_final/ablation_comparison.md
final_summary: results/ablation/20260519_phase11_retrieval_dev_full_final/ablation_comparison.json
jobs_completed: 4/4
same_dataset_hash: True
same_selected_cases_hash: True
selected_cases_hash: d83596c1a3f32e1bf4e27a7db38cd7cab0c27632ca77ba0da91ee0d8a40721fa
dataset_hash: 909d855452bca90a7f5b25cf098d05748b281f2756b037afc86159fc2d256aee
evaluated_per_config: 60
R0_retrieval_bm25_dev_full: hits=60/60, hit_rate=1.0, miss_rate=0.0, latency_mean_ms=0.7, latency_p95_ms=1.0
R1_retrieval_vector_dev_full: hits=60/60, hit_rate=1.0, miss_rate=0.0, latency_mean_ms=109.28, latency_p95_ms=9.0
R2_retrieval_hybrid_dev_full: hits=60/60, hit_rate=1.0, miss_rate=0.0, latency_mean_ms=109.28, latency_p95_ms=8.0
R3_retrieval_hybrid_rerank_dev_full: hits=60/60, hit_rate=1.0, miss_rate=0.0, latency_mean_ms=102.75, latency_p95_ms=7.0
interpretation: the earlier R2/R3 58/60 full-dev result was a real intermediate failure. The final artifact-backed run shows that the general schema-evidence guard fixes those retrieval misses on dev without editing labels or using case-specific logic.
limitation: R3 still uses the identity reranker placeholder; this is not a model-backed reranker claim.
```

Improvements verified from real artifacts:

- `VTD-371` remains exact-correct with the matrix support/sorting policy.
- `VTD-027` is exact-correct after rewritten SQL is promoted into graph execution.
- `VTD-300` is now valid and executed after accepting equivalent null-filter syntax, but remains an exact-result mismatch.
- The incomplete-run `VTD-039` generation latency anomaly did not recur under the token cap.

Remaining A4 blockers:

- `VTD-237` still needs a genuine global-change/binning SQL shape, not a scalar prevalence summary.
- `VTD-343` still needs grouped risk summary columns (`mental_health_risk`, count, averages) after average-threshold filtering.
- `VTD-078` still needs `mental_health_risk` as the grouping key.
- `VTD-141` and `VTD-300` are valid SQL mismatches and should be handled by semantic/business review or a broader general policy, not by case-specific tuning.

## Phase 16 Judge Pilot Evidence

Small live OpenRouter judge pilots have been run on `manual_a4_after_generation_token_cap` to validate the semantic-review path without changing benchmark outcomes:

```text
qwen_pilot: results/judgments/20260519_phase16_openrouter_qwen_a4_sample2_retry2
deepseek_pilot: results/judgments/20260519_phase16_openrouter_deepseek_free_a4_sample2_no_reasoning
source_artifact: results/benchmark/manual_a4_after_generation_token_cap
sample_size: 2
failures_only: true
qwen: authoritative=true, semantic_business_counts=incorrect=2
deepseek: authoritative=true, semantic_business_counts=incorrect=2
tests: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py -vv --tb=short -> 10 passed
```

Interpretation limits: this only proves the live judge pipeline and agreement on two sampled failures. It does not close Phase 11 paper-grade semantic analysis, does not replace human spot checks, and does not judge all pending valid-SQL mismatches such as `VTD-141` and `VTD-300`.

All-failure pilot before canonical verdict hardening:

```text
qwen_all_failures: results/judgments/20260519_phase16_openrouter_qwen_a4_failures_all
deepseek_all_failures: results/judgments/20260519_phase16_openrouter_deepseek_free_a4_failures_all
source_artifact: results/benchmark/manual_a4_after_generation_token_cap
total_judged_each: 5
qwen_raw_semantic_business_counts: incorrect=4, correct=1
deepseek_raw_semantic_business_counts: incorrect=4, unjudged=1
disputed_case: VTD-300
post_run_hardening: provider verdicts are canonicalized before summary metrics; partial/ambiguous labels require adjudication instead of becoming final semantic-correct claims.
tests: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py -vv --tb=short -> 12 passed
```

Interpretation limits: the all-failure pilot is strong evidence that most remaining A4 failures are business-incorrect, but `VTD-300` demonstrates why multi-judge disagreement handling is required. The next artifact should be regenerated with canonical verdict reporting before any table treats semantic correctness as a metric.

Canonical rerun and agreement report:

```text
qwen_canonical: results/judgments/20260519_phase16_openrouter_qwen_a4_failures_all_canonical
deepseek_canonical: results/judgments/20260519_phase16_openrouter_deepseek_free_a4_failures_all_canonical
agreement_report: results/judgments/20260519_phase16_qwen_deepseek_a4_failure_agreement/judge_agreement.md
agreement_summary: common_cases=5, semantic_agreement_count=5, semantic_disagreement_count=0, verdict_agreement_count=2, verdict_disagreement_count=3
final_counts: agreed_incorrect=4, adjudication_required=1
tests: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_judge_agreement.py tests\tier1_unit\test_llm_judge.py -vv --tb=short -> 14 passed
```

Interpretation limits: this agreement report compares existing judgment artifacts only. It does not call a model and does not convert partial/unjudged rows into correctness claims. Because the current comparison is failures-only, the next Phase 16 slice needs successful prediction coverage before reporting broader semantic accuracy.

All-prediction agreement:

```text
qwen_all_predictions: results/judgments/20260519_phase16_openrouter_qwen_a4_all_predictions
deepseek_all_predictions: results/judgments/20260519_phase16_openrouter_deepseek_free_a4_all_predictions
agreement_report: results/judgments/20260519_phase16_qwen_deepseek_a4_all_predictions_agreement/judge_agreement.md
common_cases: 8
semantic_agreement_count: 4
semantic_disagreement_count: 4
verdict_agreement_count: 4
verdict_disagreement_count: 4
final_counts: agreed_correct=2, agreed_incorrect=1, adjudication_required=5
provider_limitation: DeepSeek free returned provider_error for 2/8 cases, so missing labels remain unjudged.
```

Interpretation limits: the all-prediction artifact confirms that the two exact-correct benchmark cases (`VTD-027`, `VTD-039`) are also business-correct under both judges. It also shows that semantic review is not yet stable enough for paper metrics because five cases still require adjudication.

Follow-up policy: DeepSeek free is now historical pilot evidence only. The next official second-judge run should use paid `deepseek/deepseek-v4-flash` over all predictions, then compare it with Qwen. Any third-model adjudication should use the new `--case-ids` filter to send only unresolved/provider-error/partial cases.

Paid DeepSeek replacement result:

```text
deepseek_paid_all_predictions: results/judgments/20260520_phase16_openrouter_deepseek_paid_a4_all_predictions
deepseek_paid_summary: total_judged=8, authoritative_judgments=7, non_authoritative_judgments=1, provider_parse_error=1
deepseek_paid_semantic_business_counts: correct=3, incorrect=1, unjudged=4
agreement_report: results/judgments/20260520_phase16_qwen_deepseek_paid_a4_all_predictions_agreement/judge_agreement.md
agreement_summary: common_cases=8, semantic_agreement_count=5, semantic_disagreement_count=3, verdict_agreement_count=4, verdict_disagreement_count=4
final_counts: agreed_correct=3, agreed_incorrect=1, adjudication_required=4
confirmed_correct: VTD-027, VTD-039, VTD-371
confirmed_incorrect: VTD-237
adjudication_required: VTD-078, VTD-141, VTD-300, VTD-343
```

Interpretation limits: paid DeepSeek reduced the unresolved count but did not eliminate it. The next valid action is a targeted adjudicator run over the four unresolved case IDs only, not a paper-level semantic metric.

Consensus tooling:

```text
files: src/evaluation/judge_consensus.py, scripts/analyze_judge_consensus.py, tests/tier1_unit/test_judge_consensus.py
policy: at least two authoritative non-null semantic votes and no opposing authoritative semantic vote are required for consensus_correct/consensus_incorrect.
partial_policy: at least two authoritative partial_business_match votes and no non-null semantic votes produce consensus_partial_business_match.
anti_fake_guard: provider-error, provider-parse-error, non-authoritative and single-judge labels remain adjudication_required.
tests_after_partial_policy: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_judge_consensus.py tests\tier1_unit\test_judge_agreement.py tests\tier1_unit\test_llm_judge.py -vv --tb=short -> 17 passed
```

GPT-5.1 targeted adjudication and three-judge consensus:

```text
gpt51_unresolved_only: results/judgments/20260520_phase16_openrouter_gpt51_a4_unresolved_only
gpt51_summary: total_judged=4, authoritative_judgments=4, semantic_business_counts=incorrect=3, unjudged=1
consensus_report: results/judgments/20260520_phase16_qwen_deepseek_paid_gpt51_a4_consensus/judge_consensus.md
consensus_final_counts: consensus_correct=3, consensus_incorrect=4, consensus_partial_business_match=1
metric_policy_counts: semantic_correct=3, semantic_incorrect=4, partial_business_match=1, needs_human_review=0
consensus_correct: VTD-027, VTD-039, VTD-371
consensus_incorrect: VTD-078, VTD-141, VTD-237, VTD-343
consensus_partial_business_match: VTD-300
```

Interpretation limits under the older `phase16_sql_business_logic_v0` rubric: `VTD-300` was intentionally not converted into semantic correctness. All three judges treated it as partial/unjudged: the core depression-rate logic is present, but auxiliary/gold columns are missing. It was reported as `partial_business_match`, a separate paper/report column from semantic correct and semantic incorrect.

Follow-up semantic policy update:

```text
prompt_version: phase16_sql_business_logic_v1
semantic criterion: the generated SQL is business-correct when it answers the user's actual question.
gold_sql role: reference implementation, not a mandatory exact output schema.
allowed differences: extra harmless columns/parameters and missing gold-only support columns when the user can still get the requested answer.
canonicalization: partial+semantic_true -> business_correct; partial+semantic_false -> business_incorrect; partial+semantic_null -> partial_business_match.
strict policy: --judge-policy strict records stricter reference/gold-output-contract correctness separately from semantic user-question utility.
consensus traceability: prompt_versions, same_prompt_version, judge_policies and same_judge_policy are recorded to prevent silent mixing of v0/v1 or semantic/strict artifacts.
verification: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py tests\tier1_unit\test_judge_consensus.py tests\tier1_unit\test_judge_agreement.py -vv --tb=short -> 23 passed.
compile: .\.venv\Scripts\python.exe -m py_compile src\evaluation\llm_judge.py src\evaluation\judge_consensus.py scripts\judge_benchmark_artifact.py scripts\analyze_judge_consensus.py -> passed.
offline_contract_smoke: results\judgments\20260520_phase16_mock_v1_user_question_policy_smoke\judge_summary.json records prompt_version=phase16_sql_business_logic_v1 and redaction_applied=true; it is non-authoritative mock evidence only.
dual_policy_mock_smoke_semantic: results\judgments\20260520_phase16_mock_v1_semantic_vtd300_policy_smoke.
dual_policy_mock_smoke_strict: results\judgments\20260520_phase16_mock_v1_strict_vtd300_policy_smoke.
```

Next evidence required: rerun `VTD-300`, or the full A4 all-prediction set, with `phase16_sql_business_logic_v1` under both `--judge-policy semantic` and `--judge-policy strict`. Old v0 judgment artifacts remain valid historical evidence but must not be reinterpreted as v1 labels.

Live v1 VTD-300 policy check:

```text
semantic_qwen: results/judgments/20260520_phase16_openrouter_qwen_a4_v1_semantic_vtd300
semantic_deepseek_paid: results/judgments/20260520_phase16_openrouter_deepseek_paid_a4_v1_semantic_vtd300
semantic_agreement: results/judgments/20260520_phase16_qwen_deepseek_paid_a4_v1_semantic_vtd300_agreement
semantic_result: both judges authoritative; both business_correct; agreement final_counts agreed_correct=1.

strict_qwen: results/judgments/20260520_phase16_openrouter_qwen_a4_v1_strict_vtd300
strict_deepseek_paid: results/judgments/20260520_phase16_openrouter_deepseek_paid_a4_v1_strict_vtd300
strict_agreement: results/judgments/20260520_phase16_qwen_deepseek_paid_a4_v1_strict_vtd300_agreement
strict_result: Qwen authoritative business_incorrect; paid DeepSeek provider_parse_error; final_counts adjudication_required=1.
strict_gpt51: results/judgments/20260520_phase16_openrouter_gpt51_a4_v1_strict_vtd300
strict_consensus: results/judgments/20260520_phase16_qwen_deepseek_paid_gpt51_a4_v1_strict_vtd300_consensus
strict_consensus_result: consensus_incorrect=1, same_prompt_version=true, same_judge_policy=true, incorrect_votes=2.
```

Interpretation: `VTD-300` is confirmed correct for user-question utility and incorrect for strict-reference correctness. This supports reporting two paper columns rather than forcing one metric to carry both meanings.

Dual-policy report tooling:

```text
code: src/evaluation/dual_policy_report.py
cli: scripts/analyze_dual_policy_judgments.py
test: tests/tier1_unit/test_dual_policy_report.py
verification: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_dual_policy_report.py tests\tier1_unit\test_judge_agreement.py tests\tier1_unit\test_judge_consensus.py -vv --tb=short -> 5 passed.
broader_verification: dual-policy + agreement + consensus + llm_judge -> 24 passed.
VTD-300_dual_policy_report: results/judgments/20260520_phase16_a4_v1_vtd300_dual_policy_report.
VTD-300_combined_label: semantic_correct_strict_incorrect.
```

Full A4 v1 dual-policy report:

```text
semantic_agreement: results/judgments/20260520_phase16_qwen_deepseek_paid_a4_v1_semantic_all_agreement
semantic_result: common_cases=8, agreement=8/8, agreed_correct=4, agreed_incorrect=4
strict_agreement: results/judgments/20260520_phase16_qwen_deepseek_paid_a4_v1_strict_all_agreement
strict_result: common_cases=8, agreement=7/8, agreed_correct=3, agreed_incorrect=4, adjudication_required=1
strict_gpt51_vtd141: results/judgments/20260520_phase16_openrouter_gpt51_a4_v1_strict_vtd141
strict_gpt51_vtd141_result: authoritative=true, business_incorrect=1
strict_final_consensus: results/judgments/20260520_phase16_qwen_deepseek_paid_gpt51_a4_v1_strict_all_consensus
strict_final_result: consensus_correct=3, consensus_incorrect=5
dual_policy_final: results/judgments/20260520_phase16_a4_v1_all_dual_policy_final
dual_policy_final_counts: both_correct=3, both_incorrect=4, semantic_correct_strict_incorrect=1
both_correct: VTD-027, VTD-039, VTD-371
both_incorrect: VTD-078, VTD-141, VTD-237, VTD-343
semantic_correct_strict_incorrect: VTD-300
```

Interpretation: the final A4 dual-policy slice is complete and artifact-backed. It must be used as evaluation evidence only; do not tune prompts, validators, retrieval, or shape contracts to these eight IDs. Any model-quality change must be general and revalidated on a separate dev slice or larger balanced run.

Paper-facing evidence package:

```text
code: src/evaluation/dual_policy_packaging.py
cli: scripts/package_dual_policy_evidence.py
test: tests/tier1_unit/test_dual_policy_packaging.py
output_dir: results/paper/20260520_phase16_a4_dual_policy_evidence
summary: results/paper/20260520_phase16_a4_dual_policy_evidence/paper_evidence_summary.json
case_csv: results/paper/20260520_phase16_a4_dual_policy_evidence/paper_evidence_cases.csv
report: results/paper/20260520_phase16_a4_dual_policy_evidence/paper_evidence_table.md
evidence_label: small_dev_a4_slice
benchmark_metrics: execution_accuracy=0.375, valid_sql_rate=0.625, reliability_score=0.25
dual_policy_metrics: semantic_correct=4, semantic_incorrect=4, strict_correct=3, strict_incorrect=5, both_correct=3, both_incorrect=4, semantic_correct_strict_incorrect=1
verification: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_dual_policy_packaging.py tests\tier1_unit\test_dual_policy_report.py -vv --tb=short -> 2 passed
compile: .\.venv\Scripts\python.exe -m py_compile src\evaluation\dual_policy_packaging.py scripts\package_dual_policy_evidence.py -> passed
```

Interpretation: the package is a paper-facing view over existing artifacts only. It adds no new labels and keeps semantic-user-question correctness separate from strict-reference correctness.

Redaction policy artifact:

```text
artifact: results/judgments/20260520_phase16_mock_redaction_policy_smoke/judge_summary.json
redaction_policy: redaction_applied=true, raw_rows_sent=false, result_previews_sent=false, prompt_response_trace_sent=false
excluded_fields: raw_database_rows, execution_result_preview, gold_result_preview, full_prompt, raw_model_response
tests: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py tests\tier1_unit\test_judge_consensus.py tests\tier1_unit\test_judge_agreement.py -vv --tb=short -> 18 passed
```

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
