# Phase 13 - Reliability Gate, Multi-Candidate, Abstention

Status: In progress.

## Scope

Phase 13 adds a conservative decision layer that decides whether a generated result should be answered, retried, clarified, reviewed, or refused.

The gate is intentionally not case-ID aware. It must not use gold SQL, exact execution-match labels, benchmark case IDs, or hand-written exceptions for known failures. Runtime decisions are based on general signals only.

## Current Implementation

Implemented files:

```text
src/evaluation/reliability_gate.py
src/evaluation/reliability_gate_analysis.py
src/evaluation/sql_consistency_critic.py
src/evaluation/candidate_consistency.py
src/evaluation/multi_candidate_policy.py
src/evaluation/multi_candidate_ablation.py
src/evaluation/multi_candidate_series_report.py
tests/tier1_unit/test_reliability_gate.py
tests/tier1_unit/test_reliability_gate_analysis.py
tests/tier1_unit/test_sql_consistency_critic.py
tests/tier1_unit/test_candidate_consistency.py
tests/tier1_unit/test_multi_candidate_policy.py
tests/tier1_unit/test_multi_candidate_ablation.py
tests/tier1_unit/test_multi_candidate_series_report.py
tests/tier1_unit/test_multi_candidate_graph_node.py
scripts/run_benchmark.py
scripts/analyze_reliability_gate_artifact.py
scripts/analyze_multi_candidate_ablation.py
scripts/build_multi_candidate_series_report.py
scripts/plan_dual_policy_judge_ablation.py
src/evaluation/ablation_flags.py
```

The first implementation is annotation-only in benchmark agent mode:

```text
feature flag: reliability_gate
record fields:
  reliability_gate
  reliability_gate_action
  reliability_gate_reason
  reliability_gate_warnings
  sql_consistency_critic
  sql_consistency_issue_count
```

It does not yet overwrite `actual_action`, `final_answer`, or graph routing. This is deliberate: first we need artifact-backed visibility before changing user-facing behavior.

## Graph State and Benchmark Signals

Inspected runtime state:

```text
src/graph/state.py
```

The current `VTDState` already exposes the runtime signals needed for the standalone gate:

```text
raw_question / normalized_question
intent / intent_confidence
should_generate_sql
safety_label
needs_clarification
generated_sql
attempts
retry_count / max_retries
validation_errors
execution_result / execution_error
final_answer / explanation
ablation_config
```

New inactive-by-default graph state fields:

```text
candidate_sqls
selected_candidate_id
candidate_consistency
multi_candidate_policy
reliability
```

That means Phase 13 can safely preserve reliability/multi-candidate annotations in graph state and benchmark artifacts without changing latency or routing. Multi-candidate routing still needs explicit graph nodes before it can generate extra SQL.

Latency policy: multi-candidate generation must not run for every question. The project now has a standalone adaptive policy in `src/evaluation/multi_candidate_policy.py`. Default behavior is one candidate for simple/confident questions and at most two candidates for adaptive triggers such as retry/validation failure, execution failure, low intent confidence, complex dashboard/category hints, or hard/complex metadata hints when available. This policy only decides whether extra candidates are worth the cost; it does not generate extra SQL by itself.

Graph policy node:

```text
src/graph/nodes/base_nodes.py::plan_multi_candidate
```

The node records the adaptive policy decision in `VTDState.multi_candidate_policy`. It is annotation-only: it does not call the LLM, does not generate extra SQL, and does not change graph routing. The workflow routes both initial generation and retry generation through this node so the policy can observe retry/validation-failure conditions.

Inspected benchmark prediction signals:

```text
scripts/run_benchmark.py::agent_prediction
```

The benchmark prediction record contains evaluation labels such as `execution_correct`, `ok`, `gold_sql`, and `error`. These are retained for benchmark reporting, but the gate contract treats them as disallowed runtime decision signals. The gate receives a separate runtime-style `gate_record` with `execution_result`, `validation_issues`, retry metadata, safety/intent signals and consistency issues.

Benchmark predictions now preserve graph-provided reliability fields when present:

```text
candidate_sqls
selected_candidate_id
candidate_consistency
multi_candidate_policy
reliability
```

## Decision States

```text
answer
retry
ask_clarification
needs_review
refuse_unsafe
```

## Runtime Signals

Allowed runtime-style inputs:

```text
safety_label
intent
intent_confidence
needs_clarification
should_generate_sql
generated_sql/sql presence
validation_issues / validation_errors / valid_sql
execution_result
execution_error
retry_count
max_retries
optional semantic/strict judge labels when already present
question/SQL consistency issues from `src/evaluation/sql_consistency_critic.py`
```

Explicitly disallowed for runtime decision logic:

```text
case_id-specific rules
gold_sql
execution_correct
result_match
ok
known benchmark ID lists
manual correction of labels
```

## Current Rules

- unsafe request or unsafe SQL signal -> `refuse_unsafe`
- low intent confidence or explicit clarification flag -> `ask_clarification`
- missing SQL, validation failure, or execution failure before retry limit -> `retry`
- hard question/SQL consistency failure before retry limit -> `retry`
- hard multi-candidate consistency disagreement before retry limit -> `retry`
- exhausted validation/execution failures -> `needs_review`
- exhausted hard question/SQL consistency failures -> `needs_review`
- exhausted hard multi-candidate consistency disagreements -> `needs_review`
- empty execution result -> `needs_review` by default
- semantic judge incorrect/unresolved -> `needs_review`
- semantic correct plus strict-reference mismatch -> `answer` with `strict_reference_mismatch` warning
- validated and executed non-empty SQL -> `answer`

## Anti-Overfit Policy

This gate was tested with synthetic records and general artifact-shaped records only. It is not tuned to A4 case IDs such as `VTD-300`, and it must not be changed to special-case any benchmark ID.

