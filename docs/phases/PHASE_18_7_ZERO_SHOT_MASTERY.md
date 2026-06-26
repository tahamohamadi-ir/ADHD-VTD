# Phase 18.7 - Zero-Shot Mastery

Status: in progress  
Baseline artifact: `results/benchmark/20260524_221942_agent_positive400_qwen2-5-coder-7b_phase18_5_general_templates_v2_no_exact_cache_exclude_self_full400`  
Baseline metrics: EX `245/400 = 61.25%`, valid SQL `93.5%`, failures `155`, unsafe SQL `0`, p95 latency `86.8s`

## Goal

Push the anti-overfit zero/few-shot pipeline beyond `65%` execution accuracy before QLoRA, without reintroducing exact SQL cache, case-id logic, or retrieval self-overlap.

The current bottleneck is not missing template coverage alone. The remaining failures are dominated by semantic/shape mismatches:

- Broad templates firing too early.
- One-dimensional grouping where the question asks for two dimensions.
- Schema collisions between similar columns across tables.
- Validator false positives for valid SQLite/window-function SQL.
- Expensive LLM retry loops after deterministic validation failures.

## Non-Negotiable Anti-Overfit Rules

- Keep `--exclude-self` enabled for all reported positive400 runs.
- Do not restore exact SQL cache or exact question-to-SQL lookup.
- Do not hardcode VTD case IDs in runtime code.
- Deterministic templates must not be the default generation path. They are allowed only as explicit ablation/debug artifacts or narrow guardrails that do not answer full benchmark questions.
- Any deterministic template ablation must be pattern/schema driven, not gold-SQL driven.
- Report fixed/regressed case counts against the 61.25% baseline artifact.
- Run at least one paraphrase or holdout check before declaring Phase 18.7 complete.

## Proposed Changes

### 18.7a - Template Safety, Schema Gating, Validator Fixes

1. Reorder template builders so specific and high-risk shapes run before broad distributions:
   - dashboard/KPI/story outputs
   - 2D grouping/rate outputs
   - depressed-vs-non-depressed comparisons
   - rank/window/z-score queries
   - simple distribution/count templates

2. Add a Template Safety Gate after template generation:
   - rate/percentage questions must not return count-only SQL.
   - multi-dimensional questions must not return single-column `GROUP BY`.
   - depressed-vs-non-depressed questions must not return a one-sided `WHERE depression_flag = X` filter.
   - dashboard/KPI/story questions must not return a single simple metric unless the question asks for one metric.

3. Add schema context hard-gating with an escape hatch:
   - `student_depression`: "student depression", "دانشجویان افسردگی", "دیتاست اصلی دانشجو"
   - `student_habits_performance`: "habits", "عادت", "نمره امتحان"
   - `university_student_mental_health`: "university", "دانشگاهی", "متاهل", "مجرد دانشگاهی"
   - `mental_health_general`: "general", "دیتاست عمومی", "ریسک سلامت روان"
   - `workplace_mental_health_survey`: "workplace", "محیط کار", "survey محل کار"

   Escape hatch terms downgrade the lock to preferred context: `join`, `correlation`, `کنار هم`, `با شیوع جهانی`, `مقایسه با کشور`, `gap`, `cross-dataset`.

4. Fix validator false positives:
   - `AVG(...) OVER (...)` and other windowed aggregates must not require `GROUP BY`.
   - `GROUP BY` aliases produced from `CASE` expressions must be accepted for SQLite.
   - advisory shape warnings such as stable alias expectations must not trigger hard invalid SQL unless they would break execution or an explicit benchmark contract.

5. Add regression fixtures for the known 61.25% regressions:
   - `VTD-024`: `student_depression` diet distribution must use `dietary_habits`.
   - `VTD-090`: university CGPA/depression relation must stay on the university table.
   - `VTD-229`: risk-matrix template must not be shadowed by broad single-metric templates.

### 18.7b - One-Shot Deterministic Schema Surgeon

When validation returns `UNKNOWN_COLUMN`:

1. Run one deterministic patch attempt using contextual aliases.
2. Re-validate patched SQL.
3. If a mapped patch is applied and validation still fails, fail fast instead of starting a 5-attempt LLM retry loop.
4. If there is no contextual mapping, leave exactly one LLM repair slot and then stop. The `61.5%` full400 run showed that immediate no-mapping fail-fast reduced valid SQL without adding accuracy.

Initial contextual alias map:

| Context | Term | Replacement |
|---|---|---|
| `student_depression` | diet / رژیم غذایی | `dietary_habits` |
| `student_habits_performance` | diet / رژیم غذایی | `diet_quality` |
| `university_student_mental_health` | depression / افسردگی | `depression_diagnosis` |
| `student_depression` | depression / افسردگی | `depression_flag` |
| `mental_health_general` | depression / افسردگی | `depression_score` |

