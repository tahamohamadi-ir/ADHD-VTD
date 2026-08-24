# 08 - Project Structure and File Map

**Status:** Updated with v2.3 repository gates and execution-ready artifacts  
**Version:** v2.3 Execution-Ready alignment  
**Updated focus:** implementation-first, reliability-first, edge-aware, benchmark-auditable.


**Project:** ADHD-VTD / VTD-Edge / PARS-SQL  
**Purpose:** Canonical, implementation-aligned project structure for the current codebase.  
**Audience:** Developers, researchers, LLM coding assistants, reviewers.  
**Status:** Accepted as the current source-of-truth for folder and file responsibilities.

---

## 1. Why This File Exists

The project evolved from earlier VTD-Edge drafts into a cleaner, research-grade implementation structure.
Some earlier documents describe an `app/`-based layout or older modules such as `src/pipeline`, `src/rag`, and `src/analysis`.
The current project is now organized around a `src/`-based architecture with explicit modules for Persian NLU, schema linking, retrieval, generation, validation, database execution, reflexion, graph orchestration, output, and evaluation.

This file defines the **canonical project structure** that implementation work should follow from now on.

If another document conflicts with this file about folder names or file locations, prefer this file.

---

## 2. Current Architectural Philosophy

The system is a **compiler-like Persian Text-to-SQL pipeline**:

```text
Persian user question
  -> Persian NLU and normalization
  -> intent / ambiguity / safety detection
  -> schema linking and join reasoning
  -> retrieval / CAG context packing
  -> local LLM SQL generation
  -> SQL validation and deterministic repair
  -> read-only execution
  -> semantic checking
  -> answer, chart, explanation
  -> benchmark trace and error analysis
```

The LLM only generates **candidate SQL**. Safety, correctness, execution, and benchmark logging are handled by deterministic or auditable components.

---

## 3. Canonical Root Structure

```text
ADHD-VTD/
|
|-- benchmark/                     # Benchmark definitions, configs, baselines, protocols
|   |-- configs/
|   |-- baselines/
|   |-- protocols/
|   `-- README.md
|
|-- data/                          # Databases, schema artifacts, datasets, RAG artifacts
|   |-- audit/
|   |-- db/
|   |-- golden_sql/
|   |-- questions/
|   |-- rag/
|   `-- schema/
|
|-- docs/                          # Human-readable and LLM-friendly documentation
|   |-- adr/
|   |-- 00_INDEX.md
|   |-- 01_RESEARCH_GRADE_ARCHITECTURE.md
|   |-- 02_LANGGRAPH_WORKFLOW_SPEC.md
|   |-- 03_PERSIAN_NLU_AND_SCHEMA_LINKING.md
|   |-- 04_RAG_CAG_AND_RETRIEVAL_DESIGN.md
|   |-- 05_SQL_GENERATION_VALIDATION_REFLEXION.md
|   |-- 06_EVALUATION_ABLATION_AND_PAPER_PLAN.md
|   |-- 07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md
|   `-- 08_PROJECT_STRUCTURE_AND_FILE_MAP.md
|
|-- experiments/                   # Reproducible ablation and run configurations
|   |-- configs/
|   `-- README.md
|
|-- logs/                          # Runtime logs; usually gitignored except .gitkeep
|
|-- models/                        # Local LLM, embedding, reranker, narrative models
|   |-- embedding/
|   |-- narrative/
|   |-- reranker/
|   |-- MODEL_REGISTRY.md
|   `-- README.md
|
|-- results/                       # Generated benchmark and ablation outputs
|   |-- ablation/
|   |-- benchmark/
|   |-- error_analysis/
|   `-- reports/
|
|-- scripts/                       # CLI utilities and one-off project scripts
|
|-- src/                           # Main Python source code
|
|-- tests/                         # Unit, integration, and benchmark tests
|
|-- main.py
|-- pyproject.toml
|-- requirements.txt
|-- .env.example
`-- README.md
```

---

## 4. Source Code Responsibility Map

The `src/` directory is the core implementation package. Each folder must have one clear responsibility.

```text
src/
|
|-- config/             # Settings, paths, feature flags
|-- core/               # Shared types, enums, exceptions, contracts
|-- db/                 # SQLite connection, schema inspection, read-only execution
|-- evaluation/         # Benchmark runner, metrics, ablation, error analysis, reports
|-- generation/         # Prompt building, local LLM wrapper, output parsing
|-- graph/              # LangGraph state, workflow, routes, checkpoints, nodes
|-- nlu/                # Persian normalization, number/date normalization, intent/safety/ambiguity
|-- output/             # Answer formatting, chart recommendation, explanation, narrative
|-- reflexion/          # Critic, repair planner, transition memory, retry policy, error taxonomy
|-- retrieval/          # Embeddings, Chroma, BM25, hybrid retrieval, reranker, context builder
|-- schema/             # Schema registry, schema graph, schema linker, join path finding, rules
|-- sql_validation/     # Syntax, schema, safety, semantic validation, SQL rewriting
`-- utils/              # JSONL, hashing, logging, timing, shared utilities
```

