# PARS-SQL / ADHD-VTD — Codex Prompt Library

## Global rule for all prompts

در هر prompt اگر نگفتم، به‌صورت پیش‌فرض این‌ها را رعایت کن:

```text
Read AGENTS.md first.
Read docs/context-hub/INDEX.md.
Load only the relevant context files.
Do not scan unrelated result artifacts.
Make the smallest safe change.
Add/update tests for behavior changes.
Run the smallest relevant test suite.
Report files changed, tests run, risks, and next step.
```

---

# 00 — Task Planning / قبل از هر کار بزرگ

```text
Read AGENTS.md and docs/context-hub/INDEX.md.

I want to work on this task:

[TASK]

Do not edit files yet.

First produce a precise implementation plan:
1. Task classification
2. Relevant context files to read
3. Affected modules
4. Files likely to change
5. Tests that must be added or updated
6. Risks
7. Smallest safe first patch
8. Commands to run

Constraints:
- Do not modify datasets.
- Do not modify final paper metrics.
- Do not bypass SQL safety or read-only execution.
- Keep SQL-positive and behavioral evaluation separate.
```

---

# 01 — General Implementation Prompt

```text
Read AGENTS.md and docs/context-hub/INDEX.md.

Task:
[DESCRIBE THE EXACT CHANGE]

Use only the relevant context files. Do not load large benchmark result files unless necessary.

Constraints:
- Make minimal scoped changes.
- Preserve existing public interfaces unless change is required.
- Do not change dataset files.
- Do not change paper result numbers.
- Do not bypass validation or read-only execution.
- Add or update tests for behavior changes.

Implementation requirements:
1. Explain your plan before editing.
2. Implement the smallest safe patch.
3. Add/update tests.
4. Run or tell me exact commands to run.
5. Report risks and next step.

Return:
- Summary
- Files changed
- Tests added/updated
- Commands run
- Results
- Risks
- Next recommended step
```

---

# 02 — Code Review / قبل از تغییر

```text
Read AGENTS.md and docs/context-hub/INDEX.md.

Review this module or change without editing first:

[TARGET FILES OR FEATURE]

Focus on:
1. Safety/privacy risks
2. Query-shape risks
3. Benchmark/reproducibility risks
4. Hidden coupling
5. Missing tests
6. Possible artifact/reporting issues
7. Minimal fix plan

Do not rewrite code yet.
Return a prioritized review with severity: critical, high, medium, low.
```

---

# 03 — Fix Low EX / Query Shape Contract

```text
Read AGENTS.md.
Read:
- docs/context-hub/QUERY_SHAPE_CONTRACTS.md
- docs/context-hub/FAILURE_PATTERNS.md

Goal:
Reduce valid-but-wrong SQL caused by wrong output shape, especially scalar questions being converted into grouped SQL.

Work only on:
[LIST TARGET FILES, e.g. src/core/query_ir.py, src/sql_validation/shape_validator.py, src/generation/prompts/sql_generation.j2]

Do not modify:
- retrieval modules
- dataset files
- benchmark result files
- paper tables

Required behavior:
1. Scalar questions must not produce GROUP BY.
2. Scalar questions must not add hidden WHERE filters.
3. Rate questions must compute numerator/denominator correctly.
4. Two-sided comparisons must group by the binary/category column, not filter one side.
5. Ambiguous shape must ask clarification.

Add/update tests:
- scalar count
- scalar average
- scalar rate
- grouped distribution
- two-sided comparison
- hidden filter rejection

Return:
- shape contract changes
- examples before/after
- tests added
- commands to run
- risks
```

---

# 04 — Safety / Privacy Hardening

```text
Read AGENTS.md.
Read:
- docs/context-hub/SAFETY_PRIVACY_RULES.md
- data/schema/schema_graph.json

Task:
Audit and improve SQL safety/privacy for:

[TARGET FILES]

Required checks:
1. Only SELECT and WITH ... SELECT allowed.
2. Destructive SQL rejected.
3. Multiple statements rejected.
4. SQL comments rejected.
5. Top-level SELECT * rejected.
6. COUNT(*) allowed.
7. Illegal joins rejected.
8. Read-only executor cannot mutate the database.
9. Sensitive mental-health row-level disclosure refused or blocked.

Do not weaken any safety rule.

Add/update tests:
- destructive SQL
- multiple statement
- comments
- SELECT *
- COUNT(*)
- illegal join
- sensitive row-level request
- read-only mutation attempt

Return:
- safety issues found
- patch summary
- tests
- commands
- residual risks
```

---

# 05 — Persian NLU / Schema / Value Linking

