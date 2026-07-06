# 07 - Implementation Roadmap and Requirements

**Status:** Finalized implementation-first roadmap aligned with PARS-SQL / VTD-Edge v2.3 Execution-Ready proposal  
**Version:** v2.3 Execution-Ready alignment  
**Updated focus:** what to do first, what not to build yet, and how to avoid research/product drift.

---

## Current Technical Roadmap (2026-07-05)

This roadmap is the execution view of the final development plan in
`docs/PARS_SQL_PAPER1_IMPLEMENTATION_PLAN.md`. It keeps human review as the
last stage and focuses the near-term work on non-human cleanup, risk reduction,
accuracy improvements, and clean architecture.

### Phase 0 - Review, Inventory, and Preparation

Goal: establish the current source of truth before changing code.

Deliverables:

- artifact inventory: final, diagnostic-only, pending review, unpromoted,
- current risk list in `docs/Risks.md`,
- current failure taxonomy in `docs/context-hub/FAILURE_PATTERNS.md`,
- current release-gate command for affected artifacts.

Technical work:

- Validate that benchmark artifacts include config, predictions, summary,
  manifest, dataset hash, selected-case hash, model identity, prompt metadata,
  and run ID.
- Confirm that SQL-positive, behavioral, semantic/business, latency, and safety
  evidence are reported separately.
- Use `graphify-out/` only as a local navigation aid; do not commit generated
  graph artifacts.

Dependencies: existing artifacts, release gate, context hub.

Risks: stale docs, diagnostic artifacts accidentally treated as final, and
hidden metric-family mixing.

Success criteria: release gate passes with no actionable open non-human risk
and all final/pending/diagnostic statuses are explicit.

### Phase 1 - Design and Infrastructure Alignment

Goal: keep the codebase organized around stable contracts.

Deliverables:

- consolidated planning docs,
- release-gate coverage for docs and artifact governance,
- focused tests for any touched contract,
- no broad formatting-only churn mixed with logic changes.

Technical work:

- Keep `src/nlu`, `src/schema`, `src/generation`, `src/sql_validation`,
  `src/db`, `src/evaluation`, and `scripts` as separate ownership boundaries.
- Centralize failure and risk language in docs rather than scattering new
  one-off notes.
- Add or update focused tests before changing shared logic.

Dependencies: context hub, AGENTS.md rules, release gate.

Risks: over-refactoring, formatter churn masking logic changes, or new helper
APIs bypassing read-only execution.

Success criteria: touched modules have focused tests and no unrelated files are
rewritten.

### Phase 2 - MVP-Stable Accuracy Improvements

Goal: improve answer quality with generalizable fixes only.

Deliverables:

- query-shape contract improvements,
- prompt routing improvements,
- schema/value-linking improvements,
- validator feedback improvements,
- focused regression tests per failure class.

Technical work:

- Start with scalar, grouped, comparison, ranking, timeseries, and matrix shape
  contracts.
- Improve Persian normalization, colloquial/Finglish mapping, and ambiguity
  detection where they reduce repeated failure families.
- Ensure validators reject unsupported joins, hidden filters, and wrong
  aggregate shapes before execution.

Dependencies: `docs/context-hub/QUERY_SHAPE_CONTRACTS.md`,
`docs/context-hub/FAILURE_PATTERNS.md`, prompt templates, validation modules.

Risks: tuning to SPL diagnostic case IDs, changing denominator definitions, or
conflating semantic/business correctness with strict EX. These metric families
have different denominators and must be reported separately.

Success criteria: focused Phase 1-7 tests pass, no dataset changes occur, and
new evidence comes from predeclared reruns or fresh dev slices.

### Phase 3 - Core Capability Expansion

Goal: strengthen the pipeline without weakening safety or reproducibility.

Deliverables:

- cleaner candidate-generation policy,
- stronger candidate verifier diagnostics,
- clearer reliability-gate outcomes,
- aggregate-only latency and diversity summaries.

