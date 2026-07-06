# PARS-SQL Open Risks

Last updated: 2026-07-05

This file tracks unresolved risks only. Resolved items should be removed or moved
to the relevant phase notes after the mitigation is implemented and verified.

This risk log is not a final paper table. Any paper table referenced by this
log must include `dataset_hash`, `selected_cases_hash`, and artifact provenance.

Open risks use one blocker category:

- `actionable_nonhuman`: local implementation, validation, or documentation work remains.
- `blocked_human_review`: final human review, reviewer labels, or reviewer sign-off is required.
- `blocked_external_api`: external judge/API access is required.
- `paper_promotion_pending`: final paper promotion/packaging is pending, but current non-human guards pass.

## R1. Candidate adoption still lacks authoritative semantic evidence

- Area: Phase 7 candidate generation and verifier
- Status: Open
- Blocker category: blocked_human_review
- Why it matters: The SPL10 and SPL15 prompt-diverse adoption diagnostics selected non-primary candidates, but review labels are still pending. These rows are not paper metrics and cannot support semantic/business correctness claims.
- Current guard: Pending imports do not create `dual_policy_cases.jsonl`, multi-candidate ablation treats them as missing semantic evidence, and `verify_artifact.py --dual-policy-dir` rejects them. `check_release_readiness.py --candidate-review-dir` also validates pending review packages without promoting them. The latest runtime-guarded package, `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_review_20260701_budget`, is explicitly `authoritative=false` and `paper_metric_allowed=false`. `check_release_readiness.py --comparison-artifact-dir` reports `promotion_eligible=false` and a semantic-evidence promotion blocker for comparison artifacts that lack authoritative semantic/business evidence.
- Guard command: `.\.venv\Scripts\python.exe scripts\check_release_readiness.py --candidate-review-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_review_20260701_budget --promotion-doc docs\PARS_SQL_PAPER1_REPRODUCIBILITY.md --fail-on-actionable-risks`
- Next action: Complete human review last, import labels with `--authoritative` only after review, then rerun dual-policy verification and comparison.
- Close condition: Human reviewer labels are imported as authoritative dual-policy evidence, verification passes, and candidate-adoption semantic/business evidence is promoted only through the registry.

## R2. SPL10/SPL15 shadow/adoption comparisons are diagnostic only

- Area: Multi-candidate shadow/adoption benchmark comparison
- Status: Open
- Blocker category: paper_promotion_pending
- Why it matters: Shadow and adoption SPL10/SPL15 runs had matching strict EX, but acceptance is not promotion-ready. SPL10 and SPL15 diagnostics remain blocked by missing semantic evidence. The previous unguarded SPL15 comparison was also blocked by the explicit latency budget, while the latest runtime-guarded SPL15 comparison passed the latency budget but still lacks semantic/business evidence. These runs are useful for engineering diagnostics, not final paper claims.
- Current guard: Comparison artifacts report `semantic_evidence_available=false` unless both dual-policy inputs are authoritative and complete. `check_release_readiness.py --comparison-artifact-dir` validates aggregate comparison sections without promoting them to paper metrics and exposes `promotion_status=blocked_until_authoritative_semantic_evidence`; latency blockers such as `latency_budget_exceeded` are reported separately when present.
- Guard command: `.\.venv\Scripts\python.exe scripts\check_release_readiness.py --benchmark-artifact-dir results\benchmark\20260701_001813_phase7_promptdiverse_shadow_spl15_runtime_guarded_diagnostic --benchmark-artifact-dir results\benchmark\20260701_003651_phase7_promptdiverse_adopt_spl15_runtime_guarded_diagnostic --comparison-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget --candidate-review-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_review_20260701_budget --promotion-doc docs\PARS_SQL_PAPER1_REPRODUCIBILITY.md --fail-on-actionable-risks`
- Next action: Keep SPL diagnostics out of final tables. Use only as diagnostic evidence unless authoritative semantic/business review is completed.
- Close condition: Diagnostic SPL rows stay `paper_metric_allowed=false`, or authoritative semantic/business evidence is added and promoted separately from strict EX.