The SQL consistency critic checks broad obligations only, such as rate questions requiring rate computation, above/below-average filters requiring an AVG threshold, change questions requiring an explicit change measure, and quartile/percentile questions requiring a binning construct. It must not encode reference SQL templates, benchmark IDs, or exact-gold output columns.

Candidate consistency compares candidate SQL signatures and optional result hashes only. It must not use gold SQL, benchmark case IDs, `execution_correct`, `result_match`, or paper labels. Candidate generation is not active in the graph yet.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\tier1_unit\test_reliability_gate.py `
  tests\tier1_unit\test_sql_consistency_critic.py `
  tests\tier1_unit\test_candidate_consistency.py `
  tests\tier1_unit\test_multi_candidate_policy.py `
  -vv --tb=short
```

Result:

```text
26 passed for the focused gate/critic/multi-candidate-policy subset.
```

Broader Phase 13/16 related verification:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\tier1_unit\test_reliability_gate.py `
  tests\tier1_unit\test_sql_consistency_critic.py `
  tests\tier1_unit\test_ablation_runner.py `
  tests\tier1_unit\test_dual_policy_packaging.py `
  tests\tier1_unit\test_llm_judge.py `
  tests\tier1_unit\test_judge_consensus.py `
  tests\tier1_unit\test_judge_agreement.py `
  -vv --tb=short
```

Result:

```text
46 passed
```

Compile check:

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  src\evaluation\reliability_gate.py `
  src\evaluation\sql_consistency_critic.py `
  src\evaluation\ablation_flags.py `
  scripts\run_benchmark.py
```

Result: passed.

## Remaining Work

- Broaden artifact analysis from small smoke slices to larger dev artifacts, including gate actions, false abstention risk, critic false positives, and future candidate-consistency disagreements.
- Run a larger controlled A/B benchmark before making any quality claim about adaptive multi-candidate generation.
- The policy node and feature-flagged candidate generation path are present; actual generation remains disabled unless `multi_candidate_generation=true` is set explicitly.
- Redesign the action policy for valid-but-risky SQL before any routing change. The current retry path can still end in valid-result-mismatch answers; next versions should evaluate `needs_review` or judge-backed adjudication for high-risk consistency failures.
- Only after annotation evidence is stable, decide whether graph routing should use the gate to change final behavior.
- Keep fixed test blocked until dev behavior, leakage limitations, and reliability are stable.
- Current decision: multi-candidate adoption remains blocked, and reliability-gate routing remains annotation-only until larger dev evidence shows reduced false answers without unacceptable latency/abstention regression.

## First Smoke Artifact

Config:

```text
experiments/configs/A7_reliability_gate_smoke.yaml
```

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\A7_reliability_gate_smoke.yaml `
  --output-dir results\benchmark\manual_phase13_reliability_gate_smoke
```

Artifact:

```text
results\benchmark\manual_phase13_reliability_gate_smoke
```

Result:

```text
evaluated=4
failures=3
execution_accuracy=0.25
valid_sql_rate=0.5
reliability_score=-0.5
unsafe_sql=0
gate_actions: needs_review=2, answer=2
```

Case-level gate decisions:

```text
VTD-237 -> needs_review / validation_failed_exhausted
VTD-027 -> answer / validated_executed_sql
VTD-343 -> answer / validated_executed_sql
VTD-300 -> needs_review / validation_failed_exhausted
```

Interpretation: this confirms annotation is being written into real benchmark predictions. It also exposes a real limitation: `VTD-343` is valid/executed but benchmark-wrong, and a runtime-only gate cannot detect that without a general semantic/consistency signal. Therefore the gate must remain annotation-only for now.

Artifact-backed gate analysis:

```text
analysis_dir: results\reliability_gate\20260520_phase13_gate_smoke_analysis
summary: results\reliability_gate\20260520_phase13_gate_smoke_analysis\reliability_gate_summary.json
cases: results\reliability_gate\20260520_phase13_gate_smoke_analysis\reliability_gate_cases.jsonl
report: results\reliability_gate\20260520_phase13_gate_smoke_analysis\reliability_gate_report.md
action_counts: needs_review=2, answer=2
posthoc_risk_counts: review_or_clarify_on_incorrect=2, answer_on_correct=1, answer_on_valid_result_mismatch=1
```

The `answer_on_valid_result_mismatch=1` finding is post-hoc analysis, not a runtime signal. It confirms the next general engineering need: add semantic/consistency evidence before the gate is allowed to route final answers.

## Consistency Critic Smoke Artifact

After adding `src/evaluation/sql_consistency_critic.py`, the same 4-case dev smoke was rerun.

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\A7_reliability_gate_smoke.yaml `
  --output-dir results\benchmark\manual_phase13_consistency_gate_smoke
```

Artifact:

```text
results\benchmark\manual_phase13_consistency_gate_smoke
```

Result:

```text
evaluated=4
failures=3
execution_accuracy=0.25
valid_sql_rate=0.5
reliability_score=-0.5
unsafe_sql=0
gate_actions: needs_review=2, answer=2
sql_consistency_issue_count: 0 for all four final predictions
```

Artifact-backed gate analysis:

```text
analysis_dir: results\reliability_gate\20260520_phase13_consistency_gate_smoke_analysis
action_counts: needs_review=2, answer=2
posthoc_risk_counts: review_or_clarify_on_incorrect=2, answer_on_correct=1, answer_on_valid_result_mismatch=1
```

Interpretation: the first critic did not introduce a hard false-positive on this smoke, but it also did not solve the valid-result-mismatch risk. The gate remains annotation-only. The next Phase 13 step should be multi-candidate or richer semantic consistency evidence, not case-specific critic tuning.

## Graph State Reliability Surface

The graph state now has inactive-by-default fields for future multi-candidate integration:

```text
candidate_sqls: []
selected_candidate_id: null
candidate_consistency: null
multi_candidate_policy: null
reliability: null
```

This is only an integration surface. No graph node currently generates extra candidates, so this change does not increase latency.

Focused verification:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\tier1_unit\test_graph_state_reliability_fields.py `
  tests\tier1_unit\test_reliability_gate.py `
  tests\tier1_unit\test_multi_candidate_policy.py `
  tests\tier1_unit\test_candidate_consistency.py `
  -vv --tb=short
```

