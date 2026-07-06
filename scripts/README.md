# PARS-SQL Scripts

Run scripts from the repository root:

```powershell
cd D:\Project\ADHD-VTD
```

## Core Commands

- `run_benchmark.py`: run retrieval, gold, or agent benchmarks and write
  artifact directories under `results/benchmark/`.
- `run_ablation.py`: run one or more experiment configs and write an ablation
  manifest.
- `verify_artifact.py`: verify benchmark artifacts before reporting or packaging.
- `check_release_readiness.py`: run a centralized paper/release readiness gate
  over artifact verification, dual-policy evidence, stale references, and
  explicit paper-claim docs.
- `package_dual_policy_evidence.py`: create paper-facing dual-policy evidence
  packages after artifact verification passes.
- `judge_benchmark_artifact.py`: run semantic/business or strict judge passes.
- `plan_dual_policy_judge_ablation.py`: write a judge ablation manifest and
  PowerShell runbook without calling external judges.
- `merge_judge_artifacts.py`: merge split judge artifacts.
- `analyze_multi_candidate_ablation.py`: compare baseline and adaptive
  multi-candidate artifacts without inventing semantic labels.
- `build_candidate_adoption_review_package.py`: export adopted non-primary
  candidate cases for later human review without gold SQL or strict correctness
  labels.
- `import_candidate_adoption_review_labels.py`: import completed reviewer labels
  into dual-policy artifacts without inferring missing labels.

## Artifact Verification

Verify a benchmark artifact:

```powershell
.\.venv\Scripts\python.exe scripts\verify_artifact.py <benchmark_artifact_dir>
```

Verify paper-facing semantic/business evidence:

```powershell
.\.venv\Scripts\python.exe scripts\verify_artifact.py `
  <benchmark_artifact_dir> `
  --dual-policy-dir <dual_policy_artifact_dir>
```

`package_dual_policy_evidence.py` runs this verification before writing a
package. Pending, non-authoritative, or unresolved dual-policy labels must fail.
The underlying `build_dual_policy_evidence_package()` API also verifies inputs,
so direct Python use follows the same guard.

Run the centralized release gate:

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

Open risks are counted and schema-validated but do not fail by default. Each
open risk in `docs/Risks.md` must include a blocker category, current guard,
next action, and close condition. Add `--fail-on-actionable-risks` after local
non-human remediation work; use `--fail-on-open-risks` only for final
submission packaging.

`--paper-doc` scans paper-facing prose, captions, and markdown table rows for
forbidden claims and mixed metric-family wording. Strict EX,
semantic/business correctness, and behavioral accuracy must be reported as
separate metric families with explicit denominator language. When the document
is a generated paper table, the gate also requires `dataset_hash`,
`selected_cases_hash`, and artifact provenance.

`--include-standard-paper-docs` adds the standard docs, context hub, prompt
library, PyCharm AI Assistant rules, and generated paper evidence table to the
same scan, so routine release checks do not depend on a long hand-written list
of `--paper-doc` arguments.

Default stale-reference checks also include `CODEX_PROMPTS.md`,
`.codex\prompts\*.md`, and `.aiassistant\rules\*.md`, so obsolete playbook or
rule references fail the same release gate. All `.agents\skills\*\SKILL.md`
files are included too, so skill instructions cannot drift silently.
Noncanonical context-hub paths such as lowercase `query-shape-contracts.md` and
`failure-patterns.md` also fail.

`--promotion-doc` validates a markdown artifact promotion registry. Only
`paper_final` rows can allow paper metrics, and final rows must pass artifact
verification. Rows marked `diagnostic_only` or `pending_review` must set
`paper_metric_allowed=false`.

`--candidate-review-dir` validates candidate adoption review packages as
non-authoritative diagnostics and rejects gold SQL, strict correctness labels,
or benchmark mismatch labels in JSONL/CSV review rows.