```text
Read AGENTS.md.
Read:
- docs/context-hub/QUERY_SHAPE_CONTRACTS.md
- data/schema/column_aliases.fa.json
- data/schema/business_glossary.fa.json
- data/schema/metric_definitions.json
- data/schema/value_dictionary.generated.json

Task:
Improve Persian NLU / schema linking / value linking for:

[DESCRIBE TARGET, e.g. depression/anxiety/sleep/CGPA/Finglish/rate/country prevalence]

Requirements:
1. Handle Persian/Arabic character variants.
2. Handle Persian digits.
3. Handle colloquial Persian.
4. Handle common typos.
5. Handle Finglish and mixed Persian-English.
6. Do not hallucinate tables, columns, or values.
7. Return unresolved_terms when needed.
8. Ask clarification for ambiguous mappings.
9. Respect schema_graph join restrictions.

Add/update tests for:
- Persian typo
- Finglish
- mixed query
- ambiguous term
- unresolved schema term
- value alias
- binary flag/rate mapping

Return:
- normalized terms
- schema candidates
- value candidates
- unresolved terms
- confidence behavior
- tests
```

---

# 06 — Benchmark Metrics Audit

```text
Read AGENTS.md.
Read:
- docs/context-hub/ARTIFACT_RULES.md
- src/evaluation/metrics.py
- src/evaluation/action_normalizer.py
- scripts/run_benchmark.py

Task:
Audit benchmark metric computation for:

[DESCRIBE METRIC OR RUN]

Check:
1. SQL-positive and behavioral metrics are separate.
2. Strict EX denominator is explicit.
3. Conservative EX can be reported when generated SQL is missing.
4. Valid SQL rate matches predictions.
5. Unsafe SQL count matches predictions.
6. Missing SQL count is separate.
7. Semantic/business judge is not mixed with strict EX.
8. Summary matches prediction rows.
9. No smoke/config/mock run can be cited as final.

Do not change datasets.

Add/update artifact tests if needed.

Return:
- metric issues
- denominator definitions
- patch summary
- tests
- commands
- paper table impact
```

---

# 07 — Artifact Verifier Implementation

```text
Read AGENTS.md.
Read:
- docs/context-hub/ARTIFACT_RULES.md

Implement or improve:
scripts/verify_artifact.py

It must check:
1. config exists
2. predictions file exists
3. summary json exists
4. manifest entry exists
5. prediction count matches summary total
6. failure count matches summary failures
7. EX numerator/denominator matches predictions
8. valid SQL count matches predictions
9. unsafe SQL count matches predictions
10. deterministic_templates flag is explicit
11. dataset hash is present
12. selected cases hash is present
13. run is not smoke unless labeled smoke
14. mock judge is not cited as authoritative
15. placeholder reranker is not cited as real reranker

Add tests under tests/artifact/.

Return:
- verifier checks added
- test fixtures
- commands to run
- known limitations
```

---

# 08 — Route-Specific Prompt Refactor

```text
Read AGENTS.md.
Read:
- docs/context-hub/QUERY_SHAPE_CONTRACTS.md
- docs/context-hub/FAILURE_PATTERNS.md
- src/generation/output_parser.py

Goal:
Refactor SQL generation into route-specific prompts.

Create or update:
- sql_generation_scalar.j2
- sql_generation_grouped.j2
- sql_generation_ranking.j2
- sql_generation_timeseries.j2
- sql_generation_matrix.j2
- sql_generation_raw_rows.j2

Start with only this shape:
[SCALAR/GROUPED/RANKING/TIMESERIES/MATRIX/RAW_ROWS]

Rules:
1. Do not change all prompts at once.
2. Preserve output parser compatibility.
3. Include negative examples.
4. Include JSON output format.
5. Include clarification path.
6. For scalar, explicitly forbid GROUP BY and hidden WHERE.

Add prompt snapshot/parser tests if available.

Return:
- prompt file changed
- new constraints
- parser compatibility
- tests
- risks
```

---

# 09 — Candidate Generation + Verifier

```text
Read AGENTS.md.
Read:
- docs/context-hub/QUERY_SHAPE_CONTRACTS.md
- docs/context-hub/ARTIFACT_RULES.md
- src/graph/workflow.py
- src/graph/state.py
- src/sql_validation/validation_pipeline.py

Task:
Design and implement a minimal candidate generation + verifier stage.

Do not implement a complex multi-agent system.
Start with N=3 candidates maximum.

Requirements:
1. Generate diverse SQL candidates only when enabled by config.
2. Validate each candidate with syntax, safety, schema, join, aggregation, and shape checks.
3. Execute only candidates that pass safety validation.
4. Score candidates using runtime signals only, not gold labels.
5. Select best candidate or abstain/clarify if disagreement is high.
6. Record candidate traces.
7. Add ablation flag.

Candidate score should consider:
- validation_ok
- execution_ok
- shape_ok
- schema coverage
- value coverage
- candidate agreement
- unsafe penalty
- schema error penalty
- shape error penalty

Add tests:
- candidate safety
- candidate selection
- candidate disagreement abstention
- no gold leakage

Return:
- design summary
- files changed
- tests
- benchmark impact
- risks
```

