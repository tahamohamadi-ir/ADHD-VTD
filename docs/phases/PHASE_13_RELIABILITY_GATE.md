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
tests/tier1_unit/test_reliability_gate.py
tests/tier1_unit/test_reliability_gate_analysis.py
tests/tier1_unit/test_sql_consistency_critic.py
scripts/run_benchmark.py
scripts/analyze_reliability_gate_artifact.py
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

Fields not yet present in graph state:

```text
candidate_sqls
selected_candidate_id
reliability
candidate_consistency
```

That means Phase 13 can safely run the current gate as a benchmark annotation, but multi-candidate routing still needs explicit state fields and graph nodes.

Inspected benchmark prediction signals:

```text
scripts/run_benchmark.py::agent_prediction
```

The benchmark prediction record contains evaluation labels such as `execution_correct`, `ok`, `gold_sql`, and `error`. These are retained for benchmark reporting, but the gate contract treats them as disallowed runtime decision signals. The gate receives a separate runtime-style `gate_record` with `execution_result`, `validation_issues`, retry metadata, safety/intent signals and consistency issues.

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
- exhausted validation/execution failures -> `needs_review`
- exhausted hard question/SQL consistency failures -> `needs_review`
- empty execution result -> `needs_review` by default
- semantic judge incorrect/unresolved -> `needs_review`
- semantic correct plus strict-reference mismatch -> `answer` with `strict_reference_mismatch` warning
- validated and executed non-empty SQL -> `answer`

## Anti-Overfit Policy

This gate was tested with synthetic records and general artifact-shaped records only. It is not tuned to A4 case IDs such as `VTD-300`, and it must not be changed to special-case any benchmark ID.

The SQL consistency critic checks broad obligations only, such as rate questions requiring rate computation, above/below-average filters requiring an AVG threshold, change questions requiring an explicit change measure, and quartile/percentile questions requiring a binning construct. It must not encode reference SQL templates, benchmark IDs, or exact-gold output columns.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\tier1_unit\test_reliability_gate.py `
  tests\tier1_unit\test_sql_consistency_critic.py `
  -vv --tb=short
```

Result:

```text
18 passed for the focused gate/critic subset.
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

- Add broader artifact analysis for gate actions, false abstention risk, and critic false positives.
- Add a stronger general signal for valid-but-wrong-SQL cases before any routing change. Options: judge consensus, multi-candidate consistency, or a richer semantic/shape critic output.
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