`--comparison-artifact-dir` validates diagnostic multi-candidate comparison
artifacts and rejects aggregate leakage of case IDs, SQL text, gold SQL, or
strict/semantic correctness labels.

The gate also scans `src/` and `scripts/` for direct SQLite connection or
execution calls outside the approved read-only DB paths. New SQL execution
features must go through `src/db/read_only_executor.py`.

When `--judge-ablation-plan-dir` is provided, the gate validates the plan
manifest/runbook and verifies the referenced baseline and adaptive benchmark
artifacts. It does not run live judges.

When `--judge-artifact-dir` is provided, the gate validates an authoritative
judge artifact and rejects mock, non-authoritative, incomplete, or metadata-
inconsistent judge evidence.

Current validated semantic/business judge artifact:

- `results\judgments\paper1_main_semantic_openrouter_s400_split\merged_authoritative`

This artifact passes `check_release_readiness.py --judge-artifact-dir` for
metadata, row-count, redaction, and cost/token consistency. It remains a
separate semantic/business evidence family and must not be mixed with strict EX.

## Candidate Diagnostics

Matched Phase 7 diagnostic configs:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\phase7_promptdiverse_shadow_spl15_diagnostic.yaml

.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\phase7_promptdiverse_adopt_spl15_diagnostic.yaml
```

Runtime-guarded variants for the next latency diagnostic:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\phase7_promptdiverse_shadow_spl15_runtime_guarded_diagnostic.yaml

.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\phase7_promptdiverse_adopt_spl15_runtime_guarded_diagnostic.yaml
```

The guarded configs predeclare runtime trigger filters:
`multi_candidate_allowed_triggers` keeps `complex_intent`,
`validation_failed`, `missing_generated_sql`, and `execution_failed`;
`multi_candidate_blocked_triggers` suppresses broad `difficulty_hint`,
`complex_category`, and `low_intent_confidence`. They also set
`multi_candidate_extra_generation_budget_ms=60000`, which stops extra candidate
generation after a slow primary candidate and records the decision in the trace.
These controls are diagnostic runtime parameters, not paper metrics and not
semantic/business evidence.
The partial guarded shadow attempt at
`results\benchmark\20260630_144844_phase7_promptdiverse_shadow_spl15_runtime_guarded_diagnostic`
is not a valid artifact; it contains only partial JSONL files and fails
`verify_artifact.py` with `SUMMARY_JSON_MISSING`.

Latest runtime-guarded SPL15 diagnostic artifacts:

- Shadow: `results\benchmark\20260701_001813_phase7_promptdiverse_shadow_spl15_runtime_guarded_diagnostic`
- Adoption: `results\benchmark\20260701_003651_phase7_promptdiverse_adopt_spl15_runtime_guarded_diagnostic`
- Comparison: `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget`
- Candidate review package: `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_review_20260701_budget`
- Judge-ablation plan: `results\benchmark\phase7_promptdiverse_spl15_runtime_guarded_compare_20260701_budget\judge_ablation_plan`

The runtime-guarded comparison is diagnostic-only: strict EX stayed unchanged
at 9/54, valid SQL stayed unchanged, unsafe SQL stayed 0/60, and the explicit
latency budget was not exceeded. Acceptance remains
`insufficient_semantic_evidence` because authoritative semantic/business review
is unavailable. Budget traces are present for the 30/60 predictions where
adaptive multi-candidate generation was enabled; no case exhausted the 60000 ms
extra-generation budget. The runtime-guarded review package is also
diagnostic-only and pending: it contains 6 adopted non-primary cases, sets
`authoritative=false` and `paper_metric_allowed=false`, and redacts gold SQL and
strict reference fields. The judge-ablation plan is a runbook only: it has 19
planned commands, separates semantic and strict judge policies, marks 8 live
judge commands as network-required, and creates no semantic/business metric
until the runbook is executed and artifacts pass verification.

