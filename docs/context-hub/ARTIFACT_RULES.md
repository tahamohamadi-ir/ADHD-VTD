# Artifact Rules

This is the canonical short protocol for benchmark, artifact, reproducibility,
and paper-facing evidence governance. Use `docs/BENCHMARK_AND_TEST_GUIDE.md`
only when operational command detail is needed.

## Never cite as final result

Do not cite:

- smoke runs,
- partial runs,
- failed runs,
- config-only files,
- placeholder reranker runs,
- mock judge outputs,
- pilot judge if full judge exists,
- deterministic template pack as main model result.

## Evaluation family separation

Keep these families separate in reports, tables, and acceptance checks:

- SQL-positive evaluation: strict execution accuracy, conservative execution
  accuracy, valid SQL rate, invalid SQL count, missing SQL count, result
  mismatch count, unsafe SQL count, latency mean/p95.
- Behavioral evaluation: expected-action accuracy, safety rejection accuracy,
  clarification accuracy, abstention precision/recall, unsafe SQL count.
- Semantic/business evaluation: judge or human-review correctness, provider,
  model, prompt version, authoritative status, and human spot-check status.
- Metric-family policy: these families use different denominators and must be
  reported separately.

Never put behavioral cases in the strict EX denominator. Never combine strict EX
with semantic/business correctness.

Paper-facing prose, captions, and tables must also keep these families
separate. The release gate scans `--paper-doc` inputs and rejects segments that
mention multiple metric families without explicit separation language such as
`reported separately` or `different denominators`.

## Required files for a valid benchmark run

A valid run must include:

- config file
- predictions
- benchmark results
- summary json
- summary md
- failures if any
- manifest entry
- dataset hash
- selected cases hash
- model identity
- prompt version or prompt metadata when available
- git commit or reproducible run identifier when available

## Required consistency checks

The artifact verifier must check:

1. prediction count matches summary total
2. failure count matches summary failures
3. valid SQL count matches predictions
4. EX numerator/denominator matches predictions
5. unsafe SQL count matches predictions
6. config flags match summary
7. deterministic_templates flag is explicit
8. dataset hash is present
9. selected cases hash is present
10. run is not marked smoke unless cited as smoke
11. deterministic template usage is explicit
12. mock judges are not marked authoritative
13. placeholder rerankers are not cited as real rerankers
14. `dataset_path`, when present, still hashes to `dataset_hash`
15. source/scripts do not introduce direct SQL execution outside approved
    read-only DB paths

## Release verification command

Run the centralized release gate before paper-facing packaging:

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

Open risks are counted and schema-validated by default. Each open risk in
`docs/Risks.md` must include a blocker category, current guard, next action, and
close condition. Use `--fail-on-actionable-risks` after non-human remediation
work, and reserve `--fail-on-open-risks` for final submission packaging after
human review and external judge/API blockers are closed.

Use `--include-standard-paper-docs` to scan the current standard paper-facing
docs, context hub docs, prompt library, PyCharm AI Assistant rules, and the
generated paper evidence table in one repeatable release-gate command. Extra
`--paper-doc` values can still be added for new manuscripts or generated
tables.

Default stale-reference checks also cover `CODEX_PROMPTS.md`,
`.codex\prompts\*.md`, and `.aiassistant\rules\*.md` so obsolete prompt or rule
references fail before release packaging. All `.agents\skills\*\SKILL.md`
files are included too, so skill instructions cannot drift silently.
Noncanonical context-hub paths such as lowercase `query-shape-contracts.md` and
`failure-patterns.md` also fail.

The release gate also scans `src/` and `scripts/` for direct SQLite connection
or execution calls. New SQL execution paths must route through
`src/db/read_only_executor.py` or the approved read-only DB metadata helpers.

`--candidate-review-dir` validates candidate adoption review packages as
non-authoritative diagnostic artifacts and rejects gold/reference leakage.