Result:

```text
28 passed
```

Broader graph/reliability regression:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\tier1_unit\test_graph_state_reliability_fields.py `
  tests\tier1_unit\test_graph_routes.py `
  tests\tier1_unit\test_multi_candidate_policy.py `
  tests\tier1_unit\test_candidate_consistency.py `
  tests\tier1_unit\test_sql_consistency_critic.py `
  tests\tier1_unit\test_reliability_gate.py `
  tests\tier1_unit\test_reliability_gate_analysis.py `
  tests\tier1_unit\test_ablation_runner.py `
  -vv --tb=short
```

Result:

```text
40 passed
```

Compile check:

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  src\graph\state.py `
  src\evaluation\candidate_consistency.py `
  src\evaluation\multi_candidate_policy.py `
  src\evaluation\reliability_gate.py `
  scripts\run_benchmark.py
```

Result: passed.

## Policy Node Smoke Artifact

After adding `plan_multi_candidate`, a real 4-case dev smoke was run. This is artifact-backed evidence, not an inferred result.

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\A7_reliability_gate_smoke.yaml `
  --output-dir results\benchmark\manual_phase13_policy_node_smoke
```

Artifact:

```text
results\benchmark\manual_phase13_policy_node_smoke
```

Benchmark result:

```text
evaluated=4
failures=3
execution_accuracy=0.25
valid_sql_rate=0.75
reliability_score=-1.25
unsafe_sql=0
latency_ms mean=25962.25 median=19182.0 p95=54354.0
```

Policy annotation result:

```text
multi_candidate_policy enabled=2, disabled=2
trigger_counts: complex_intent=1, retry_in_progress=2, validation_failed=2
candidate_sqls: empty for all cases
```

Interpretation: the policy node correctly marks harder/retry cases as eligible for extra candidates while leaving simple/confident cases single-candidate. Since candidate generation is not active, this smoke does not prove multi-candidate quality improvement and should not be reported as such.

Artifact-backed analysis:

```text
results\reliability_gate\20260520_phase13_policy_node_smoke_analysis\reliability_gate_report.md
```

Analysis counts:

```text
action_counts: needs_review=1, answer=3
multi_candidate_counts: enabled=2, disabled=2
posthoc_risk_counts: review_or_clarify_on_incorrect=1, answer_on_correct=1, answer_on_valid_result_mismatch=2
```

This confirms the current gate still answers some valid-result-mismatch cases, so routing must remain annotation-only until candidate generation/consistency or judge-backed semantic signals are available.

## Feature-Flagged Candidate Generation

Adaptive candidate generation now exists behind an explicit feature flag:

```text
feature flag: multi_candidate_generation
config: experiments/configs/A7_reliability_gate_adaptive_multicandidate_smoke.yaml
implementation: src/graph/nodes/base_nodes.py::generate_sql
```

Default behavior is unchanged:

```text
multi_candidate_generation absent/false -> one LLM generation call
```

When explicitly enabled and `multi_candidate_policy.enabled=true`, the generation node:

```text
generates up to the policy candidate count
parses each candidate JSON
validates each candidate with the same validation/shape stack
executes only valid candidates to obtain runtime result hashes
records candidate_sqls
records selected_candidate_id
records candidate_consistency
passes the selected candidate through the existing parse/validate/execute path
```

Selection and consistency use only candidate SQL signatures and runtime result hashes. They do not use benchmark case IDs, gold SQL, exact execution-match labels, or hand-written failure exceptions.

Latency policy:

```text
The feature is disabled unless the config explicitly enables multi_candidate_generation=true.
The adaptive policy defaults to 2 candidates on triggered cases, not unbounded generation.
Simple/confident questions remain single-candidate.
```

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\tier1_unit\test_multi_candidate_graph_node.py `
  tests\tier1_unit\test_multi_candidate_policy.py `
  tests\tier1_unit\test_candidate_consistency.py `
  tests\tier1_unit\test_ablation_runner.py `
  -vv --tb=short
```

Result:

```text
18 passed
```

Compile check:

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  src\graph\nodes\base_nodes.py `
  src\evaluation\ablation_flags.py
```

Result: passed.

## Adaptive Multi-Candidate Smoke

A first real matched smoke was run after enabling the feature flag. This is a small diagnostic run, not paper-grade evidence.

Baseline artifact:

```text
results\benchmark\manual_phase13_policy_node_smoke
```

Adaptive artifact:

```text
results\benchmark\manual_phase13_adaptive_multicandidate_smoke
```

Adaptive command:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\A7_reliability_gate_adaptive_multicandidate_smoke.yaml `
  --output-dir results\benchmark\manual_phase13_adaptive_multicandidate_smoke