## R3. Human review remains deferred by design

- Area: Candidate adoption and semantic/business correctness governance
- Status: Open
- Blocker category: blocked_human_review
- Why it matters: The project intentionally postponed human review to the final stage. Until then, any semantic correctness claim based on candidate adoption remains blocked.
- Current guard: Review package and import summaries set `paper_metric_allowed=false`; pending review cannot become dual-policy evidence. The runtime-guarded SPL15 review package contains only the 6 adopted non-primary cases, with reviewer labels pending and gold/reference fields redacted.
- Guard command: `.\.venv\Scripts\python.exe scripts\check_release_readiness.py --candidate-review-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_review_20260701_budget --fail-on-actionable-risks`
- Next action: At the final review stage, fill only reviewer columns, import labels, verify dual-policy artifacts, and document reviewer identity/scope.
- Close condition: Final human review is complete, reviewer scope is documented, and imported labels pass dual-policy verification without exposing gold/reference fields.

## R4. Judge ablation consensus still needs adjudication

- Area: Semantic judge ablation
- Status: Open
- Blocker category: blocked_human_review
- Why it matters: The runtime-guarded SPL15 judge ablation run completed, but
  the dual-model consensus evidence is not fully adjudicated. The Qwen and
  DeepSeek judge branches are now authoritative after retry3, but some Qwen vs
  DeepSeek disagreements remain `adjudication_required` in consensus and
  dual-policy outputs. These outputs are diagnostic only and cannot support
  final semantic/business paper claims until the disputed labels are resolved.
- Current guard: Plan artifacts do not call a model and are not cited as final
  results. `check_release_readiness.py --judge-ablation-plan-dir` validates
  the plan manifest/runbook and verifies the referenced baseline/adaptive
  benchmark artifacts without executing live judges. The runtime-guarded SPL15
  plan,
  `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan`,
  passed this gate with 19 planned commands, semantic and strict policies
  explicit, and 8 live judge commands marked network-required. After execution,
  the four Qwen judge artifacts pass `check_release_readiness.py
  --judge-artifact-dir` as authoritative. The first DeepSeek pass was
  incomplete: baseline semantic had 21 provider parse errors, baseline strict
  had 14, adaptive semantic had 8, and adaptive strict had 11. Targeted
  DeepSeek reruns were executed on 2026-07-05 and merged with
  `scripts\merge_judge_artifacts.py --duplicate-policy prefer-authoritative`.
  In retry3, all four merged DeepSeek artifacts pass authoritative validation.
  The retry3 merged dual-policy comparison artifact passes artifact-shape
  validation but reports `status=blocked`, because complete semantic/business
  evidence is unavailable and a semantic-regression blocker remains. The
  baseline dual-policy artifact has 7 combined adjudication-required rows; the
  adaptive dual-policy artifact has 6.
- Guard command: `.\.venv\Scripts\python.exe scripts\check_release_readiness.py --comparison-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\ablation_merged_retry3_20260705\multi_candidate_dual_policy_ablation --judge-ablation-plan-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan --judge-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments\baseline_semantic_qwen_qwen3_6-plus --judge-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments\baseline_strict_qwen_qwen3_6-plus --judge-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments\adaptive_semantic_qwen_qwen3_6-plus --judge-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments\adaptive_strict_qwen_qwen3_6-plus --judge-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments_merged_retry3_20260705\baseline_semantic_deepseek_deepseek-v4-flash --judge-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments_merged_retry3_20260705\baseline_strict_deepseek_deepseek-v4-flash --judge-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments_merged_retry3_20260705\adaptive_semantic_deepseek_deepseek-v4-flash --judge-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan\judgments_merged_retry3_20260705\adaptive_strict_deepseek_deepseek-v4-flash --promotion-doc docs\PARS_SQL_PAPER1_REPRODUCIBILITY.md --fail-on-actionable-risks`
- Next action: Keep the retry3 ablation diagnostic-only. At the final review
  stage, adjudicate the remaining consensus disagreements, or explicitly approve
  a new third-judge plan before any non-human adjudication. Keep
  semantic/business evidence separate from strict EX and behavioral evaluation.