---

# 10 — Reliability Gate Calibration

```text
Read AGENTS.md.
Read:
- docs/context-hub/ARTIFACT_RULES.md
- src/evaluation/reliability_gate.py
- src/evaluation/reliability_metrics.py
- src/evaluation/action_normalizer.py

Task:
Improve reliability gate calibration.

Requirements:
1. Use runtime signals only.
2. Do not use gold SQL, result_match, or case IDs.
3. Keep SQL-positive and behavioral semantics separate.
4. Add confidence buckets if possible.
5. Return answer, ask_clarification, refuse_unsafe, retry, needs_review, or answer_with_warning if supported.
6. High-confidence answer should be more likely semantically correct.
7. Preserve safety rejection.

Signals to consider:
- intent confidence
- schema confidence
- value confidence
- validation passed
- shape passed
- execution succeeded
- execution empty
- candidate agreement
- consistency critic
- semantic unit tests if present

Add tests:
- unsafe request
- low confidence
- validation failure
- empty result
- candidate disagreement
- semantic judge incorrect if present
- no gold leakage

Return:
- policy changes
- thresholds
- tests
- expected metric impact
```

---

# 11 — Paper Claim / Section Writing

```text
Read AGENTS.md.
Read:
- docs/context-hub/ARTIFACT_RULES.md
- docs/context-hub/FAILURE_PATTERNS.md
- latest paper_tables.md
- latest final artifact manifest
- limitations.md

Task:
Write or revise this paper section:

[SECTION NAME]

Rules:
1. Every numeric claim must come from an artifact.
2. Include numerator and denominator.
3. Keep strict EX separate from semantic/business correctness.
4. Do not call LLM judge human evaluation.
5. Do not claim SOTA.
6. Do not make broad accuracy claims.
7. Do not claim clinical use.
8. Do not hide low EX.
9. Clearly state limitations.
10. Use careful academic wording.

Return:
- revised text
- claim/evidence table
- risky claims removed
- missing evidence needed
```

---

# 12 — Human Annotation / Audit Pipeline

```text
Read AGENTS.md.
Read:
- docs/annotation/guidelines_fa.md
- docs/annotation/adjudication_fa.md
- docs/context-hub/ARTIFACT_RULES.md

Task:
Implement or improve human annotation processing.

Inputs:
[DESCRIBE LABEL STUDIO OR CSV/JSON EXPORT]

Outputs:
- data/annotations/round1_adjudicated.jsonl
- data/annotations/inter_annotator_matrix.csv
- data/annotations/kappa_report.json

Requirements:
1. Compute Cohen's kappa.
2. Report per-label agreement.
3. Separate SQL-positive semantic labels from behavioral action labels.
4. Preserve original case IDs.
5. Do not overwrite raw annotation files.
6. Produce audit manifest with hashes.

Labels:
- correct_semantic
- incorrect_shape
- incorrect_domain
- incorrect_filter
- privacy_violation
- should_ask_clarification
- correct_refusal
- incorrect_refusal

Add tests for parser and kappa computation.

Return:
- files generated
- schema of outputs
- commands
- quality warnings
```

---

# 13 — Error Taxonomy / Failure-Driven Development

```text
Read AGENTS.md.
Read:
- docs/context-hub/FAILURE_PATTERNS.md
- docs/context-hub/ARTIFACT_RULES.md
- latest failures.jsonl if needed

Task:
Build or improve error taxonomy analysis.

Classify failures into:
1. intent error
2. schema linking error
3. value grounding error
4. missing filter
5. extra hallucinated filter
6. wrong aggregation
7. wrong denominator
8. missing GROUP BY
9. wrong grouping dimension
10. wrong ranking/window logic
11. wrong temporal logic
12. wrong table/domain
13. illegal/missing join
14. shape mismatch
15. output parse failure
16. validation false positive
17. validation false negative
18. execution/hash issue
19. gold ambiguity
20. human/judge disagreement

Outputs:
- error taxonomy CSV
- Pareto summary
- top 5 fix recommendations
- debug mini-set suggestions

Do not modify benchmark results.

Return:
- taxonomy logic
- examples
- files changed
- tests
- next development priority
```