```

Adaptive result:

```text
evaluated=4
failures=3
execution_accuracy=0.25
valid_sql_rate=0.5
reliability_score=-0.5
unsafe_sql=0
latency_ms mean=50582.75 median=43167.5 p95=106646.0
```

Reliability analysis:

```text
results\reliability_gate\20260521_phase13_adaptive_multicandidate_smoke_analysis
```

A/B comparison:

```text
results\multi_candidate_ablation\20260521_phase13_policy_vs_adaptive_multicandidate_smoke_v2
```

A/B integrity:

```text
same_dataset_hash=true
same_selected_cases_hash=true
same_model=true
```

A/B deltas:

```text
execution_accuracy_delta=0.0
valid_sql_rate_delta=-0.25
unsafe_sql_delta=0.0
latency_p95_delta_ms=52292.0
candidate_issue_counts: NO_VIABLE_CANDIDATES=2
acceptance_status=blocked
```

Interpretation:

```text
This is a negative smoke. Adaptive multi-candidate generation did not improve EX, lowered valid SQL rate, and increased p95 latency substantially.
The feature must remain disabled for routing and quality claims.
Do not tune to the named case IDs; treat this as a general policy/selection failure around retry-triggered candidate generation with no viable candidates.
```

## Adaptive Redesign Smoke

After the first blocked smoke, the candidate path was made more conservative:

```text
No extra candidates are generated inside the retry loop.
No extra candidates are generated when prior validation/execution errors are already present.
Candidates are adopt-only-if-safe: consistency must pass and the selected candidate must be viable.
If candidates are invalid or disagree, the primary generation continues and candidate evidence remains review-only.
```

Verification:

```text
focused multi-candidate tests: 20 passed
compile check: passed
```

Second adaptive artifact:

```text
results\benchmark\manual_phase13_adaptive_multicandidate_smoke_v2
```

Second adaptive result:

```text
evaluated=4
failures=3
execution_accuracy=0.25
valid_sql_rate=0.75
reliability_score=-1.25
unsafe_sql=0
latency_ms mean=29431.0 median=16984.5 p95=74206.0
```

Second A/B report:

```text
results\multi_candidate_ablation\20260521_phase13_policy_vs_adaptive_multicandidate_smoke_v3
```

Second A/B deltas:

```text
execution_accuracy_delta=0.0
valid_sql_rate_delta=0.0
unsafe_sql_delta=0.0
latency_p95_delta_ms=19852.0
candidate_issue_counts: NO_VIABLE_CANDIDATES=1
acceptance_status=insufficient_semantic_evidence
```

Interpretation:

```text
The redesign removed the valid-SQL regression from the first adaptive smoke, but still did not improve EX and still increased p95 latency.
This is not ready for routing or paper claims.
Keep multi_candidate_generation disabled outside explicit experiments.
```

## Shadow-Only Candidate Evidence

Candidate adoption is now controlled separately:

```text
multi_candidate_generation=true -> generate/record candidate evidence when policy triggers.
multi_candidate_adoption=false -> default shadow-only mode; do not alter selected output.
multi_candidate_adoption=true -> experimental adoption mode; only allowed after A/B evidence.
```

Config:

```text
experiments/configs/A7_reliability_gate_adaptive_multicandidate_smoke.yaml
multi_candidate_adoption: false
```

Verification:

```text
focused graph/multi-candidate/ablation tests: 21 passed
compile check: passed
```

Shadow-only artifact:

```text
results\benchmark\manual_phase13_shadow_multicandidate_smoke
```

Shadow-only result:

```text
evaluated=4
failures=3
execution_accuracy=0.25
valid_sql_rate=0.75
reliability_score=-1.25
unsafe_sql=0
latency_ms mean=26450.0 median=17624.5 p95=61931.0
```

Shadow-only A/B report:

```text
results\multi_candidate_ablation\20260521_phase13_policy_vs_shadow_multicandidate_smoke
```

Shadow-only A/B deltas:

```text
execution_accuracy_delta=0.0
valid_sql_rate_delta=0.0
unsafe_sql_delta=0.0
latency_p95_delta_ms=7577.0
candidate_issue_counts: NO_VIABLE_CANDIDATES=1
acceptance_status=insufficient_semantic_evidence
```

Interpretation:

```text
Shadow-only avoids output regression on this smoke and has lower added latency than adoption mode.
It still does not improve EX and still leaves valid-result-mismatch answers, so it remains experimental evidence only.
```

## Cost-Benefit Series Report

The negative/neutral multi-candidate result is preserved as an artifact-backed finding for research reporting.

Tooling:

```text
src/evaluation/multi_candidate_series_report.py
scripts/build_multi_candidate_series_report.py
tests/tier1_unit/test_multi_candidate_series_report.py
```

Report:

```text
results\multi_candidate_ablation\20260522_phase13_multicandidate_cost_benefit_series_v5_dual_policy\multi_candidate_series_report.md
```

Summary:

```text
run_count=6
status_counts: blocked=2, insufficient_semantic_evidence=4
best_available_recommendation=do_not_adopt_candidate_adoption
```

Runs:

```text
1. adoption smoke: EX delta 0.0, valid SQL delta -0.25, p95 +52292ms, blocked.
2. safer adoption smoke: EX delta 0.0, valid SQL delta 0.0, p95 +19852ms, insufficient evidence.
3. shadow-only smoke: EX delta 0.0, valid SQL delta 0.0, p95 +7577ms, insufficient evidence.
4. shadow-only with candidate-evidence gate smoke: EX delta 0.0, valid SQL delta 0.0, p95 +48260ms, insufficient evidence.
5. dev-spl2 shadow-only after gate fix: EX delta 0.0, valid SQL delta 0.0, p95 -401707ms, insufficient evidence. The p95 decrease is dominated by a baseline outlier and is not a general speedup claim.
6. dev-spl2 shadow-only after dual-policy judging: EX delta 0.0, valid SQL delta 0.0, p95 -401707ms, blocked due semantic_user_question regression.
```

Paper interpretation:

```text
Multi-candidate generation is an explored but not yet cost-effective reliability intervention on this smoke slice.
Candidate adoption is blocked or unsupported because it did not improve execution accuracy, did not provide a reliable latency/value tradeoff, and in the dual-policy evidence can regress semantic-user-question correctness.
Shadow-only candidate evidence is safer than adoption, but remains diagnostic/review infrastructure until a larger dev-set ablation proves semantic gain without valid-SQL, strict-reference, safety, or latency regressions.
```

Anti-fake policy:

```text
The series report summarizes existing A/B artifacts only.
It does not run a model, execute SQL, edit predictions, infer missing semantic labels, or convert negative/null findings into success claims.
```

## Candidate Evidence Gate Smoke

A conservative gate rule was added after the shadow-only smoke:

```text
If multi_candidate_policy.enabled=true and candidate_count>1, but no candidate_sqls and no candidate_consistency evidence are present, return needs_review with reason candidate_evidence_missing_after_trigger.
```

This rule uses only runtime evidence availability. It does not use case IDs, gold SQL, benchmark correctness labels, or known failure lists.

Verification:

```text
focused reliability/multi-candidate tests: 25 passed
compile check: passed
```

Artifact:

```text
results\benchmark\manual_phase13_shadow_multicandidate_gate_evidence_smoke
```

Result:

```text
evaluated=4
failures=3
execution_accuracy=0.25
valid_sql_rate=0.75
reliability_score=-1.25
unsafe_sql=0
latency_ms mean=40036.5 median=23457.0 p95=102614.0
```

Reliability analysis:

```text
results\reliability_gate\20260521_phase13_shadow_multicandidate_gate_evidence_analysis
gate_actions: needs_review=2, answer=2
gate_reasons: validation_failed_exhausted=1, validated_executed_sql=2, candidate_evidence_missing_after_trigger=1
gate_warnings: multi_candidate_evidence_unavailable=1
posthoc_risk_counts: review_or_clarify_on_incorrect=2, answer_on_correct=1, answer_on_valid_result_mismatch=1
```

A/B comparison:

```text
results\multi_candidate_ablation\20260521_phase13_policy_vs_shadow_gate_evidence_smoke
same_dataset_hash=true
same_selected_cases_hash=true
same_model=true
execution_accuracy_delta=0.0
valid_sql_rate_delta=0.0
reliability_score_delta=0.0
unsafe_sql_delta=0.0
latency_p95_delta_ms=48260.0
candidate_issue_counts: NO_VIABLE_CANDIDATES=1
acceptance_status=insufficient_semantic_evidence
```

Interpretation:

```text
The rule correctly turns one expected-but-missing candidate-evidence situation into needs_review, reducing false-answer risk on this smoke.
It does not improve EX, valid SQL rate, or reliability score, and it increases p95 latency.
Therefore it is useful as conservative review instrumentation but not sufficient for routing, adoption, or paper-grade quality claims.
```

## Annotation-Only Gate Fix

The dev-spl2 analysis exposed a general contract bug: `plan_multi_candidate` can mark a case as eligible for extra candidates even when `multi_candidate_generation=false`. In that annotation-only mode, missing candidate evidence is expected and must not create a false `needs_review` action.

Fix:

```text
scripts\run_benchmark.py records multi_candidate_generation_enabled and multi_candidate_adoption_enabled.
src\evaluation\reliability_gate.py requires missing candidate evidence only when multi_candidate_generation_enabled=true.
```

Verification:

```text
tests\tier1_unit\test_reliability_gate.py
tests\tier1_unit\test_reliability_gate_analysis.py
tests\tier1_unit\test_multi_candidate_graph_node.py
result: 26 passed
compile check: passed
```

This is a general feature-flag contract fix. It does not use benchmark IDs, gold SQL, execution labels, or known failures.

## Dev-SPL2 A/B After Gate Fix

Configs:

```text
experiments\configs\A7_reliability_gate_dev_spl2.yaml
experiments\configs\A7_reliability_gate_shadow_multicandidate_dev_spl2.yaml
```

Artifacts:

```text
baseline: results\benchmark\manual_phase13_gate_dev_spl2_after_gate_fix
shadow: results\benchmark\manual_phase13_shadow_multicandidate_dev_spl2_after_gate_fix
baseline analysis: results\reliability_gate\20260521_phase13_gate_dev_spl2_after_gate_fix_analysis
shadow analysis: results\reliability_gate\20260521_phase13_shadow_multicandidate_dev_spl2_after_gate_fix_analysis
A/B: results\multi_candidate_ablation\20260521_phase13_gate_vs_shadow_multicandidate_dev_spl2_after_gate_fix
```

Results:

```text
baseline: evaluated=8, EX=0.375, valid_sql_rate=0.75, reliability_score=-0.5, unsafe_sql=0, p95=538185ms
shadow: evaluated=8, EX=0.375, valid_sql_rate=0.75, reliability_score=-0.5, unsafe_sql=0, p95=136478ms
same_dataset_hash=true
same_selected_cases_hash=true
same_model=true
```

A/B deltas:

```text
execution_accuracy_delta=0.0
valid_sql_rate_delta=0.0
reliability_score_delta=0.0
unsafe_sql_delta=0.0
latency_p95_delta_ms=-401707.0
semantic_evidence_available=false
acceptance_status=insufficient_semantic_evidence
```

Interpretation:

```text
Shadow-only candidate evidence still does not improve EX, valid SQL rate, or reliability on this larger dev slice.
The apparent p95 latency improvement is dominated by a baseline outlier and should be reported as latency variability, not a speedup claim.
Multi-candidate adoption remains blocked; shadow mode remains diagnostic only.
```

## Dual-Policy Judge Plan

The next step requires live OpenRouter judge calls. To keep this reproducible and avoid hand-written command drift, a planner was added:

```text
src\evaluation\judge_ablation_plan.py
scripts\plan_dual_policy_judge_ablation.py
tests\tier1_unit\test_judge_ablation_plan.py
```

Generated plan:

```text
results\judgments\20260522_phase13_gate_vs_shadow_dev_spl2_dual_policy_plan
manifest: RUN metadata and all planned commands
runbook: RUN_JUDGE_ABLATION.ps1
```

Scope:

```text
baseline artifact: results\benchmark\manual_phase13_gate_dev_spl2_after_gate_fix
shadow artifact: results\benchmark\manual_phase13_shadow_multicandidate_dev_spl2_after_gate_fix
judge models: qwen/qwen3.6-plus, deepseek/deepseek-v4-flash
judge policies: semantic_user_question, strict_reference
prediction scope: all 8 predictions from each artifact
post-processing: agreement -> consensus -> dual-policy report -> multi-candidate A/B with dual-policy dirs
```

Verification:

```text
tests\tier1_unit\test_judge_ablation_plan.py
tests\tier1_unit\test_multi_candidate_ablation.py
tests\tier1_unit\test_llm_judge.py
result: 24 passed
compile check: passed
```

Anti-fake statement:

```text
The planner writes commands and a manifest only.
It does not call OpenRouter, run a model, infer semantic labels, edit predictions, or create benchmark outcomes.
No semantic/strict correctness claim exists until RUN_JUDGE_ABLATION.ps1 is executed with a real API key and the resulting artifacts are inspected.
```

## Dual-Policy Dev-Spl2 A/B Result

The generated OpenRouter runbook was executed on the matched dev-spl2 baseline and shadow-only artifacts.

Final artifact:

```text
results\judgments\20260522_phase13_gate_vs_shadow_dev_spl2_dual_policy_plan\ablation\multi_candidate_dual_policy_ablation
```

Integrity checks:

```text
same_dataset_hash=true
same_selected_cases_hash=true
same_model=true
common_cases=8
```

Benchmark deltas:

```text
execution_accuracy_delta=0.0
valid_sql_rate_delta=0.0
reliability_score_delta=0.0
unsafe_sql_delta=0.0
latency_mean_delta_ms=-46472.37
latency_median_delta_ms=2627.0
latency_p95_delta_ms=-401707.0
```

The p95 decrease is still dominated by the baseline outlier and must be treated as latency variability, not a speedup claim.

Dual-policy counts:

```text
baseline semantic_user_question: correct=5, incorrect=3
baseline strict_reference: correct=3, incorrect=4, adjudication_required=1
baseline combined: both_correct=3, both_incorrect=2, semantic_correct_strict_incorrect=2, adjudication_required=1

