# PARS-SQL Paper 1 Reproducibility Notes

Last updated: 2026-07-05

## Environment

```powershell
cd D:\Project\ADHD-VTD
.\.venv\Scripts\python.exe --version
```

The current local generation model used by the recent runs is:

```text
models/generation/qwen2.5-coder-7b-instruct-q4_k_m.gguf
```

## Unit and Artifact Tests

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit tests\artifact -q
```

Latest recorded result:

```text
520 passed, 3 warnings
```

## Release Readiness Gate

Run before paper-facing packaging or final claim review:

```powershell
.\.venv\Scripts\python.exe scripts\check_release_readiness.py `
  --benchmark-artifact-dir <benchmark_artifact_dir> `
  --dual-policy-pair <benchmark_artifact_dir>=<dual_policy_artifact_dir> `
  --comparison-artifact-dir <multi_candidate_comparison_dir> `
  --candidate-review-dir <candidate_review_package_dir> `
  --judge-ablation-plan-dir <judge_ablation_plan_dir> `
  --judge-artifact-dir <judge_artifact_dir> `
  --include-standard-paper-docs `
  --paper-doc <paper_facing_markdown> `
  --promotion-doc docs\PARS_SQL_PAPER1_REPRODUCIBILITY.md `
  --fail-on-actionable-risks
