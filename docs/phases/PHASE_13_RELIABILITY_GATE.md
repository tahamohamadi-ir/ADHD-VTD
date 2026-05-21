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
tests/tier1_unit/test_reliability_gate.py
tests/tier1_unit/test_reliability_gate_analysis.py
tests/tier1_unit/test_sql_consistency_critic.py
tests/tier1_unit/test_candidate_consistency.py
tests/tier1_unit/test_multi_candidate_policy.py
tests/tier1_unit/test_multi_candidate_ablation.py
tests/tier1_unit/test_multi_candidate_graph_node.py
scripts/run_benchmark.py
scripts/analyze_reliability_gate_artifact.py
scripts/analyze_multi_candidate_ablation.py
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

- Add broader artifact analysis for gate actions, false abstention risk, critic false positives, and future candidate-consistency disagreements.
- Add graph nodes for adaptive multi-candidate generation. It should stay disabled for simple/confident questions and only activate on the policy triggers.
- The policy node is present; the next missing graph work is actual candidate generation/execution when the policy is enabled.
- Add a stronger general signal for valid-but-wrong-SQL cases before any routing change. Options: judge consensus, adaptive multi-candidate consistency, or a richer semantic/shape critic output.
- Only after annotation evidence is stable, decide whether graph routing should use the gate to change final behavior.
- Keep fixed test blocked until dev behavior, leakage limitations, and reliability are stable.

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

## Multi-Candidate A/B Comparison Tooling

Before actual candidate generation is enabled, the project now has an artifact-backed comparison scaffold:

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