`--comparison-artifact-dir` validates diagnostic multi-candidate comparison
artifacts, including aggregate `candidate_diversity_summary` and
`component_latency_summary` and `latency_diagnostics` sections, and rejects
aggregate leakage of case IDs, SQL text, gold SQL, or strict/semantic
correctness labels. Component latency summaries must distinguish recorded
components from components not present in the trace. Latency diagnostics must
include aggregate breakdowns by adaptive multi-candidate policy, adaptive
candidate SQL count, adaptive reliability-gate action, and candidate issue code.
The comparison validation output also reports `promotion_status`,
`promotion_eligible`, and `promotion_blockers`; diagnostic artifacts may pass
validation while still being blocked from candidate-adoption promotion until
authoritative semantic/business evidence is available.
New comparison artifacts may also include aggregate
`latency_regression_summary`, which reports only p95/mean latency-regression
signals, top aggregate latency groups, and recorded component contributors.
It must not include case IDs, SQL text, gold SQL, or strict/semantic labels.
If `analyze_multi_candidate_ablation.py` is run with
`--max-latency-p95-delta-ms` or `--max-latency-mean-delta-ms`,
`acceptance_checks.latency_budget` must record the explicit aggregate benchmark
budget, observed p95/mean deltas, exceeded dimensions, and whether acceptance
is blocked by `latency_budget_exceeded`.
`acceptance_checks.status` must be one of `blocked`,
`insufficient_semantic_evidence`, `needs_review`, or `eligible_for_review`.
`acceptance_checks.semantic_evidence_available` must be boolean, and
`acceptance_checks.blocker_reasons`, when present, must be a list of strings.

When `--promotion-doc` is supplied, the gate validates a markdown paper artifact
promotion registry with these columns:

- `Scope`
- `Artifact Type`
- `Artifact Path`
- `Evidence Family`
- `Status`
- `Paper Metric Allowed`

Only `paper_final` rows can allow paper metrics, and they must pass artifact
verification. `diagnostic_only` and `pending_review` rows must set
`paper_metric_allowed=false`. Smoke, dry-run, mock, pending, shadow, SPL,
failed, and diagnostic artifacts cannot be marked `paper_final`.

For any paper-facing benchmark artifact:

```powershell
.\.venv\Scripts\python.exe scripts\verify_artifact.py <benchmark_artifact_dir>
```

For semantic/business evidence that depends on a dual-policy artifact:

```powershell
.\.venv\Scripts\python.exe scripts\verify_artifact.py `
  <benchmark_artifact_dir> `
  --dual-policy-dir <dual_policy_artifact_dir>
```

`src/evaluation/dual_policy_packaging.py` also verifies the benchmark and
dual-policy artifacts before writing a paper-facing package, so direct API use
must obey the same gate.

## Judge ablation plan rule

Judge ablation plans are command/runbook artifacts, not semantic results.

`scripts/check_release_readiness.py --judge-ablation-plan-dir <plan_dir>`
validates that a plan:

- records two or more judge models,
- keeps semantic and strict policies explicit,
- marks only live judge calls as network-required,
- records completion files for every step,
- states that it does not call a judge or create benchmark outcomes,
- verifies the referenced baseline and adaptive benchmark artifacts.

Do not cite a judge ablation plan as a metric. Only cite completed judge,
consensus, dual-policy, and ablation artifacts after verification.

## Judge artifact metadata rule

Paper-facing judge artifacts must pass:

```powershell
.\.venv\Scripts\python.exe scripts\check_release_readiness.py `
  --judge-artifact-dir <judge_artifact_dir>