```

Notes:

- The gate calls `scripts/verify_artifact.py` for benchmark and dual-policy
  evidence.
- When given `--judge-ablation-plan-dir`, the gate validates the judge ablation
  manifest/runbook and verifies the referenced baseline/adaptive benchmark
  artifacts without running live judges.
- When given `--judge-artifact-dir`, the gate validates authoritative judge
  metadata, counts, redaction policy, and cost/token metadata without calling a
  model.
- Direct calls to `build_dual_policy_evidence_package()` also verify benchmark
  and dual-policy inputs before writing paper-facing outputs.
- When given `--candidate-review-dir`, the gate validates that candidate
  adoption review packages are non-authoritative, not paper metrics, and do not
  export gold SQL, strict correctness labels, or benchmark mismatch labels.
- When given `--comparison-artifact-dir`, the gate validates that
  multi-candidate comparison artifacts include aggregate
  `candidate_diversity_summary`, `component_latency_summary`, and
  `latency_diagnostics` sections without case IDs, SQL text, gold SQL, or
  strict/semantic correctness labels. The gate also reports
  `promotion_status`, `promotion_eligible`, and `promotion_blockers` so
  diagnostic artifacts can pass validation while candidate-adoption promotion
  remains blocked until authoritative semantic/business evidence is available.
- Open risks in `docs/Risks.md` are counted and schema-validated but do not
  fail by default. Each open risk must include a blocker category, current
  guard, next action, and close condition.
- Use `--fail-on-actionable-risks` after local non-human remediation work.
- Use `--fail-on-open-risks` only for final submission packaging.
- Keep SQL-positive, behavioral, and semantic/business evidence separate.
- `--include-standard-paper-docs` adds the standard paper-facing docs,
  context-hub docs, prompt library, PyCharm AI Assistant rules, and generated
  paper evidence table to the paper-doc scan. Use extra `--paper-doc` arguments
  only for new paper-facing files outside that standard set.
- `--paper-doc` scans paper-facing prose, captions, and markdown tables for
  forbidden claims and mixed metric-family wording.
- Generated paper tables must include `dataset_hash`, `selected_cases_hash`,
  and artifact provenance. `scripts/verify_artifact.py` checks dataset hash
  drift when the artifact config records `dataset_path`.
- The gate scans `src/` and `scripts/` for direct SQLite execution paths
  outside the approved read-only DB helpers.
- `--promotion-doc` validates the artifact promotion registry below. A row can
  be paper-facing only if its status is explicit and non-final rows set
  `paper_metric_allowed=false`.

`--include-standard-paper-docs` currently covers:

- `docs\00_INDEX.md`
- `docs\01_RESEARCH_GRADE_ARCHITECTURE.md`
- `docs\02_LANGGRAPH_WORKFLOW_SPEC.md`
- `docs\03_PERSIAN_NLU_AND_SCHEMA_LINKING.md`
- `docs\04_RAG_CAG_AND_RETRIEVAL_DESIGN.md`
- `docs\05_SQL_GENERATION_VALIDATION_REFLEXION.md`
- `docs\06_EVALUATION_ABLATION_AND_PAPER_PLAN.md`
- `docs\07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md`
- `docs\08_PROJECT_STRUCTURE_AND_FILE_MAP.md`
- `docs\09_DATASET_AND_EVALUATION_FILES_GUIDE.md`
- `docs\10_FULL_DEVELOPMENT_ROADMAP_ZERO_TO_SOTA.md`
- `docs\11_SEMANTIC_BUSINESS_LOGIC_EVALUATION.md`
- `docs\DATASET_CARD.md`
- `docs\BENCHMARK_AND_TEST_GUIDE.md`
- `docs\PARS_SQL_PAPER1_IMPLEMENTATION_PLAN.md`
- `docs\PARS_SQL_PAPER1_RESULTS_SUMMARY.md`
- `docs\PHASE0_50Q_AUDIT_TEMPLATE.md`
- `docs\README.md`
- `docs\THREAT_MODEL.md`
- `docs\context-hub\*.md`
- `docs\paper\limitations.md`
- `CODEX_PROMPTS.md`
- `.codex\prompts\*.md`
- `.aiassistant\rules\*.md`
- `results\paper\20260520_phase16_a4_dual_policy_evidence\paper_evidence_table.md`

These checks validate claim wording, metric-family separation, table
provenance, and promotion-registry consistency. They do not promote any
diagnostic or pending-review artifact to a paper-final metric.
Prompt-library and PyCharm AI Assistant rule docs are scanned by the same
paper-doc gate for claim wording, metric-family separation, and paper-table
provenance.

## Paper Artifact Promotion Registry

This registry is a guardrail for paper-facing claims. It does not change any
recorded metric. It states whether an artifact is allowed to support a final
paper metric after the release gate has verified the corresponding files.

Status meanings:

- `paper_final`: eligible for paper metrics only after verification passes.
- `diagnostic_only`: engineering evidence only; never cite as final.
- `pending_review`: recorded for traceability, but not promoted yet.

| Scope | Artifact Type | Artifact Path | Evidence Family | Status | Paper Metric Allowed | Notes |
|---|---|---|---|---|---|---|
| main_local_no_template_positive400 | benchmark | results\benchmark\20260621_122748_paper1_main_local_no_templates_bounded | sql_positive | pending_review | false | Historical 400-case no-template run; re-promote only after current manifest/provenance verification passes. |
| semantic_openrouter_s400 | judge | results\judgments\paper1_main_semantic_openrouter_s400_split\merged_authoritative | semantic_business | pending_review | false | Authoritative live judge artifact exists, but final paper use remains separate from strict EX and awaits final review. |
| phase7_promptdiverse_adopt_spl10 | benchmark | results\benchmark\phase7_promptdiverse_adopt_spl10_20260627_044546 | sql_positive | diagnostic_only | false | SPL10 candidate-adoption diagnostic only; no paper metric promotion. |
| phase7_promptdiverse_shadow_spl10 | benchmark | results\benchmark\phase7_promptdiverse_shadow_spl10_20260627_044546 | sql_positive | diagnostic_only | false | SPL10 shadow diagnostic only; no paper metric promotion. |
| phase7_promptdiverse_shadow_spl15 | benchmark | results\benchmark\20260630_114130_phase7_promptdiverse_shadow_spl15_diagnostic | sql_positive | diagnostic_only | false | SPL15 shadow diagnostic only; no paper metric promotion. |
| phase7_promptdiverse_adopt_spl15 | benchmark | results\benchmark\20260630_115607_phase7_promptdiverse_adopt_spl15_diagnostic | sql_positive | diagnostic_only | false | SPL15 candidate-adoption diagnostic only; no paper metric promotion. |
| phase7_promptdiverse_shadow_spl15_runtime_guarded | benchmark | results\benchmark\20260701_001813_phase7_promptdiverse_shadow_spl15_runtime_guarded_diagnostic | sql_positive | diagnostic_only | false | Runtime-guarded SPL15 shadow diagnostic only; no paper metric promotion. |
| phase7_promptdiverse_adopt_spl15_runtime_guarded | benchmark | results\benchmark\20260701_003651_phase7_promptdiverse_adopt_spl15_runtime_guarded_diagnostic | sql_positive | diagnostic_only | false | Runtime-guarded SPL15 candidate-adoption diagnostic only; no paper metric promotion. |
| bounded_no_template_smoke | benchmark | results\benchmark\20260621_112756_paper1_main_local_no_templates_bounded_smoke | sql_positive | diagnostic_only | false | Smoke run only; never cite as main performance. |

## Phase 7 Candidate Diagnostic SPL15

Run only as diagnostic evidence, not as a paper metric:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\phase7_promptdiverse_shadow_spl15_diagnostic.yaml

.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\phase7_promptdiverse_adopt_spl15_diagnostic.yaml
```