- Close condition: All selected judge branches pass authoritative validation,
  consensus and dual-policy artifacts have complete policy labels, and any
  semantic/business metrics remain separate from strict EX.

## R5. External judge availability and reproducibility are not guaranteed

- Area: Semantic/business judge evaluation
- Status: Open
- Blocker category: blocked_external_api
- Why it matters: Paid or hosted judge providers can fail, change models, or return provider errors. Existing docs include examples of provider-error and mock judge artifacts that must not be promoted.
- Current guard: Mock authoritative judge output is rejected by
  `verify_artifact.py`. Judge ablation plans must mark live judge calls as
  network-required and keep offline analysis steps separate.
  `check_release_readiness.py --judge-artifact-dir` validates authoritative
  judge metadata, counts, redaction policy, and token/cost metadata before
  paper-facing judge evidence is accepted. The existing
  `results\judgments\paper1_main_semantic_openrouter_s400_split\merged_authoritative`
  artifact passes this gate for metadata, 400 judgment rows, redaction policy,
  and cost/token metadata, but final paper use remains pending review and
  promotion. The 2026-07-04 runtime-guarded SPL15 judge run confirms the
  provider risk: Qwen branches completed as authoritative, while DeepSeek
  branches required three targeted retries before all selected rows became
  authoritative.
- Guard command: `.\.venv\Scripts\python.exe scripts\check_release_readiness.py --judge-artifact-dir results\judgments\paper1_main_semantic_openrouter_s400_split\merged_authoritative --promotion-doc docs\PARS_SQL_PAPER1_REPRODUCIBILITY.md --fail-on-actionable-risks`
- Next action: Run live judges only when provider/model access is available,
  then validate the resulting judge artifacts and keep provider errors or parse
  errors outside correctness claims.
- Close condition: Chosen judge artifacts pass authoritative validation, provider errors are documented outside correctness counts, and paper promotion remains separate from SQL-positive metrics.

## R6. Paper reproducibility notes may become stale

- Area: Paper and reproducibility documentation
- Status: Open
- Blocker category: paper_promotion_pending
- Why it matters: `docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md` records artifact paths and metrics from earlier runs. New diagnostic Phase 7 artifacts must not be mixed into final paper tables unless explicitly verified and promoted.
- Current guard: Artifact rules prohibit citing smoke, dry-run,
  config-only, mock, failed, or placeholder artifacts as final results.
  `docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md` now includes a promotion registry,
  and `check_release_readiness.py --promotion-doc` rejects non-final rows with
  `paper_metric_allowed=true` and final rows that point at diagnostic artifacts.
  The paper-doc gate now passes for the top-level paper/evaluation docs
  `docs\00_INDEX.md` through
  `docs\11_SEMANTIC_BUSINESS_LOGIC_EVALUATION.md`, plus
  `docs\DATASET_CARD.md`, `docs\BENCHMARK_AND_TEST_GUIDE.md`,
  `docs\PARS_SQL_PAPER1_IMPLEMENTATION_PLAN.md`,
  `docs\PARS_SQL_PAPER1_RESULTS_SUMMARY.md`,
  `docs\PHASE0_50Q_AUDIT_TEMPLATE.md`, `docs\README.md`,
  `docs\THREAT_MODEL.md`, `docs\context-hub\*.md`,
  `docs\paper\limitations.md`, and
  `results\paper\20260520_phase16_a4_dual_policy_evidence\paper_evidence_table.md`
  and `.aiassistant\rules\*.md` after making behavioral, SQL-positive, and
  semantic/business metric-family separation explicit. Prompt-library claim
  scans also pass for `CODEX_PROMPTS.md` and `.codex\prompts\*.md`. These
  metric families use different denominators and are reported separately.
  `scripts\check_release_readiness.py --include-standard-paper-docs` now covers
  this standard paper-doc, prompt, context-hub, and AI-assistant rule set in one
  repeatable command. Default stale-reference checks also cover the prompt
  library, AI-assistant rule docs, `.agents\skills\*\SKILL.md`, and
  noncanonical context-hub path spellings.