The surgeon must record these counters in attempts or benchmark metadata:

- `surgeon_invoked`
- `surgeon_patch_applied`
- `surgeon_patch_validated`
- `surgeon_fail_fast`
- `surgeon_deferred_to_single_retry`

### 18.7b2 - Corrective Regression Recovery

The first full400 run after 18.7b produced EX `61.5%`: `6` fixed, `5` regressed, net `+1`; valid SQL dropped to `92.25%`. Before retrieval ablation, apply one corrective pass that remains anti-overfit:

1. Add general deterministic templates for the five observed valid-result regression shapes:
   - top-N city counts in `student_depression`
   - treatment-seeking rate by `mental_health_risk`
   - workplace treatment rate by normalized `gender`
   - `internet_quality` distribution
   - `diet_quality` versus exam/mental-health/sleep performance
2. Adjust Template Safety Gate so colloquial "چه نسبتی" blocks count-only SQL but does not block AVG-based relationship SQL.
3. Re-run full400 with a distinct ablation id before any vector/reranker test.

### 18.7b5 - Failed154 Template Pack and Validator Fix (Quarantined Ablation)

The targeted `failed154` iteration is now solved as an iteration gate:

```text
artifact: results/benchmark/20260525_114648_agent_positive400_qwen2-5-coder-7b_phase18_7b5_failed154_template_pack154_validatorfix
evaluated: 154
failures: 0
execution_accuracy: 1.0
valid_sql_rate: 1.0
reliability_score: 154.0
unsafe_sql: 0
latency_ms_mean: 873.12
latency_ms_median: 845
latency_ms_p95: 1063
latency_ms_max: 1588
```

Implementation notes:

- Added pattern/schema-driven deterministic templates for all `154` previously failed cases from the 18.7b full400 artifact.
- Added a validator fix for a false-positive shape rejection where generic depression-risk ranking questions were incorrectly forced to `GROUP BY mental_health_risk`.
- The full400 follow-up with templates reached EX `377/400 = 94.25%`, but `324/400` cases bypassed LLM generation through deterministic templates and `23` previously correct cases regressed. This is not aligned with the target architecture.
- Decision: quarantine the large deterministic template pack as an ablation/debug baseline. The runtime default must keep `deterministic_templates=false` so the system remains AI/QIR/schema/retrieval driven.
- The final failed154 gate is useful for regression investigation only. It is selected from previous failures and must not be reported as full-system accuracy or generalization evidence.
- Full400 without deterministic templates plus holdout/paraphrase validation remain mandatory before declaring Phase 18.7 complete or claiming that the change is not overfit.

### 18.7c - Retrieval Ablation

Run retrieval changes in two separate ablations:

1. `18.7c1`: `use_vector=true`, no reranker.
2. `18.7c2`: `use_vector=true` plus multilingual reranker.

Preferred reranker: `BAAI/bge-reranker-v2-m3` or the local equivalent under `models/rerankers`.

Do not combine vector and reranker changes with template or surgeon changes in the same first-pass comparison.

### 18.7d - Reliability Gate Over Existing Multi-Candidate

Current benchmark already uses multi-candidate generation/adoption. Phase 18.7d should not be described as "turning on multi-candidate"; it should evaluate Reliability Gate / Semantic Critic over the existing multi-candidate outputs.

Compare:

- annotation-only gate
- routed gate actions
- semantic critic selection

Reliability-gate routing must remain behind a dedicated ablation flag until it improves EX, reliability score, and regression count on the same selected case set.

## Verification Plan

### Unit Tests

Run focused tests after 18.7a/18.7b:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_template_sql.py tests\tier1_unit\test_schema_linker.py tests\tier1_unit\test_sql_consistency_critic.py tests\tier1_unit\test_sql_rewriter_ast.py -q
```

Add or update tests for:

- template safety gate rejecting broad matches.
- `UNKNOWN_COLUMN` one-shot surgeon patching.
- windowed aggregates in `aggregation_validator.py`.
- `CASE ... AS alias` with `GROUP BY alias`.
- known regression fixtures: `VTD-024`, `VTD-090`, `VTD-229`.

### Full Unit Suite

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_template_sql.py tests\tier1_unit\test_prompt_builder.py tests\tier1_unit\test_intent_classifier.py tests\tier1_unit\test_safety_detector.py tests\tier1_unit\test_ambiguity_detector.py tests\tier1_unit\test_sql_consistency_critic.py tests\tier1_unit\test_sql_rewriter_ast.py tests\tier1_unit\test_schema_linker.py tests\tier1_unit\test_value_linker_disorder_columns.py tests\tier1_unit\test_graph_attempt_trace.py tests\tier1_unit\test_graph_retry_and_config.py tests\tier1_unit\test_retrieval.py tests\tier1_unit\test_aggregation_validator.py tests\tier1_unit\test_shape_validator.py -q
```