shadow semantic_user_question: correct=4, incorrect=4
shadow strict_reference: correct=3, incorrect=4, adjudication_required=1
shadow combined: both_correct=3, both_incorrect=3, semantic_correct_strict_incorrect=1, adjudication_required=1
```

Multi-candidate evidence:

```text
activation_rate=0.625
policy enabled for 5/8 cases
generated two candidates for 3/8 cases
generated zero candidates for 5/8 cases
candidate_issue_counts: NO_VIABLE_CANDIDATES=1
```

Final acceptance:

```text
status=blocked
reason=semantic_user_question correctness regressed on one common case
```

Interpretation:

```text
Shadow-only multi-candidate evidence did not improve EX, valid SQL rate, reliability, unsafe SQL, or strict-reference correctness on this matched dev-spl2 slice.
It also reduced semantic_user_question correctness from 5/8 to 4/8 under the two-judge consensus artifacts.
Therefore multi-candidate adoption remains blocked, and shadow-only evidence remains diagnostic/review infrastructure only.
This negative result should be preserved for paper reporting as evidence that multi-candidate is not automatically cost-effective.
Do not tune to the named regression case; use the general finding to require broader semantic protection before any routing or adoption claim.
```

Anti-fake policy:

```text
This result is based on existing benchmark artifacts and live OpenRouter judge artifacts.
No prediction, SQL, judgment label, metric, or benchmark outcome was edited or inferred.
Partial, unjudged, and provider-error rows remain explicit in their source artifacts.
```

## Richer Semantic Critic

After the dual-policy A/B blocked multi-candidate adoption, Phase 13 moved back to a lower-latency reliability signal: strengthen the question/SQL critic so valid-but-wrong SQL is more likely to be retried or reviewed before final answer.

New general checks:

```text
1. Risk-profile questions with stress/sleep above/below-average thresholds must include result context averages:
   AVG(stress_level) and AVG(sleep_hours) must appear in the SELECT list, not only inside WHERE threshold subqueries.