---

## 5. Module-Level Contracts

### 5.1 `src/config`

**Purpose:** Centralize all project paths and runtime configuration.

Expected files:

```text
src/config/
|-- paths.py
|-- settings.py
|-- features.py
`-- __init__.py
```

Rules:

- No business logic here.
- No LLM calls here.
- All project-relative paths should be resolved through `paths.py` or `settings.py`.
- `.env` overrides should be handled in `settings.py`.

---

### 5.2 `src/core`

**Purpose:** Shared domain-neutral contracts.

Expected files:

```text
src/core/
|-- types.py
|-- enums.py
|-- exceptions.py
|-- contracts.py
`-- __init__.py
```

Rules:

- Keep Pydantic models, enums, and common exceptions here.
- Do not put module-specific logic here.
- Avoid turning `core/` into a dumping ground.

---

### 5.3 `src/nlu`

**Purpose:** Persian-first natural language understanding.

Expected files:

```text
src/nlu/
|-- persian_normalizer.py
|-- number_normalizer.py
|-- date_normalizer.py
|-- intent_classifier.py
|-- ambiguity_detector.py
|-- safety_intent_detector.py
|-- colloquial_mapper.py
|-- term_extractor.py
`-- __init__.py
```

Responsibilities:

- Persian/Arabic character normalization.
- Digit normalization.
- Jalali/Gregorian date normalization.
- Colloquial Persian mapping.
- Intent, ambiguity, and unsafe-intent detection.
- Domain term extraction before schema linking.

---

### 5.4 `src/schema`

**Purpose:** Ground user intent in the actual database schema.

Expected files:

```text
src/schema/
|-- schema_loader.py
|-- schema_registry.py
|-- schema_graph.py
|-- schema_linker.py
|-- join_path_finder.py
|-- business_rules.py
`-- __init__.py
```

Responsibilities:

- Load `data/schema/*.json` artifacts.
- Resolve aliases and business concepts into tables/columns.
- Infer join paths.
- Build compact schema context for prompts.
- Prevent schema hallucination by exposing only known tables and columns.

---

### 5.5 `src/retrieval`

**Purpose:** Retrieve the smallest high-value context needed for SQL generation.

Expected files:

```text
src/retrieval/
|-- embedding_model.py
|-- chroma_store.py
|-- bm25_index.py
|-- hybrid_retriever.py
|-- reranker.py
|-- context_builder.py
|-- retrieval_scorer.py
`-- __init__.py
```

Responsibilities:

- Load local embedding models.
- Build/query ChromaDB indexes.
- Build/query BM25 indexes.
- Fuse vector, lexical, intent, schema-overlap, and skeleton scores.
- Optionally rerank retrieved examples.
- Build prompt-ready CAG context.

---

### 5.6 `src/generation`

**Purpose:** Build prompts and call the local LLM.

Expected files:

```text
src/generation/
|-- llm_engine.py
|-- local_llm.py
|-- prompt_builder.py
|-- output_parser.py
|-- prompts/
|   |-- sql_generation.j2
|   |-- sql_repair.j2
|   |-- clarification.j2
|   |-- answer_generation.j2
|   `-- __init__.py
`-- __init__.py
```

Rules:

- The generation layer must not execute SQL.
- The generation layer must not decide safety.
- LLM output must be parsed into a strict structured format before validation.

---

### 5.7 `src/sql_validation`

**Purpose:** Treat generated SQL as untrusted input and validate it before execution.

Expected files:

```text
src/sql_validation/
|-- syntax_validator.py
|-- schema_validator.py
|-- safety_validator.py
|-- semantic_validator.py
|-- sql_rewriter.py
|-- validation_result.py
`-- __init__.py
```