- Guard command: `.\.venv\Scripts\python.exe scripts\check_release_readiness.py --benchmark-artifact-dir results\benchmark\20260701_001813_phase7_promptdiverse_shadow_spl15_runtime_guarded_diagnostic --benchmark-artifact-dir results\benchmark\20260701_003651_phase7_promptdiverse_adopt_spl15_runtime_guarded_diagnostic --comparison-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget --candidate-review-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_review_20260701_budget --judge-ablation-plan-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan --judge-artifact-dir results\judgments\paper1_main_semantic_openrouter_s400_split\merged_authoritative --include-standard-paper-docs --promotion-doc docs\PARS_SQL_PAPER1_REPRODUCIBILITY.md --fail-on-actionable-risks`
- Next action: Before paper submission, regenerate paper-facing tables only
  from verified artifact manifests, promote eligible rows to `paper_final`, and
  update reproducibility notes in one pass.
- Close condition: Final paper-facing tables are regenerated from verified manifests, promotion rows are final where allowed, and the release gate passes with no actionable open risks.

## R7. Behavioral evaluation remains separate and must stay out of SQL-positive EX

- Area: Benchmark metrics
- Status: Open
- Blocker category: paper_promotion_pending
- Why it matters: Behavioral expected-action accuracy is not strict SQL execution accuracy. Mixing them would overstate or distort model performance.
- Current guard: AGENTS.md explicitly forbids mixing behavioral cases with strict EX; focused regression includes action normalizer and metrics tests.
- Guard command: `.\.venv\Scripts\python.exe scripts\check_release_readiness.py --include-standard-paper-docs --promotion-doc docs\PARS_SQL_PAPER1_REPRODUCIBILITY.md --fail-on-actionable-risks`
- Next action: Keep behavioral tables separate from SQL-positive tables and include denominator definitions in all reports.
- Close condition: Paper-facing reports keep behavioral expected-action accuracy, SQL-positive strict execution accuracy, and semantic/business evidence as separate metric families with explicit denominators.

## R8. Prompt-diverse candidate selection may still overfit diagnostics

- Area: Prompt engineering and candidate verifier
- Status: Open
- Blocker category: blocked_human_review
- Why it matters: Prompt-diverse candidate adoption has only been evaluated on
  small SPL10/SPL15 diagnostic samples. It should not drive case-specific
  prompt, validator, or retrieval tuning.
- Current guard: Review package limitations say rows must not be used for
  case-specific tuning; no datasets or gold labels were modified. Candidate
  verifier and consistency code sanitize benchmark IDs, gold SQL, strict/semantic
  labels, and execution-correct labels before scoring or reporting runtime
  candidate signals. Candidate adoption review packages also redact gold SQL,
  execution-correct labels, and benchmark mismatch/error labels by default, and
  the release gate rejects packages that reintroduce those fields. The matched
  SPL15 shadow/adoption artifacts, comparison artifact, and runtime-guarded
  review package now exist and pass release-gate validation without
  paper-metric promotion,
  including `--comparison-artifact-dir` aggregate-leakage checks. The comparison
  artifact now includes aggregate `candidate_issue_outcome_summary` counters by
  candidate issue code, with no case IDs, SQL text, gold SQL, or semantic
  labels. Runtime trigger allowlists/denylists are now supported only as
  predeclared config parameters and are tested to avoid gold/case-label inputs.