2. Comparative questions such as "more", "higher", or Persian equivalents must include a grouped comparison or baseline.
   A SQL query that filters only one group, e.g. WHERE mental_health_risk = 'High', is not enough to answer "more than what?".

3. Above/below-average questions must compute the average threshold in WHERE/HAVING.
   AVG(...) in the SELECT list alone does not satisfy an average-threshold filter when the predicate uses fixed numbers.
```

Code:

```text
src\evaluation\sql_consistency_critic.py
src\evaluation\reliability_gate_analysis.py
scripts\analyze_reliability_gate_artifact.py --recompute-gate
```

Verification:

```text
tests\tier1_unit\test_sql_consistency_critic.py
tests\tier1_unit\test_reliability_gate.py
tests\tier1_unit\test_reliability_gate_analysis.py
result: 31 passed
compile check: passed
```

Post-hoc recompute artifacts:

```text
baseline: results\reliability_gate\20260522_phase13_gate_dev_spl2_richer_semantic_critic_recomputed
shadow:   results\reliability_gate\20260522_phase13_shadow_multicandidate_dev_spl2_richer_semantic_critic_recomputed
```

Recomputed baseline summary:

```text
action_counts: needs_review=2, answer=4, retry=2
posthoc_risk_counts:
  review_or_clarify_on_incorrect=2
  answer_on_correct=3
  retry_requested=2
  answer_on_valid_result_mismatch=1
```

Recomputed shadow summary:

```text
action_counts: needs_review=3, answer=4, retry=1
posthoc_risk_counts:
  review_or_clarify_on_incorrect=3
  answer_on_correct=3
  retry_requested=1
  answer_on_valid_result_mismatch=1