Runtime-guarded variants are available for the next latency diagnostic. They
predeclare `multi_candidate_allowed_triggers` and
`multi_candidate_blocked_triggers` so candidate generation is limited by
runtime signals only, not by case IDs, gold SQL, or correctness labels. They
also declare `multi_candidate_extra_generation_budget_ms=60000` so extra
candidate generation can stop after a slow primary candidate and record that
budget decision in the trace:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\phase7_promptdiverse_shadow_spl15_runtime_guarded_diagnostic.yaml

.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\phase7_promptdiverse_adopt_spl15_runtime_guarded_diagnostic.yaml
```

After both artifacts exist, compare them:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_multi_candidate_ablation.py `
  <shadow_artifact_dir> `
  <adopt_artifact_dir> `
  --max-latency-p95-delta-ms 500 `
  --max-latency-mean-delta-ms 500 `
  --output-dir results\benchmark\phase7_promptdiverse_spl15_compare_<timestamp>
```

Then build and validate the non-authoritative review package:

```powershell
.\.venv\Scripts\python.exe scripts\build_candidate_adoption_review_package.py `
  <adopt_artifact_dir> `
  --output-dir results\benchmark\phase7_promptdiverse_spl15_review_<timestamp>

.\.venv\Scripts\python.exe scripts\check_release_readiness.py `
  --benchmark-artifact-dir <shadow_artifact_dir> `
  --benchmark-artifact-dir <adopt_artifact_dir> `
  --comparison-artifact-dir results\benchmark\phase7_promptdiverse_spl15_compare_<timestamp> `
  --candidate-review-dir results\benchmark\phase7_promptdiverse_spl15_review_<timestamp> `
  --promotion-doc docs\PARS_SQL_PAPER1_REPRODUCIBILITY.md
```

Rules:

- `paper_metric_allowed=false`.
- Do not tune prompts, validators, retrieval, or candidate scoring to selected
  case IDs.
- Keep strict SQL-positive diagnostics separate from semantic/business review.
- Review packages must redact gold SQL, execution-correct labels, and benchmark
  mismatch labels.

Current diagnostic artifacts from 2026-06-30:

- Shadow benchmark:
  `results\benchmark\20260630_114130_phase7_promptdiverse_shadow_spl15_diagnostic`
- Adoption benchmark:
  `results\benchmark\20260630_115607_phase7_promptdiverse_adopt_spl15_diagnostic`
- Matched comparison:
  `results\benchmark\phase7_promptdiverse_spl15_compare_20260630_latency_budget`
- Candidate review package:
  `results\benchmark\phase7_promptdiverse_spl15_review_20260630_timing_trace`

Current runtime-guarded diagnostic status:

- Guarded shadow config:
  `experiments\configs\phase7_promptdiverse_shadow_spl15_runtime_guarded_diagnostic.yaml`
- Guarded adoption config:
  `experiments\configs\phase7_promptdiverse_adopt_spl15_runtime_guarded_diagnostic.yaml`
- Latest guarded shadow artifact:
  `results\benchmark\20260701_001813_phase7_promptdiverse_shadow_spl15_runtime_guarded_diagnostic`
- Latest guarded adoption artifact:
  `results\benchmark\20260701_003651_phase7_promptdiverse_adopt_spl15_runtime_guarded_diagnostic`