- Guard command: `.\.venv\Scripts\python.exe scripts\check_release_readiness.py --comparison-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget --candidate-review-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_review_20260701_budget --fail-on-actionable-risks`
- Next action: Review SPL15 failures at aggregate level only. Defer row-level
  human review and authoritative semantic/business labels to the final review
  stage.
- Close condition: No case-specific tuning is performed from SPL diagnostics, final human review is complete, and any semantic/business claim is supported by authoritative evidence.

## R9. SPL15 adoption latency regression needs investigation

- Area: Candidate generation and verifier runtime
- Status: Open
- Blocker category: blocked_human_review
- Why it matters: The previous unguarded SPL15 adoption diagnostic kept strict
  EX unchanged and improved valid SQL rate, but p95 latency increased by 638 ms
  in the 2026-06-30 timing rerun. The latest runtime-guarded SPL15 diagnostic
  removed that aggregate latency-budget blocker, but latency remains
  model/runtime-sensitive and adoption still lacks semantic/business evidence.
- Current guard: SPL15 artifacts are diagnostic-only and `paper_metric_allowed`
  remains false. The comparison artifact records latency deltas separately from
  correctness and now includes aggregate `component_latency_summary` and
  `latency_diagnostics` without case IDs, SQL text, gold SQL, or
  strict/semantic correctness labels. Comparison artifacts also include
  aggregate `latency_regression_summary`, which flags p95/mean latency changes
  and ranks aggregate groups/components only. The previous unguarded budgeted
  comparison used explicit +500 ms p95 and +500 ms mean latency-delta budgets;
  acceptance was blocked because p95 delta was +638 ms. The latest
  runtime-guarded comparison uses the same budgets and reports
  `latency_budget_exceeded=false` with p95 delta -1145 ms and mean delta
  -565.53 ms. The release gate validates those aggregate sections through
  `--comparison-artifact-dir`, including recorded-component and adaptive
  reliability-gate action breakdowns. The current timing rerun records
  candidate-verification and reliability-gate timing as aggregate component
  diagnostics. Runtime-guarded SPL15 configs now exist to limit candidate
  generation to predeclared runtime triggers (`complex_intent`,
  `validation_failed`, `missing_generated_sql`, `execution_failed`) while
  suppressing broader `difficulty_hint`, `complex_category`, and
  `low_intent_confidence` triggers. They now also declare
  `multi_candidate_extra_generation_budget_ms=60000` so slow primary candidate
  generation can suppress extra candidate calls and record the budget decision
  in the trace. In the latest guarded pair, budget traces are present for 30/60
  predictions on each side and no case exhausted the 60000 ms extra-generation
  budget. A 2026-06-30 guarded shadow run attempt, produced before this
  extra-generation budget was added to the configs, timed out after producing
  only 2 partial predictions/failures/attempts; `verify_artifact.py` rejects the
  directory with `SUMMARY_JSON_MISSING`, so it is not citable and cannot be used
  as a comparison input.
- Guard command: `.\.venv\Scripts\python.exe scripts\check_release_readiness.py --benchmark-artifact-dir results\benchmark\20260701_001813_phase7_promptdiverse_shadow_spl15_runtime_guarded_diagnostic --benchmark-artifact-dir results\benchmark\20260701_003651_phase7_promptdiverse_adopt_spl15_runtime_guarded_diagnostic --comparison-artifact-dir results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget --fail-on-actionable-risks`
- Next action: Treat the runtime-guarded SPL15 pair as diagnostic evidence only.
  Do not promote adoption until authoritative semantic/business evidence exists.
  Continue monitoring aggregate latency on any larger rerun with the same
  explicit latency budget. Do not infer semantic correctness from these timings,
  and do not tune to individual case IDs or gold labels.
- Close condition: Larger or final-stage evidence documents the latency budget outcome, adoption is not promoted before authoritative semantic/business evidence, and latency remains reported separately from correctness.