The runtime-guarded judge-ablation run was executed on 2026-07-04. The four Qwen
branches pass authoritative judge-artifact validation. In the first DeepSeek
pass, all four branches were non-authoritative because provider parse errors
occurred. The generated dual-policy ablation artifact validates as a diagnostic
comparison, but its acceptance status is `blocked`, so it is not a paper metric
and must not be mixed with strict EX or behavioral evaluation.

Targeted DeepSeek reruns were executed on 2026-07-05 and merged with
`scripts\merge_judge_artifacts.py --duplicate-policy prefer-authoritative`.
After retry3, all four merged DeepSeek artifacts are authoritative. The retry3
merged dual-policy ablation artifact validates as diagnostic-only and remains
`blocked` because consensus and dual-policy evidence still contain
adjudication-required Qwen-vs-DeepSeek disagreements. These are not provider
parse errors and must not be converted into correctness labels without final
adjudication or an explicitly approved third-judge plan.

These runs are not paper metrics. Compare completed artifacts with
`analyze_multi_candidate_ablation.py`, then build a review package with
`build_candidate_adoption_review_package.py` and validate it through
`check_release_readiness.py --candidate-review-dir`.

Current SPL15 diagnostic artifacts:

- Shadow: `results\benchmark\20260630_114130_phase7_promptdiverse_shadow_spl15_diagnostic`
- Adoption: `results\benchmark\20260630_115607_phase7_promptdiverse_adopt_spl15_diagnostic`
- Comparison: `results\benchmark\phase7_promptdiverse_spl15_compare_20260630_latency_budget`
- Review package: `results\benchmark\phase7_promptdiverse_spl15_review_20260630_timing_trace`

The SPL15 comparison is diagnostic-only: strict EX remained 9/54, valid SQL
improved from 39/54 to 40/54, unsafe SQL stayed 0/60, and acceptance is
`blocked` because the explicit p95 latency budget was exceeded. Semantic
evidence is still unavailable.

The comparison summary includes aggregate-only `candidate_diversity_summary`,
`candidate_issue_outcome_summary`, `component_latency_summary`,
`latency_regression_summary`, and `latency_diagnostics` sections. Use those
sections for engineering review; do not tune from case IDs, gold SQL, generated
SQL text, or strict/semantic labels.
Validate the comparison artifact with
`check_release_readiness.py --comparison-artifact-dir`.
Current latency diagnostics also include
`by_adaptive_reliability_gate_action`, so runtime review can compare answer,
review, clarification, and refusal paths without row-level inspection.
`latency_regression_summary` reports aggregate runtime triage only. In the
current SPL15 comparison it flags increased p95/mean latency; top aggregate
signals are `NO_VIABLE_CANDIDATES`, `needs_review`, and enabled
multi-candidate groups, with attempt generation as the largest recorded
component-delta contributor.
The current comparison was built with `--max-latency-p95-delta-ms 500` and
`--max-latency-mean-delta-ms 500`; the p95 delta is +638 ms and blocks
acceptance, while the mean delta is +332.47 ms and remains within budget.
Component latency is recorded-component-only. New benchmark traces record
candidate-verification and reliability-gate timing explicitly. In the current
SPL15 comparison both are recorded with integer millisecond p95 0 ms; use this
only as aggregate runtime diagnostics, not as a semantic correctness signal.

## Benchmark Examples

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 20 --top-k 3
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset dev --sample 20
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --ablation-id full_trace
```

`retrieval` evaluates evidence retrieval only. `gold` is an executor and metric
sanity check, not a model result. `agent` runs the full workflow and requires a
valid local model path.

## Rules

- Never bypass the read-only executor.
- Do not modify datasets from scripts unless dataset version, hashes, docs, and
  manifests are updated together.
- Keep SQL-positive, behavioral, and semantic/business metrics separate.
- Do not cite smoke, dry-run, config-only, mock, failed, or placeholder artifacts
  as final results.