- Latest guarded comparison artifact:
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget`
- Latest guarded candidate review package:
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_review_20260701_budget`
- Latest guarded judge-ablation plan:
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan`
- These artifacts are diagnostic-only and have not replaced any paper-final
  benchmark. The configs allow `complex_intent`, `validation_failed`,
  `missing_generated_sql`, and `execution_failed`, while blocking broad
  `difficulty_hint`, `complex_category`, and `low_intent_confidence` triggers.
  They also set `multi_candidate_extra_generation_budget_ms=60000` as a
  diagnostic latency control; it is not correctness or semantic/business
  evidence.
- The latest guarded artifacts passed `scripts\verify_artifact.py`; the guarded
  comparison passed `scripts\check_release_readiness.py --comparison-artifact-dir`
  with `latency_budget_exceeded=false`. The guarded candidate review package
  passed `scripts\check_release_readiness.py --candidate-review-dir` with
  `authoritative=false` and `paper_metric_allowed=false`. The guarded
  judge-ablation plan passed
  `scripts\check_release_readiness.py --judge-ablation-plan-dir`; it contains
  19 planned commands and 8 network-required live judge commands.
- The guarded judge-ablation run was executed on 2026-07-04. The four Qwen
  branches passed `scripts\check_release_readiness.py --judge-artifact-dir` as
  authoritative: baseline semantic 21/60 correct, baseline strict 7/60 correct,
  adaptive semantic 22/60 correct, and adaptive strict 7/60 correct. These
  semantic/business and strict-policy judge counts use their own judge
  denominators and are diagnostic-only, not final paper metrics.
- The four DeepSeek branches did not pass paper-facing authoritative judge
  validation. Provider parse errors were recorded in 21 baseline semantic rows,
  14 baseline strict rows, 8 adaptive semantic rows, and 11 adaptive strict rows.
  Those rows remain unpromoted provider failures, not correctness claims.
- A targeted DeepSeek rerun was executed on 2026-07-05 under
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments_rerun_20260704`.
  Original and rerun rows were merged under
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments_merged_20260705`
  with `scripts\merge_judge_artifacts.py --duplicate-policy prefer-authoritative`.
  The merged baseline strict DeepSeek artifact passes authoritative validation.
  The merged baseline semantic, adaptive semantic, and adaptive strict DeepSeek
  artifacts remain non-authoritative with 11, 1, and 2 provider parse-error rows,
  respectively. These provider failures are not correctness labels.
- A second targeted retry was executed on 2026-07-05 under
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments_retry2_20260705`.
  After merging retry2 under
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments_merged_retry2_20260705`,
  baseline strict DeepSeek, adaptive semantic DeepSeek, and adaptive strict
  DeepSeek pass authoritative validation. Baseline semantic DeepSeek remains
  non-authoritative with 59/60 authoritative rows and one provider parse-error
  row for `VTD-141`. Provider parse errors are counted separately from
  semantic/business correct and incorrect rows.
- A third targeted retry was executed on 2026-07-05 under
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments_retry3_20260705`.
  After merging retry3 under
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments_merged_retry3_20260705`,
  all four DeepSeek judge artifacts pass authoritative validation. The final
  retry3 merged baseline semantic DeepSeek branch has 60/60 authoritative
  judgments and no provider parse-error rows.
- The generated dual-policy ablation artifact at
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\ablation\multi_candidate_dual_policy_ablation`
  passed comparison artifact validation, but its acceptance status is `blocked`
  because complete semantic/business evidence is unavailable and a semantic
  regression blocker is present. It is diagnostic-only.
- A merged diagnostic dual-policy ablation artifact was generated at
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\ablation_merged_20260705\multi_candidate_dual_policy_ablation`.
  It passes comparison artifact validation, but remains diagnostic-only with
  `status=blocked`: baseline dual-policy evidence has 17 combined adjudication
  required rows, adaptive dual-policy evidence has 8, and a semantic-regression
  blocker remains. SQL-positive, semantic/business, and strict-policy judge
  counts use separate denominators and are reported separately.
- A retry2 merged diagnostic dual-policy ablation artifact was generated at
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\ablation_merged_retry2_20260705\multi_candidate_dual_policy_ablation`.
  It passes comparison artifact validation, but remains diagnostic-only with
  `status=blocked`: baseline dual-policy evidence has 8 combined adjudication
  required rows, adaptive dual-policy evidence has 6, and a semantic-regression
  blocker remains. SQL-positive, semantic/business, and strict-policy judge
  counts use separate denominators and are reported separately.