Technical work:

- Keep candidate adoption diagnostic until authoritative semantic/business
  evidence exists.
- Track aggregate candidate diversity, component latency, and issue-code
  outcomes without leaking case IDs, gold SQL, or correctness labels.
- Keep runtime budgets explicit in config and trace output.

Dependencies: benchmark runner, comparison artifact builder, candidate review
package, release gate.

Risks: latency regressions, leakage into candidate scoring, or diagnostic
evidence being promoted too early.

Success criteria: comparison artifacts pass aggregate-leakage checks and remain
promotion-blocked until review evidence is authoritative.

### Phase 4 - Testing, Optimization, and Hardening

Goal: make behavior stable before final human review.

Deliverables:

- focused unit and artifact tests,
- release-gate clean run,
- documented residual risks,
- reproducible commands for benchmark and judge artifacts.

Technical work:

- Run focused tests for safety, selection, disagreement, no-gold-leakage,
  output parser, judge parser, merge artifacts, release readiness, and artifact
  verifiers.
- Run broader tier1/artifact tests after shared evaluation or release-gate
  changes.
- Investigate full-repo formatting separately from logic work.

Dependencies: pytest, ruff, release gate, verified artifact paths.

Risks: old repo-wide lint drift and long benchmark runtimes.

Success criteria: touched-code formatting/checks pass, focused regression tests
pass, and release gate remains green for affected artifact families.

### Phase 5 - Deployment, Monitoring, and Maintenance

Goal: prepare a reproducible research package and a future local/private
deployment path.

Deliverables:

- final artifact manifest,
- paper-facing tables generated from verified artifacts,
- reproducibility commands,
- human review/adjudication package,
- maintenance checklist.

Technical work:

- Complete human adjudication only after non-human cleanup is stable.
- Promote artifacts to `paper_final` only through the promotion registry and
  release gate.
- Keep deployment local/private and route all SQL through the read-only
  executor.

Dependencies: human review, promotion registry, final artifact package.

Risks: reviewer disagreement, judge-model instability, and overclaiming
diagnostic evidence.

Success criteria: final package has no actionable risk, no unverified metric,
and explicit limitations for remaining open risks.

### Later Phases

- Build a clean paraphrase holdout for anti-overfit claims.
- Add CI jobs that run the fast release gate, focused unit tests, and doc drift
  checks.
- Add structured observability for local deployments: trace IDs, validator
  outcomes, abstention reasons, latency buckets, and safety-route decisions.
- Evaluate larger prompt-diverse/adaptive candidate policies only after
  authoritative semantic/business review is available.

## 1. Recommended Python Version

Use:

```text
Python 3.12.10 64-bit on Windows
```

Reason:

- stable on Windows,
- compatible with modern LLM/NLP/embedding tooling,
- avoids Python 3.13+ wheel instability for native/ML packages.

---

## 2. Requirements Strategy

Policy:

```text
Pin direct top-level dependencies.
Do not over-pin transitive dependencies like tokenizers unless required.
Use a fresh venv for major requirements changes.
After a successful install, freeze a working lock snapshot.
```

Recommended additions if missing:

```txt
rank-bm25>=0.2.2,<0.3
networkx>=3.4,<4
tabulate>=0.9.0,<1
openpyxl>=3.1.0,<4
statsmodels>=0.14.0,<0.16
sentencepiece>=0.2.0,<0.3
```

---

## 3. Canonical Project Structure

The canonical structure is defined in:

```text
docs/08_PROJECT_STRUCTURE_AND_FILE_MAP.md
```

Current source modules:

```text
src/config           settings, paths, feature flags
src/core             contracts, enums, exceptions, shared types
src/nlu              Persian normalization, number/date normalization, intent/safety/ambiguity routing
src/schema           schema loading, registry, schema graph, schema linking, value linking
src/retrieval        BM25, embeddings, Chroma, reranker, hybrid retrieval, context packing
src/generation       local LLM, prompt builder, output parser
src/sql_validation   syntax, safety, schema, semantic validation, SQL rewriting
src/db               SQLite read-only connection, execution, schema inspection
src/reflexion        critic, repair planner, retry policy, transition memory
src/graph            LangGraph research runtime
src/output           answer formatting, chart recommendation, explanation, narrative
src/evaluation       benchmark, ablation, metrics, error analysis, reports
src/utils            logging, hashing, timing, jsonl helpers
```

If this file conflicts with `08_PROJECT_STRUCTURE_AND_FILE_MAP.md`, prefer file 08.

---

## 4. Feature Decision Matrix

Keep this table in the root `README.md`.

| Feature | Build timing |
|---|---|
| schema freeze and schema snapshot | Phase 0 gate |
| 50-question benchmark audit | Phase 0 gate |
| README feature decision table | Phase 0 gate |
| DATASET_CARD.md | Phase 0 gate |
| Persian/number/date normalizer tests | Phase 1 |
| safety/ambiguity router | Phase 1 / Milestone 1.5 |
| value retrieval | Phase 2 or early Phase 3 |
| simple local LLM SQL generation | Milestone 1 |
| CAG retrieval | after Milestone 1.5 passes |
| LangGraph full pipeline | research runtime only |
| multi-candidate consistency abstention | Paper 1 extension or Paper 2 |
| SQL Surgeon / Reflexion | after validation stack is stable |
| edge state machine | later edge phase, not before research benchmark works |

---

## 5. Phase 0 - Governance, Schema Freeze, and Dataset Audit

### Goal

Make the project executable before it becomes complex.

### Tasks

```text
1. Freeze the current SQLite schema.
2. Generate schema_snapshot.generated.json from the DB.
3. Compare manual and generated schema snapshots.
4. Select 50 SQL-positive benchmark items.
5. Execute gold SQL for those 50 items against current DB.
6. Record misalignment in data/audit/phase0_50q_audit.csv.
7. Fix gold SQL or schema metadata before coding the LLM pipeline.
8. Create DATASET_CARD.md.
9. Add Feature Decision Matrix to README.md.
10. Commit Phase 0 to GitHub.
```

### Deliverables

```text
data/schema/schema_snapshot.generated.json
data/audit/phase0_50q_audit.csv
data/audit/phase0_50q_audit_report.md
DATASET_CARD.md
README.md updated with Feature Decision Matrix
```

### Acceptance Criteria

```text
[ ] Current DB opens read-only.
[ ] Generated schema snapshot exists.
[ ] 50 selected gold SQL queries execute or are explicitly marked as broken.
[ ] Every broken item has a correction decision.
[ ] README.md explains what is MVP, Paper 1, Paper 2, and Edge Later.
[ ] Phase 0 is committed to GitHub.
```

---

## 6. Milestone 1 - Raw Small-Model SQL Baseline

### Goal

Check whether a very small local model can produce any useful SQL before adding CAG or Reflexion.

### Setup

```text
Model: Qwen2.5-Coder-1.5B or Qwen3-1.7B
Dataset: 50 simple SQL-positive questions
Context: compact schema only
No CAG
No Reflexion
No SQL Surgeon
```

### Target

```text
EX@1 >= 40%
Valid SQL Rate >= 70%
Unsafe SQL reaches executor = 0
```

Passing this milestone does not justify jumping to advanced RAG. Run Milestone 1.5 first.

---

## 7. Milestone 1.5 - Mini Stress-Test

### Goal

Prevent false progress after an easy SQL baseline.

### Test Set

```text
10 Finglish/typo questions
5 Jalali-date questions
5 unsafe/adversarial questions
```

### Target

```text
Finglish/typo routing accuracy >= 70%
Jalali safe handling >= 80%
Unsafe rejection accuracy = 100%
No unsafe SQL reaches executor
```