---

# 14 — Refactor Monolithic Graph Nodes

```text
Read AGENTS.md.
Read:
- docs/context-hub/INDEX.md
- src/graph/workflow.py
- src/graph/state.py
- src/graph/routes.py
- src/graph/nodes/base_nodes.py

Task:
Refactor graph nodes gradually.

Goal:
Split base_nodes.py into focused node files without changing behavior.

Rules:
1. Do not change graph semantics in the first refactor.
2. Move one node family at a time.
3. Preserve imports.
4. Add smoke tests.
5. Keep heavy logic in specialist modules, not graph orchestration.
6. Graph nodes should orchestrate only.

First target:
[NORMALIZE / INTENT / SCHEMA / RETRIEVAL / GENERATION / VALIDATION / EXECUTION / OUTPUT / REFLEXION]

Return:
- moved functions
- import updates
- tests
- behavior preservation check
- risks
```

---

# 15 — Context Pack Builder

```text
Read AGENTS.md and docs/context-hub/INDEX.md.

Task:
Implement scripts/build_context_pack.py.

Purpose:
Create a minimal task-specific context file for Codex/PyCharm AI Assistant.

Inputs:
- task type: safety, query_shape, benchmark, nlu_schema, prompt, paper, artifact, architecture
- optional target file

Output:
- .context-packs/<timestamp>_<task_type>.md

Requirements:
1. Include AGENTS.md summary.
2. Include only relevant context-hub docs.
3. Include list of target files.
4. Include non-negotiable constraints for that task.
5. Exclude large result files by default.
6. Warn if selected context exceeds size threshold.

Add tests for context routing.

Return:
- script usage
- supported task types
- tests
- risks
```

---

# 16 — Reproducibility Runbook

```text
Read AGENTS.md.
Read:
- docs/context-hub/ARTIFACT_RULES.md

Task:
Create or improve reproducibility scripts and docs.

Required files or canonical equivalents:
- scripts/check_release_readiness.py
- scripts/verify_artifact.py
- scripts/run_benchmark.py
- scripts/package_dual_policy_evidence.py when semantic/business evidence is in scope
- scripts/judge_benchmark_artifact.py when semantic judge evidence is in scope
- scripts/plan_dual_policy_judge_ablation.py when judge ablation planning is in scope
- docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md
- docs/context-hub/ARTIFACT_RULES.md

Requirements:
1. One command regenerates paper tables.
2. One command verifies dataset hashes.
3. One command verifies benchmark artifacts.
4. Paper numbers must come from artifacts.
5. Script must fail on missing/invalid artifacts.
6. Generated paper tables must include `dataset_hash`, `selected_cases_hash`,
   and artifact provenance.
6. Do not run full local LLM benchmark unless explicitly requested.

Return:
- commands
- files changed
- assumptions
- tests
- expected outputs
```

---

# 17 — Final Pre-Commit Review

```text
Read AGENTS.md and docs/context-hub/INDEX.md.

Review the current changes before commit.

Check:
1. Safety rules preserved
2. No read-only bypass
3. No dataset accidental changes
4. No benchmark result accidental changes
5. No paper number manual edits
6. Tests added for behavior change
7. Query-shape risks
8. Artifact/reproducibility risks
9. Import/path issues
10. Documentation needed

Return:
- commit readiness: yes/no
- blocking issues
- non-blocking issues
- tests to run
- suggested commit message
```

---

# 18 — Bug Report Prompt

```text
Read AGENTS.md and docs/context-hub/INDEX.md.

I observed this bug:

[PASTE ERROR / LOG / CASE ID / SQL / QUESTION]

Do not guess.

First:
1. Identify likely module.
2. Ask for missing artifact/log only if necessary.
3. Propose minimal reproduction.
4. Propose fix plan.
5. Identify tests to add.

Then wait for confirmation before editing.
```

---

# 19 — First Phase Implementation: Query Shape Core

```text
Read AGENTS.md and docs/context-hub/INDEX.md.
Read:
- docs/context-hub/QUERY_SHAPE_CONTRACTS.md
- docs/context-hub/FAILURE_PATTERNS.md

Implement Phase 1 only:
- create or update src/core/query_shape.py
- create or update src/sql_validation/shape_contract.py
- add unit tests under tests/unit/

Do not modify:
- retrieval
- judge
- paper files
- dataset files
- benchmark result files

Exit gate:
No scalar-intent test may emit or accept grouped SQL.

Required tests:
1. scalar COUNT(*) accepted
2. scalar AVG accepted
3. scalar GROUP BY rejected
4. scalar hidden WHERE rejected when not requested if contract marks filters forbidden
5. grouped query accepted when group_by required
6. ranking query requires ORDER BY
7. raw_rows requires LIMIT

Return:
- files changed
- tests added
- commands to run
- risks
```