Responsibilities:

- Enforce single-statement SQL.
- Enforce read-only `SELECT`.
- Reject unsafe commands.
- Parse SQL with `sqlglot`.
- Check tables/columns against `SchemaRegistry`.
- Check aggregation/grouping/limit rules.
- Support deterministic safe rewrites when allowed.

---

### 5.8 `src/db`

**Purpose:** Read-only database interaction.

Expected files:

```text
src/db/
|-- sqlite_connection.py
|-- read_only_executor.py
|-- schema_inspector.py
|-- result_serializer.py
`-- __init__.py
```

Rules:

- Use SQLite read-only mode.
- Never execute SQL before validation.
- Use timeouts.
- Return structured execution results.
- Do not format the final user answer here.

---

### 5.9 `src/reflexion`

**Purpose:** Convert validation/execution/semantic errors into repair actions.

Expected files:

```text
src/reflexion/
|-- critic.py
|-- repair_planner.py
|-- transition_memory.py
|-- error_taxonomy.py
|-- retry_policy.py
`-- __init__.py
```

Responsibilities:

- Categorize errors.
- Decide whether deterministic repair is safe.
- Build targeted critic feedback.
- Track attempts and avoid infinite retry loops.
- Produce research-friendly error taxonomy records.

---

### 5.10 `src/graph`

**Purpose:** LangGraph orchestration.

Expected files:

```text
src/graph/
|-- state.py
|-- workflow.py
|-- routes.py
|-- checkpoints.py
|-- nodes/
|   |-- normalize_node.py
|   |-- intent_node.py
|   |-- schema_linking_node.py
|   |-- retrieval_node.py
|   |-- generation_node.py
|   |-- validation_node.py
|   |-- execution_node.py
|   |-- reflexion_node.py
|   |-- semantic_check_node.py
|   |-- output_node.py
|   |-- candidate_helpers.py
|   |-- candidate_inspector.py
|   |-- candidate_orchestrator.py
|   |-- execution_attempts.py
|   |-- generation_router.py
|   |-- output_payloads.py
|   |-- reflexion_payloads.py
|   |-- sql_repair_helpers.py
|   |-- validation_attempts.py
|   `-- __init__.py
`-- __init__.py
```

Rules:

- `graph/` wires components together.
- Business logic should stay inside the relevant component module.
- Nodes should be thin wrappers around tested services.
- Workflow imports should use the dedicated `*_node.py` modules. During
  incremental cleanup, those modules may re-export operational callables from
  `base_nodes.py`, and tests should lock that compatibility contract.
- Candidate selection helpers belong in dedicated graph helper modules and
  must not expose gold SQL, reference answers, strict labels, or semantic
  labels in runtime candidate metadata.
- Candidate orchestration may coordinate generation, inspection, consistency,
  verifier scoring, latency budget accounting, and adoption gates, but must not
  own validation, execution, artifact promotion, or paper metrics.
- `generate_candidates_node.py` is policy-only compatibility glue. Actual
  multi-candidate SQL generation must stay behind `generate_sql` and
  `candidate_orchestrator.py`, where validation, inspection, and adoption gates
  are available.
- Candidate inspection may validate and execute candidate SQL only through
  injected validators and `src/db/read_only_executor.py`; direct SQLite access
  is not allowed in graph helper modules.
- SQL generation routing belongs in `generation_router.py`. It may choose
  between no-prompt, deterministic-template, single-LLM, and multi-candidate
  generation using injected dependencies, but it must not own prompt building,
  SQL validation, candidate scoring, SQL execution, artifact promotion, or
  paper metrics.
- Deterministic graph-local SQL repair helpers belong in dedicated helper
  modules and must still validate patched SQL before adoption.
- Validation attempt and retry-decision helpers belong in
  `validation_attempts.py`. They may format validation errors, build
  `SQLAttempt` records, and decide the retry category, but must not instantiate
  validators, rewrite SQL, execute SQL, or alter safety rules.