### Deliverable

```text
results/milestone_1_5_stress_test/summary.md
```

---

## 8. Phase 1 - Deterministic Core

Implement and test:

```text
PersianNormalizer
NumberNormalizer
DateNormalizer
IntentClassifier v1
AmbiguityDetector v1
SafetyIntentDetector v1
SchemaLoader
SchemaRegistry
SchemaLinker
ValueLinker
```

Acceptance:

```text
pytest tests/tier1_unit -v
python scripts/test_schema_linker.py
python scripts/test_value_linker.py
```

---

## 9. Phase 2 - SQL Validation and Read-Only Execution

Implement:

```text
SyntaxValidator
SafetyValidator
SchemaValidator
JoinValidator
AggregationValidator
SemanticValidator v1
ReadOnlyExecutor
ResultSerializer
```

Rules:

```text
Only SELECT.
No multiple statements.
No mutation keywords.
No unsafe raw sensitive output.
Read-only SQLite URI.
Timeout enabled.
LIMIT required for raw retrieval.
```

---

## 10. Phase 3 - Minimal Local LLM Pipeline

Implement:

```text
LocalLLM
PromptBuilder
OutputParser
scripts/run_query.py
```

Run:

```powershell
python scripts/run_query.py "چند دانشجو افسردگی دارند؟"
```

Do not add CAG until the deterministic validators can reject bad SQL.

---

## 11. Phase 4 - CAG Retrieval

Implement:

```text
BM25Retriever
EmbeddingRetriever
SchemaOverlapRetriever
ValueRetriever
SkeletonRetriever
HybridRetriever
ContextBuilder
```

Measure:

```text
Schema Recall@k
Value Recall@k
Intent@k
Skeleton@k
Context token budget
```

---

## 12. Phase 5 - Research Runtime with LangGraph [COMPLETED]

Implement LangGraph after components are independently testable.

Status: 
- **Achieved:** Full LangGraph orchestration implemented in `src/graph`.
- **GPU Acceleration:** `llama-cpp-python` with CUDA 12.4 support integrated for 12x speedup.
- **Nodes:** Modularized Normalize -> Classify -> Link -> Generate -> Validate -> Execute -> Format.
- **Retry Loops:** Self-correction logic implemented for SQL repair.

---

## 13. Phase 6 - Reliability, Abstention, and Multi-Candidate Generation [COMPLETED]

Status:
- **Abstention:** Logic implemented in `classify_intent` and `routes.py` to reject ambiguous queries.
- **Validation-Driven Repair:** Implemented in `validate_sql` and `route_after_validation`.
- **Next Step:** Multi-candidate generation (sampling) and consistency checks (Paper 2 extensions).

---

## 14. Phase 7 - Benchmark and Ablation

First-paper minimum:

```text
A0 Direct prompt
A1 + Persian normalization
A2 + schema linking
A3 + value linking
A4 + CAG examples
A7 + validation stack
```

Run more ablations only after these produce useful results.

---

## 15. Human Agreement Requirement

Before paper submission:

```text
Review at least 50 benchmark items with a second reviewer or independent LLM-as-judge.
Report Cohen's Kappa or agreement percentage.
Disclose single-annotator limitations honestly.
```

---

## 16. Setup Commands

```powershell
cd D:\Project\ADHD-VTD
py -3.12 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

---

## 17. Immediate Tomorrow-Morning Checklist

```text
[ ] Ensure DB path is correct: data/db/vtd_health_research_v1.db
[ ] Generate schema snapshot from current DB.
[ ] Pick 50 SQL-positive questions.
[ ] Execute their gold SQL.
[ ] Write phase0_50q_audit_report.md.
[ ] Create DATASET_CARD.md.
[ ] Update README.md with Feature Decision Matrix.
[ ] Commit to GitHub.
```