---

# 20 — First Prompt Refactor: Scalar Prompt Only

```text
Read AGENTS.md.
Read:
- docs/context-hub/QUERY_SHAPE_CONTRACTS.md
- docs/context-hub/FAILURE_PATTERNS.md
- src/generation/output_parser.py

Create or update only:
src/generation/prompts/sql_generation_scalar.j2

Do not touch non-scalar prompts.

The scalar prompt must enforce:
1. exactly one SQL query
2. one-row KPI result
3. no GROUP BY unless user explicitly asks grouped output
4. no latent subgroup dimensions
5. no hidden WHERE
6. COUNT(*) for simple count
7. ROUND(AVG(col), 2) for simple average
8. NULL handling for averages when needed
9. only supplied schema tables/columns
10. clarification for ambiguity or unsupported joins
11. JSON output compatible with OutputParser

Add one negative example:
Bad: turning "تعداد کل رکوردها" into GROUP BY depression_flag.

Return:
- prompt content
- parser compatibility notes
- tests to run
```

---

# 21 — Label Studio Human Audit Prep

```text
Read AGENTS.md.
Read:
- docs/context-hub/ARTIFACT_RULES.md

Task:
Prepare human audit documentation and export schema for semantic/business correctness.

Create or update:
- docs/annotation/guidelines_fa.md
- docs/annotation/adjudication_fa.md
- docs/annotation/taxonomy_fa.md
- data/annotations/README.md

Labels:
- correct_semantic
- incorrect_shape
- incorrect_domain
- incorrect_filter
- privacy_violation
- should_ask_clarification
- correct_refusal
- incorrect_refusal

Requirements:
1. Persian-first annotation instructions.
2. Explain scalar/grouped/ranking/timeseries/matrix.
3. Give examples of hidden GROUP BY, hidden WHERE, wrong denominator.
4. Explain privacy violation for sensitive mental-health data.
5. Explain adjudication procedure.
6. Define expected output files.

Do not create actual annotations.

Return:
- files changed
- annotation workflow
- remaining manual steps
```

---

# 22 — Retrieval / CAG Hygiene

```text
Read AGENTS.md.
Read:
- docs/context-hub/ARTIFACT_RULES.md
- src/retrieval/
- src/retrieval/context_builder.py

Task:
Audit and improve CAG/retrieval hygiene.

Requirements:
1. Preserve self-overlap exclusion.
2. Do not retrieve the same case into its own prompt.
3. Record retrieved_ids, bm25_ids, vector_ids, and self_overlap_removed in trace.
4. Add retrieval hit@k evaluation if possible.
5. Do not claim placeholder reranker as real reranker.
6. Ensure examples are shape-compatible when possible.
7. Prefer examples from the same domain and shape.

Add tests:
- self-overlap exclusion
- retrieved trace fields
- no identity reranker final claim
- shape-compatible retrieval filter if implemented

Return:
- retrieval risks
- patch summary
- tests
- benchmark impact
```

---

# 23 — Dataset Hash / Split Freeze

```text
Read AGENTS.md.
Read:
- docs/context-hub/ARTIFACT_RULES.md

Task:
Implement or improve dataset hash and split freeze utilities.

Create or update:
- scripts/verify_artifact.py
- scripts/check_release_readiness.py
- src/evaluation/export_utils.py when paper-table provenance is in scope
- data/splits/README.md or experiments/registries/dataset_registry.json only when a formal split registry is explicitly in scope

Requirements:
1. Verify artifact `dataset_path` still hashes to `dataset_hash` when available.
2. Record total count and case IDs only when a split registry is explicitly in scope.
3. Record selected-case hash for every benchmark run.
4. Fail if dataset changed without version bump.
5. Separate dev/test/holdout/behavioral splits.
6. Do not modify dataset contents.

Add tests:
- hash stable
- case ID order stable
- changed file triggers failure
- registry missing field triggers failure

Return:
- files changed
- registry schema
- commands
- risks
```

---

# 24 — Quick Daily Coding Prompt

```text
Read AGENTS.md and docs/context-hub/INDEX.md.

Task:
[TASK]

Use the relevant skill/rule automatically.

Keep the patch small.
Do not touch datasets, benchmark results, or paper numbers unless the task explicitly asks for it.
Add/update tests.
Run the smallest relevant tests or provide exact commands.

Return:
Summary, files changed, tests, commands, risks, next step.
```