- Execution attempt helpers belong in `execution_attempts.py`. They may attach
  read-only execution results to the latest `SQLAttempt` and build state update
  payloads, but must not instantiate executors, open SQLite connections, retry
  independently, or bypass `src/db/read_only_executor.py`.
- Output payload helpers belong in `output_payloads.py`. They may coordinate
  answer formatting, chart recommendation, explanation fallback, and graceful
  failure payloads through injected output functions, but must not run SQL,
  mutate attempts, compute benchmark metrics, or promote paper artifacts.
- Reflexion payload helpers belong in `reflexion_payloads.py`. They may extract
  the latest error context, seed retry memory, format repair error text, attach
  critic feedback/repair plans to attempts, and build update payloads, but must
  not alter retry routing, instantiate validators/executors, or change repair
  prompt semantics.
- Routes must be deterministic.

---

### 5.11 `src/output`

**Purpose:** Convert validated execution results into user-facing output.

Expected files:

```text
src/output/
|-- answer_formatter.py
|-- chart_recommender.py
|-- narrative_generator.py
|-- explanation_builder.py
`-- __init__.py
```

Responsibilities:

- Persian answer formatting.
- KPI/table/chart recommendation.
- No hallucination if result is empty.
- Optional narrative/data-storytelling layer.
- Explanations and trace references.

---

### 5.12 `src/evaluation`

**Purpose:** Research-grade evaluation.

Expected files:

```text
src/evaluation/
|-- benchmark_runner.py
|-- metrics.py
|-- reliability_metrics.py
|-- retrieval_metrics.py
|-- ablation_runner.py
|-- error_analyzer.py
|-- report_generator.py
|-- export_utils.py
|-- llm_judge.py              # Phase 16 target
`-- __init__.py
```

Responsibilities:

- Run benchmark datasets.
- Compute EM, EX, valid SQL rate, schema linking accuracy, intent accuracy, safety rejection accuracy, clarification accuracy, retry success rate, latency and bootstrap CI.
- Keep execution correctness separate from semantic/business correctness.
- Run ablation configs.
- Store and report model/config/ablation/module metadata.
- Integrate optional LLM-as-a-Judge after Phase 10 trace artifacts are stable.
- Export paper-ready tables and reports.

---

## 6. Data Directory Contract

```text
data/
|-- audit/
|   `-- vtd_400_500_audit_report.md
|
|-- db/
|   |-- vtd_health_research_schema.sql
|   `-- vtd_health_research_v1.db
|
|-- schema/
|   |-- schema_snapshot.json
|   |-- schema_snapshot.generated.json
|   |-- schema_graph.json
|   |-- column_aliases.fa.json
|   |-- business_glossary.fa.json
|   `-- metric_definitions.json
|
|-- questions/
|   |-- full/
|   |-- train/
|   |-- dev/
|   |-- test/
|   `-- special/
|
|-- golden_sql/
|   |-- golden_examples.jsonl
|   `-- few_shot_bank.jsonl
|
`-- rag/
    |-- indexed_examples.jsonl
    |-- bm25/
    `-- chroma/
```

### Important Data Rules

- `data/db/` stores the actual SQLite database and SQL schema file.
- `data/schema/schema_snapshot.json` is the LLM-friendly curated schema.
- `data/schema/schema_snapshot.generated.json` is generated from the real SQLite database for sync checks.
- `data/questions/full/` stores full benchmark packages.
- `data/questions/special/` stores ambiguity, no-SQL, adversarial, chart, and edge-case questions.
- `data/golden_sql/` stores few-shot examples for generation.
- `data/rag/` stores retrieval-ready indexed artifacts.

---

## 7. Benchmark vs Evaluation vs Results

These three folders have different meanings:

```text
benchmark/          -> definitions, protocols, baseline configs
src/evaluation/     -> Python implementation of metrics and runners
results/benchmark/  -> generated benchmark run outputs
```

Correct mental model:

```text
benchmark/configs/full_system.yaml
        |
        v
src/evaluation/benchmark_runner.py
        |
        v