- A retry3 merged diagnostic dual-policy ablation artifact was generated at
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\ablation_merged_retry3_20260705\multi_candidate_dual_policy_ablation`.
  It passes comparison artifact validation, but remains diagnostic-only with
  `status=blocked`: all selected judge artifacts are authoritative, baseline
  dual-policy evidence has 7 combined adjudication-required rows, adaptive
  dual-policy evidence has 6, and a semantic-regression blocker remains.
  SQL-positive, semantic/business, and strict-policy judge counts use separate
  denominators and are reported separately.
- Budget traces were exported for 30/60 predictions on each side, matching the
  cases where adaptive multi-candidate generation was enabled. No case exhausted
  the 60000 ms extra-generation budget in this run.
- A guarded shadow run attempt at
  `results\benchmark\20260630_144844_phase7_promptdiverse_shadow_spl15_runtime_guarded_diagnostic`
  timed out before this extra-generation budget was added and produced only
  partial JSONL files: 2 partial predictions, 2 partial failures, and 2 partial
  attempts. `scripts\verify_artifact.py` rejects it with
  `SUMMARY_JSON_MISSING`; it is not a valid benchmark artifact, not a comparison
  input, and not citable.

Latest runtime-guarded diagnostic outcome, SQL-positive only:

- Same dataset hash and selected-case hash; 60 common cases, SPL15 balanced
  across four difficulty levels.
- Strict EX stayed unchanged at 9/54 attempted SQL-positive generated SQL.
- Conservative EX stayed unchanged at 9/56 SQL-positive cases including missing
  SQL.
- Valid SQL stayed unchanged; unsafe SQL stayed 0/60.
- Candidate policy activated for 30/60 cases and adoption selected 6
  non-primary candidates.
- The guarded candidate review package contains those 6 adopted non-primary
  cases only: 6/6 valid SQL, 0 unsafe SQL, gold/reference fields redacted,
  reviewer labels pending, and no paper-metric authorization.
- Aggregate candidate diversity: 30/60 cases generated two adaptive candidates;
  selected-candidate ranks were 8 primary, 6 non-primary, and 46 none.
- Acceptance status is `insufficient_semantic_evidence`: the explicit aggregate
  latency budget did not block adoption because p95 latency delta was -1145 ms
  against a +500 ms p95 budget and mean latency delta was -565.53 ms against a
  +500 ms mean budget. Semantic/business correctness is still unavailable and
  remains 0/0 for this diagnostic.
- Release-readiness validation reports
  `promotion_status=blocked_until_authoritative_semantic_evidence` with
  `promotion_eligible=false`; promotion blockers are semantic-evidence blockers,
  not SQL-positive or behavioral metrics.
- SQL-positive diagnostics, behavioral safety counts, and semantic/business
  evidence status use different denominators and are reported separately.

Previous unguarded SPL15 diagnostic outcome, SQL-positive only:

- Same dataset hash and selected-case hash; 60 common cases, SPL15 balanced
  across four difficulty levels.
- Strict EX stayed unchanged at 9/54 attempted SQL-positive generated SQL.
- Conservative EX stayed unchanged at 9/56 SQL-positive cases including missing
  SQL.
- Valid SQL improved from 39/54 to 40/54; unsafe SQL stayed 0/60.
- Candidate policy activated for 31/60 cases and adoption selected 6
  non-primary candidates.
- Aggregate candidate diversity: 31/60 cases generated two adaptive
  candidates; selected-candidate ranks were 9 primary, 6 non-primary, and 45
  none.
- Aggregate candidate issue outcomes are SQL-positive diagnostics only. The
  current comparison has 33 cases without a candidate issue code and 2 cases
  with multiple issue-code memberships. `NO_VIABLE_CANDIDATES` appears in 16
  issue memberships, all remained wrong under strict EX, and contains the only
  aggregate valid-SQL regression membership. `SINGLE_VIABLE_CANDIDATE` appears
  in 7 issue memberships, selected 6 non-primary candidates, and contains the 2
  aggregate valid-SQL improvements; strict EX still stayed unchanged overall.
- Acceptance status is `blocked`: the explicit aggregate latency budget blocks
  adoption because p95 latency delta is +638 ms against a +500 ms p95 budget.
  Mean latency delta is +332.47 ms against a +500 ms mean budget and remains
  within budget. Semantic/business correctness is not available and remains 0/0
  for this diagnostic.
- Release-readiness validation reports this as
  `promotion_status=blocked_until_authoritative_semantic_evidence` with
  `promotion_eligible=false`; promotion blockers include
  `acceptance_status_blocked`, `latency_budget_exceeded`, and
  `semantic_evidence_unavailable`. This is a candidate-adoption promotion
  blocker, not a SQL-positive or semantic/business metric.
- Adoption increased latency modestly in this rerun: mean delta +332.47 ms,
  median delta +425.5 ms, and p95 delta +638 ms. No adaptive latency exceeded
  the 60000 ms high-latency diagnostic threshold.
- The aggregate-only `latency_regression_summary` reports
  `status=latency_regression_detected` because p95 and mean latency increased.
  In the per-case latency-delta distribution, mean delta is +332.467 ms,
  median delta is +416.5 ms, and p95 delta is +2127 ms. This is runtime
  triage only, not a SQL-positive or semantic/business correctness metric.
- Aggregate latency diagnostics use no case IDs, gold SQL, generated SQL text,
  or strict/semantic correctness labels. The enabled multi-candidate group had
  31 cases with adaptive p95 33997 ms and p95 delta 2444 ms; the disabled group
  had 29 cases with adaptive p95 21213 ms and p95 delta 1322 ms.
- The highest aggregate latency-delta groups are `NO_VIABLE_CANDIDATES`
  (16 issue memberships, p95 delta 2792 ms) and `needs_review`/enabled
  multi-candidate groups (p95 delta 2444 ms). These are aggregate triage
  groups only and must not be used for case-specific tuning.
- Reliability-gate action latency breakdown is aggregate-only. In the current
  artifact: `answer` has 26 cases with p95 adaptive latency 26695 ms and p95
  delta 1142 ms; `needs_review` has 28 cases with p95 adaptive latency 33513 ms
  and p95 delta 2444 ms; `refuse_unsafe` has 3 cases with p95 adaptive latency
  372 ms. This remains a diagnostic runtime view, not a correctness claim.
- Component latency summary is recorded-component-only. In the current artifact,
  total pipeline p95 changed from 31069 ms to 31707 ms; attempt generation p95
  changed from 30217 ms to 30486 ms; attempt execution p95 changed from 38 ms
  to 32 ms; candidate execution p95 changed from 73 ms to 75 ms. Candidate
  verification timing was recorded for 31/60 cases on each side with integer
  millisecond p95 0 ms; reliability-gate timing was recorded for 58/60 cases on
  each side with integer millisecond p95 0 ms. These timings show no measurable
  millisecond-level overhead in this diagnostic run. The per-case component
  delta contributor summary points first to attempt generation (p95 delta
  2347 ms), then total pipeline latency (p95 delta 2127 ms); they are not a
  semantic/business correctness signal.
- SQL-positive diagnostics, behavioral safety counts, and semantic/business
  evidence status use different denominators and are reported separately.

These numbers are diagnostic-only engineering evidence. They must not be moved
to final paper metrics without separate authoritative semantic/business review
and promotion-registry approval.

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

Validation status:

- `scripts\check_release_readiness.py --judge-artifact-dir` passes for
  `results\judgments\paper1_main_semantic_openrouter_s400_split\merged_authoritative`.
- This validates judge artifact metadata, row counts, redaction policy, and
  cost/token metadata only. Final paper use remains separate from strict EX and
  still awaits final review/promotion.

## Pending Reproducibility Items

- Optional clean paraphrase holdout for stronger anti-overfit claims.
- Optional human spot-check of a sample of the 400 OpenRouter semantic/business judgments before final paper submission.