### Stepwise Benchmarks

All reported runs must use `--exclude-self`, no exact cache, and an ablation id that names the active phase.

18.7a:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 1000 --trace-level compact --ablation-id phase18_7a_template_safety_schema_validator_full400
```

18.7b:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 1000 --trace-level compact --ablation-id phase18_7b_one_shot_surgeon_failfast_full400
```

18.7b2:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 1000 --trace-level compact --ablation-id phase18_7b2_regression_recovery_bounded_unknown_full400
```

Fast gates before full400:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --path data\questions\special\phase18_7b_regressed5.json --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 100 --trace-level compact --ablation-id phase18_7b2_regressed5_smoke
```

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --path data\questions\special\phase18_7b_failed154.json --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 100 --trace-level compact --ablation-id phase18_7b5_failed154_template_pack154_validatorfix
```

These gates are iteration tools only. They are selected from prior failures and must not be used as final accuracy claims.

Next required full400 check after quarantining deterministic templates:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 300 --trace-level compact --ablation-id phase18_7c0_ai_pipeline_no_deterministic_templates_full400
```

Template-pack runs are allowed only with an explicit config that sets `features.deterministic_templates: true`, and must be labeled as template-ablation results.

### 18.7e - QIR/Shape Recovery Without Deterministic Templates

No-template baseline artifact:

`20260526_013554_agent_positive400_qwen2-5-coder-7b_phase18_7c0_ai_pipeline_no_deterministic_templates_nctx8192_full400`

Observed result: EX `134/400 = 33.5%`, valid SQL `94%`, failures `266`.

Regression analysis versus the `61.25%` baseline:

- Correct in both: `126`.
- Correct only in the `61.25%` baseline: `119`.
- Correct only in no-template: `8`.
- Main root cause: QIR carried empty `dimensions` and `metrics` for grouped/rate/comparison questions, so the LLM produced valid scalar SQL with the wrong analytical shape.

Implemented runtime-safe corrections:

- QIR planner now derives dimensions/metrics from schema links and text shape cues.
- Schema linking now prefers `student_depression` for student-depression analytical questions unless a stronger table context or cross-dataset escape hatch exists.
- Shape validator now rejects scalar outputs for grouped/table-shaped QIR, count-only SQL for rate questions, one-sided filters for two-sided comparisons, and single-column grouping for multi-dimensional requests.
- Retrieval scoring now uses inferred SQL skeleton tags, and graph retrieval sends a QIR-derived skeleton signature.
- Multi-candidate policy now triggers for QIR table-shaped metric/dimension requests.

Debug-only datasets generated from artifacts:

- `data/questions/special/phase18_7c0_failed266.json`
- `data/questions/special/phase18_7c0_lost119.json`

Focused next checks:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --path data\questions\special\phase18_7c0_lost119.json --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 100 --trace-level compact --ablation-id phase18_7e_lost119_qir_shape_repair
```

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --path data\questions\special\phase18_7c0_failed266.json --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 100 --trace-level compact --ablation-id phase18_7e_failed266_qir_shape_repair
```

Then rerun full400:

```powershell
$env:VTD_LLM_N_CTX="8192"
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 300 --trace-level compact --ablation-id phase18_7e_ai_pipeline_qir_shape_full400
```

18.7c1:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 0 --top-k 5 --use-vector --exclude-self --bootstrap-iterations 1000 --trace-level compact --ablation-id phase18_7c1_vector_only_full400
```

18.7c2:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 0 --top-k 5 --use-vector --reranker bge-reranker-v2-m3 --exclude-self --bootstrap-iterations 1000 --trace-level compact --ablation-id phase18_7c2_vector_bge_reranker_full400
```

18.7d:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 1000 --trace-level compact --ablation-id phase18_7d_reliability_gate_multicandidate_full400
```

If `--reranker` is not the actual CLI flag, use the project config flag that maps to `retrieval_reranker` and record it in the benchmark config.

## Acceptance Criteria

- Execution accuracy `>= 65%`.
- Valid SQL rate `>= 94%`.
- Regressions `<= 5` versus the 61.25% baseline artifact.
- Difficulty split:
  - Easy `>= 95%`
  - Medium `>= 72%`
  - Hard `>= 52%`
  - Complex `>= 35%`
- p95 latency `<= 65.1s` (`25%` below the 86.8s baseline).
- Unsafe SQL `= 0`.
- Holdout or paraphrase validation completed with no evidence of exact-cache style memorization.

## Exit Decision

If Phase 18.7 reaches the acceptance criteria, freeze zero/few-shot optimization and prepare QLoRA. If it misses `65%` but reduces latency and regressions, keep the architectural improvements and move QLoRA earlier rather than adding more broad templates.