```

Interpretation:

```text
The richer critic reduces post-hoc answer-on-valid-result-mismatch risk on the existing dev-spl2 artifacts.
This is not a model-quality or routing claim because no benchmark was rerun and no prediction artifact was edited.
The next valid step is a fresh matched dev-spl2 benchmark with the richer critic active at runtime, then dual-policy review only if runtime risk improves without excessive retry/abstention cost.
```

Anti-overfit policy:

```text
The checks are based on explicit question/SQL obligations only.
They do not use case IDs, gold SQL, execution_correct, selected failure lists, result hashes, or judge labels.
```

### Runtime Reruns

First richer-critic runtime run:

```text
artifact: results\benchmark\manual_phase13_gate_dev_spl2_richer_semantic_critic
analysis: results\reliability_gate\20260522_phase13_gate_dev_spl2_richer_semantic_critic_runtime_analysis
A/B: results\reliability_gate\20260522_phase13_gate_dev_spl2_before_after_richer_semantic_critic

EX=0.375
valid_sql_rate=0.625
reliability_score=0.25
unsafe_sql=0
status=blocked
```

Interpretation: reliability improved versus the previous baseline, but valid SQL regressed, so this was not acceptable.

General shape-key fix:

```text
bug: mental_health_risk was falsely reported missing unless it appeared immediately after SELECT.
fix: the validator now checks the whole SELECT clause.
verification: focused shape/critic/gate tests -> 45 passed
```

Second runtime run after shape-key fix:

```text
artifact: results\benchmark\manual_phase13_gate_dev_spl2_richer_critic_after_shape_key_fix
analysis: results\reliability_gate\20260522_phase13_gate_dev_spl2_richer_critic_after_shape_key_fix_analysis
A/B: results\reliability_gate\20260522_phase13_gate_dev_spl2_before_after_richer_critic_shape_key_fix

EX=0.375
valid_sql_rate=0.875
reliability_score=-1.25
unsafe_sql=0
status=insufficient_semantic_evidence
```

Interpretation: valid SQL improved, but reliability worsened because three valid-result-mismatch cases were still answered. This is not a rollout claim.

Average-threshold recompute after the final critic tightening:

```text
artifact: results\reliability_gate\20260522_phase13_gate_dev_spl2_richer_critic_shape_key_fix_recomputed_avg_threshold
analysis_mode=recomputed_runtime_gate
action_counts: needs_review=1, answer=5, retry=2
posthoc_risk_counts:
  review_or_clarify_on_incorrect=1
  answer_on_correct=3
  retry_requested=2
  answer_on_valid_result_mismatch=2
verification: focused shape/critic/gate tests -> 46 passed
```

Interpretation: this recompute was more promising than the stored second run, but it was analysis-only and required a fresh runtime benchmark before any claim.

Final runtime run after the AVG-threshold critic fix:

```text
artifact: results\benchmark\manual_phase13_gate_dev_spl2_richer_critic_avg_threshold_final
analysis: results\reliability_gate\20260522_phase13_gate_dev_spl2_richer_critic_avg_threshold_final_analysis
A/B: results\reliability_gate\20260522_phase13_gate_dev_spl2_before_after_richer_critic_avg_threshold_final

EX=0.375
valid_sql_rate=0.875
reliability_score=-1.25
unsafe_sql=0
latency mean=17328.75ms
latency median=15082.0ms
latency p95=35112.0ms
```

Stored gate analysis:

```text
action_counts: needs_review=1, answer=5, retry=2
posthoc_risk_counts:
  review_or_clarify_on_incorrect=1
  answer_on_correct=3
  retry_requested=2
  answer_on_valid_result_mismatch=2
```

A/B versus `results\benchmark\manual_phase13_gate_dev_spl2_after_gate_fix`:

```text
same_dataset_hash=true
same_selected_cases_hash=true
same_model=true
execution_accuracy_delta=0.0
valid_sql_rate_delta=+0.125
reliability_score_delta=-0.75
unsafe_sql_delta=0.0
latency_p95_delta_ms=-503073.0
acceptance_status=insufficient_semantic_evidence
```

Case-level finding:

```text
VTD-343 -> retry / consistency_failed_retryable / valid SQL but result mismatch
VTD-141 -> retry / consistency_failed_retryable / valid SQL but result mismatch
VTD-300 -> answer / validated_executed_sql / valid SQL but result mismatch
VTD-078 -> answer / validated_executed_sql / valid SQL but result mismatch
```

Final interpretation:

```text
The richer critic improved valid SQL rate versus the earlier gate baseline and reduced latency in this run, but it did not improve execution accuracy and worsened the reliability score.
The p95 latency decrease is dominated by the earlier baseline outlier and must not be reported as a general speedup claim.
The gate still answers two valid-result-mismatch cases, so it is not safe to route final answers from this signal alone.
Reliability-gate routing remains disabled/annotation-only.
Next engineering direction should be conservative: valid-but-risky SQL should move to needs_review or judge-backed adjudication rather than automatic retry loops that can preserve or create wrong answers.
```

## Review-On-Consistency-Failure Policy

A conservative feature flag was added to test whether high-risk question/SQL consistency failures should be reviewed instead of retried:

```text
feature flag: reliability_gate_review_consistency_failures
config: experiments\configs\A7_reliability_gate_review_consistency_dev_spl2.yaml
implementation: src\evaluation\reliability_gate.py
```

Default behavior is unchanged. When the flag is false, consistency failures before the retry limit still return:

```text
retry / consistency_failed_retryable
```

When the flag is true, consistency failures return:

```text
needs_review / consistency_failed_review
```

Verification:

```text
tests\tier1_unit\test_reliability_gate.py
tests\tier1_unit\test_ablation_runner.py
tests\tier1_unit\test_reliability_gate_analysis.py
tests\tier1_unit\test_sql_consistency_critic.py
tests\tier1_unit\test_shape_validator.py
result: 51 passed
compile check: passed
```

Runtime artifact:

```text
artifact: results\benchmark\manual_phase13_gate_dev_spl2_review_consistency_failures
analysis: results\reliability_gate\20260522_phase13_gate_dev_spl2_review_consistency_failures_analysis
A/B vs original gate baseline: results\reliability_gate\20260522_phase13_gate_dev_spl2_before_after_review_consistency_failures
A/B vs AVG-threshold run: results\reliability_gate\20260522_phase13_gate_dev_spl2_avg_threshold_vs_review_consistency_failures
```

Benchmark result:

```text
evaluated=8
execution_accuracy=0.375
valid_sql_rate=0.875
reliability_score=-1.25
unsafe_sql=0
latency mean=17355.88ms
latency median=15256.5ms
latency p95=42649.0ms
```

Stored gate analysis:

```text
action_counts: needs_review=3, answer=5
reason_counts:
  validation_failed_exhausted=1
  validated_executed_sql=5
  consistency_failed_review=2