```

The gate validates `judge_summary.json`, `judgments.jsonl`,
`judge_costs.json`, `semantic_business_summary.csv`, and
`judge_reasoning.md`. It requires provider, model, prompt version, judge
policy, authoritative status, provider-error counts, redaction policy, and
token/cost metadata. Mock or non-authoritative judge artifacts cannot pass as
paper-facing judge evidence.

Provider errors and provider parse errors are not correctness labels. Judge
summaries must count them separately from semantic/business correct and
incorrect rows, and artifacts containing non-authoritative provider-error rows
must remain unpromoted until affected judge branches are rerun or replaced by a
predeclared judge model.

When merging retry judge artifacts, use
`scripts\merge_judge_artifacts.py --duplicate-policy prefer-authoritative`.
This policy may replace a provider-error retry row with an existing live
authoritative row for the same case, but it must not infer, rewrite, or promote
non-authoritative rows into correctness labels.

## Paper table rule

All paper tables must be generated from artifacts.

Never manually edit final paper numbers.

Generated paper tables must include:

- `dataset_hash`
- `selected_cases_hash`
- artifact provenance such as summary, predictions, benchmark CSV, or manifest

`scripts/check_release_readiness.py --paper-doc <paper_tables.md>` rejects
paper table markdown that lacks dataset/split hashes or artifact provenance.

## Dual-policy semantic evidence rule

The dual-policy artifact must be authoritative, complete, and free of unresolved
labels such as `adjudication_required`, `partial_business_match`,
`partial_or_mixed`, or `unjudged`.

Keep strict SQL execution metrics separate from semantic/business correctness.

## Diagnostic run rule

Small SPL, shadow, smoke, dry-run, failed judge, and mock artifacts can be used
for engineering diagnostics only. They may be discussed as diagnostics with
explicit scope labels, but they must not be marked `paper_final` or used as
final paper metrics.

Candidate generation and verifier diagnostics must not use benchmark IDs, gold
SQL, execution-correct labels, strict/semantic policy labels, or other
paper-label fields for runtime candidate scoring. Use aggregate diagnostics
only until larger selected-case validation and final review are complete.
Runtime multi-candidate trigger controls, when used, must be declared in the
benchmark config through `multi_candidate_allowed_triggers` and/or
`multi_candidate_blocked_triggers`. These controls may use runtime uncertainty
or complexity signals such as `complex_intent`, `validation_failed`,
`missing_generated_sql`, or `execution_failed`; they must not be derived from
case IDs, gold SQL, execution-correct labels, strict/semantic labels, or
benchmark mismatch labels.
Runtime candidate-generation budgets, when used, must be declared through
`multi_candidate_extra_generation_budget_ms`. The budget may stop extra
candidate generation after a slow primary candidate and must be recorded in the
prediction trace; it is a latency control, not a correctness metric or semantic
evidence.
Multi-candidate comparison summaries should include aggregate
`candidate_diversity_summary`, `component_latency_summary`, and
`latency_diagnostics` sections that omit case IDs, SQL text, gold SQL, and
strict or semantic correctness labels. They may also include an aggregate
`candidate_issue_outcome_summary` for SQL-positive diagnostic counters by
candidate issue code; this summary must not include case IDs, SQL text, gold SQL,
or semantic/business labels. Case-level comparison rows are trace artifacts, not
tuning inputs. The release gate must expose promotion blockers separately from
diagnostic artifact validity, so missing semantic/business evidence blocks
adoption promotion without turning the diagnostic artifact into a failed run.
`latency_regression_summary`, when present, is aggregate runtime triage only: it
can flag p95/mean latency increases and rank aggregate groups/components, but it
is not a correctness metric and must not be used for case-specific tuning.
Latency-budget acceptance guards are opt-in and must be explicit. They compare
aggregate benchmark latency deltas only; they do not create semantic/business
evidence and must remain separate from SQL-positive correctness and behavioral
evaluation.
Component latency summaries must report only recorded timing fields. Mark
optional components that are absent from a prediction trace as not recorded
rather than inferring attribution from total latency. New benchmark traces may
include candidate-verification and reliability-gate timing, but older artifacts
must remain explicitly unavailable until rerun.
Latency diagnostics should include action-level aggregate breakdowns such as
`by_adaptive_reliability_gate_action` so runtime review can distinguish answer,
review, clarification, and refusal paths without inspecting individual cases.

Candidate adoption review packages are non-authoritative diagnostic artifacts.
They must set `paper_metric_allowed=false` and must not export gold SQL,
benchmark execution-correct labels, or result-mismatch labels. Strict reference
review, if needed, uses separately controlled reference material at the final
human-review stage.

For larger candidate-selection diagnostics, use matched shadow/adoption configs
such as `experiments/configs/phase7_promptdiverse_shadow_spl15_diagnostic.yaml`
and `experiments/configs/phase7_promptdiverse_adopt_spl15_diagnostic.yaml`.
These configs are diagnostic-only, keep deterministic templates disabled, keep
semantic/business review separate, and require the candidate review package gate
before any downstream discussion.