results/benchmark/<timestamp>_<mode>_<dataset>_<model_slug>_<ablation_id>/
```

Do not store generated outputs inside `benchmark/`.

---

## 8. Documentation Sync Notes

The following documentation files remain conceptually valid and should stay:

- `00_INDEX.md`
- `01_RESEARCH_GRADE_ARCHITECTURE.md`
- `02_LANGGRAPH_WORKFLOW_SPEC.md`
- `03_PERSIAN_NLU_AND_SCHEMA_LINKING.md`
- `04_RAG_CAG_AND_RETRIEVAL_DESIGN.md`
- `05_SQL_GENERATION_VALIDATION_REFLEXION.md`
- `06_EVALUATION_ABLATION_AND_PAPER_PLAN.md`
- `07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md`
- ADR files in `docs/adr/`

However, any old references to these paths should be considered deprecated:

```text
app/
src/analysis/
src/pipeline/
src/rag/
src/validators/
data/benchmark/ as primary dataset location
data/rag_examples.json
```

Use these paths instead:

```text
src/nlu/
src/graph/
src/retrieval/
src/sql_validation/
data/questions/
data/golden_sql/
data/rag/
results/benchmark/
```

---

## 9. Recommended Updates to Existing Docs

### `00_INDEX.md`

Add this file to the documentation map:

```text
08_PROJECT_STRUCTURE_AND_FILE_MAP.md | Canonical current folder structure, module responsibilities, data contracts, and path conventions
```

### `07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md`

Replace the old `app/`-based folder structure with a pointer to this file.

Recommended text:

```text
The canonical current project structure is documented in `08_PROJECT_STRUCTURE_AND_FILE_MAP.md`.
The older `app/`-based structure has been superseded by the current `src/`-based architecture.
```

### Older `Developer Documents/`

Keep them as historical references only, or move them to:

```text
docs/legacy/
```

Do not let older documents override the current Research-Grade documentation suite.

---

## 10. LLM-Friendly Implementation Instruction

When giving this project to an LLM coding assistant, include this instruction:

```text
Use `08_PROJECT_STRUCTURE_AND_FILE_MAP.md` as the source of truth for folder names and file responsibilities.
Do not create an `app/` directory.
Do not use deprecated modules such as `src/analysis`, `src/rag`, `src/pipeline`, or `src/validators`.
Use `src/nlu`, `src/retrieval`, `src/graph`, and `src/sql_validation` instead.
Generated benchmark outputs must go to `results/benchmark/`, not `benchmark/`.
```

---

## 11. Definition of Structural Done

The project structure is considered synchronized when:

```text
[ ] `00_INDEX.md` references this file.
[ ] `07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md` no longer presents `app/` as the active structure.
[ ] `src/rag` and `src/pipeline` are removed if empty.
[ ] `src/analysis` is replaced by `src/nlu`.
[ ] `src/validators` is replaced by `src/sql_validation`.
[ ] `data/schema/*.json` exists.
[ ] `data/golden_sql/*.jsonl` exists.
[ ] `data/rag/indexed_examples.jsonl` exists.
[ ] Benchmark configs are stored in `benchmark/`.
[ ] Benchmark outputs are stored in `results/benchmark/`.
```


---

## 12. v2.3 Repository Gates and New Required Artifacts

### 12.1 Root-Level Required Files

Add these to the root repository before contacting supervisors or publishing the repo:

```text
README.md
DATASET_CARD.md
```

`README.md` must include:

```text
project goal
privacy/edge motivation
Feature Decision Matrix
Phase 0 status
how to run the 50-question audit
how to run one query
```

`DATASET_CARD.md` must include:

```text
dataset origin
synthetic/de-identified policy
schema version
number of SQL-positive and behavioral examples
annotation process
known single-annotator limitation
human/LLM review status
clinical-use disclaimer
```

### 12.2 Required Audit Artifacts

Add these paths:

```text
data/audit/phase0_50q_audit.csv
data/audit/phase0_50q_audit_report.md
results/milestone_1_5_stress_test/summary.md
```

### 12.3 New Suggested Source Files

```text
src/schema/value_linker.py
src/nlu/safety_intent_detector.py
src/nlu/ambiguity_detector.py
src/evaluation/reliability_metrics.py
src/evaluation/robustness_runner.py
src/evaluation/human_agreement.py
src/sql_validation/reliability_gate.py
```

### 12.4 Conflict Rule

If a proposal document suggests a feature that is not in README's Feature Decision Matrix, do not implement it yet. First classify it as:

```text
MVP_NOW
PAPER_1
PAPER_2
EDGE_LATER
DO_NOT_BUILD_YET
```