posthoc_risk_counts:
  review_or_clarify_on_incorrect=3
  answer_on_correct=3
  answer_on_valid_result_mismatch=2
```

A/B versus the original gate baseline:

```text
same_dataset_hash=true
same_selected_cases_hash=true
same_model=true
execution_accuracy_delta=0.0
valid_sql_rate_delta=+0.125
reliability_score_delta=-0.75
unsafe_sql_delta=0.0
acceptance_status=insufficient_semantic_evidence
```

A/B versus the AVG-threshold final runtime run:

```text
execution_accuracy_delta=0.0
valid_sql_rate_delta=0.0
reliability_score_delta=0.0
unsafe_sql_delta=0.0
latency_p95_delta_ms=+7537.0
acceptance_status=insufficient_semantic_evidence
```

Interpretation:

```text
The policy changes gate annotations as intended: two consistency failures move to needs_review instead of retry.
It does not change benchmark actual_action or final answer because Phase 13 routing is still disabled.
Therefore it is useful evidence for the next routing experiment, but it is not a quality improvement claim.
The two remaining answer_on_valid_result_mismatch cases show that critic coverage is still incomplete.
```

## Multi-Candidate A/B Comparison Tooling

Before actual candidate generation is used for claims or routing, the project now has an artifact-backed comparison scaffold:

```text
src/evaluation/multi_candidate_ablation.py
scripts/analyze_multi_candidate_ablation.py
tests/tier1_unit/test_multi_candidate_ablation.py
```

The tool compares two existing benchmark artifact directories:

```text
baseline A: current single-candidate graph with plan_multi_candidate annotation only
adaptive B: future adaptive candidate generation run
```

It records:

```text
same_selected_cases_hash
same_dataset_hash
same_model
execution_accuracy / valid_sql_rate / reliability_score / unsafe_sql deltas
latency mean/median/p95 deltas
multi_candidate activation rate
candidate_count distribution
candidate consistency issue counts
baseline-correct -> adaptive-wrong execution regressions
optional semantic_user_question and strict_reference label changes when dual-policy reports are supplied
```

Anti-fake policy:

```text
The comparison tool reads existing benchmark and optional dual-policy judgment artifacts only.
It does not run a model, execute SQL, edit predictions, infer missing semantic labels, or use case IDs/gold SQL as tuning rules.
```

Verification:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\tier1_unit\test_multi_candidate_ablation.py `
  tests\tier1_unit\test_multi_candidate_policy.py `
  tests\tier1_unit\test_candidate_consistency.py `
  -vv --tb=short
```

Result:

```text
13 passed
```

CLI self-check:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_multi_candidate_ablation.py `
  results\benchmark\manual_phase13_policy_node_smoke `
  results\benchmark\manual_phase13_policy_node_smoke `
  --output-dir results\multi_candidate_ablation\20260521_phase13_policy_node_self_check
```

Self-check result:

```text
same_selected_cases_hash=true
metric_deltas=0 for all benchmark metrics
multi_candidate activation_rate=0.5 from annotation-only policy
generated candidate count=0 for all cases
status=insufficient_semantic_evidence
```

Interpretation: this verifies the comparison pipeline only. It is not a multi-candidate quality claim because actual adaptive candidate generation is not enabled and no dual-policy A/B labels were supplied.

## Multi-Candidate Regression Plan

Before enabling actual multi-candidate generation, the project must prove that adaptive generation reduces errors rather than adding latency and false confidence.

Primary correctness policy:

```text
semantic_user_question: the generated answer/SQL answers the user's actual question.
strict_reference: stricter comparison against the reference/gold output contract.
```

Both must be reported separately. Semantic correctness is primary for user utility; strict-reference correctness is a secondary paper metric.

A/B design:

```text
A: single-candidate graph with plan_multi_candidate annotation only
B: adaptive candidate generation only when multi_candidate_policy.enabled=true
```

The comparison must use the same dataset split, selected cases, model, retrieval settings, and `--exclude-self` policy. The report must verify `same_selected_cases_hash=true`.

Required metrics:

```text
execution_accuracy
valid_sql_rate
reliability_score
unsafe_sql
semantic_user_question correctness
strict_reference correctness
latency mean/median/p95
multi_candidate activation rate
candidate_count distribution
candidate_result_hash_disagreement count
candidate table/filter/aggregation disagreement counts
baseline-correct -> adaptive-wrong regressions
```

Acceptance gate:

```text
unsafe_sql must not increase
semantic_user_question correctness must not drop on agreed judge labels
baseline-correct -> adaptive-wrong regressions must be explicitly reviewed
latency p95 must be reported and accepted explicitly
partial/unjudged/provider-error rows must not be counted as correct
```

Stop condition:

```text
If adaptive generation increases valid-result-mismatch or false-answer risk, keep it disabled and use candidate consistency only as a review signal.
```

Anti-overfit / anti-fake constraints:

```text
Do not tune prompts, validators, triggers, or candidate selection to named case IDs.
Do not infer missing semantic labels.
Do not edit predictions or benchmark outcomes.
Report only generated benchmark and judge artifacts.
```
