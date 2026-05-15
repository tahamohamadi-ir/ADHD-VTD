# 10 - Full Development Roadmap: From Zero to State-of-the-Art

**Status:** Updated with v2.3 execution gates, Milestone 1.5, and first-paper scope  
**Version:** v2.3 Execution-Ready alignment  
**Updated focus:** implementation-first, reliability-first, edge-aware, benchmark-auditable.


**Project:** ADHD-VTD / VTD-Edge / PARS-SQL  
**Goal:** Build a Persian-first, privacy-preserving, research-grade Text-to-SQL system for mental-health / student-lifestyle analytics.  
**Target quality:** From working MVP → publishable research system → state-of-the-art-style local/edge NL2SQL framework.  
**Architecture style:** Compiler-like, graph-orchestrated, schema-grounded, retrieval-augmented, self-correcting Text-to-SQL.

---

## 0. Current Project Status

The project already has a strong foundation:

```text
ADHD-VTD/
├── data/
│   ├── db/
│   ├── schema/
│   ├── questions/
│   ├── golden_sql/
│   └── rag/
├── docs/
├── models/
├── results/
├── scripts/
├── src/
│   ├── config/
│   ├── core/
│   ├── db/
│   ├── evaluation/
│   ├── generation/
│   ├── graph/
│   ├── nlu/
│   ├── output/
│   ├── reflexion/
│   ├── retrieval/
│   ├── schema/
│   ├── sql_validation/
│   └── utils/
└── tests/
```

Already created or bootstrapped:

```text
✅ Project structure
✅ data/schema/*.json
✅ data/golden_sql/*.jsonl
✅ data/rag/indexed_examples.jsonl
✅ src/config/paths.py
✅ src/config/settings.py
✅ src/core/types.py
✅ src/nlu/persian_normalizer.py
✅ src/nlu/number_normalizer.py
✅ src/nlu/date_normalizer.py
✅ src/db/schema_inspector.py
✅ src/schema/schema_loader.py
✅ src/schema/schema_registry.py
✅ src/schema/schema_linker.py
✅ basic schema linker test
✅ src/generation/local_llm.py (GPU-accelerated)
✅ src/sql_validation/validation_pipeline.py
✅ src/graph/workflow.py (LangGraph Agent)
✅ scripts/run_agent.py (CLI Entry point)
```

The next goal is to convert this foundation into a complete, tested, benchmarked, reproducible, and publishable system.

---

# Roadmap Overview

The roadmap is divided into 15 phases:

```text
Phase 0   Project governance and source-of-truth cleanup
Phase 1   Environment, reproducibility, and config hardening
Phase 2   Data/schema quality foundation
Phase 3   Persian NLU and intent routing
Phase 4   Schema linking v2 and query planning
Phase 5   SQL validation and read-only execution [COMPLETED]
Phase 6   Minimal local LLM Text-to-SQL pipeline [COMPLETED]
Phase 7   Hybrid CAG/RAG retrieval
Phase 8   LangGraph orchestration [COMPLETED]
Phase 9   Reflexion, SQL Surgeon, and semantic critic [BETA - Basic logic in Graph]
Phase 10  Benchmark runner and evaluation framework
Phase 11  Ablation, error analysis, and research metrics
Phase 12  Output, chart recommendation, and data storytelling
Phase 13  Optimization, robustness, and edge-readiness
Phase 14  State-of-the-art upgrades
Phase 15  Research packaging, paper, GitHub, and PhD portfolio
```

Recommended implementation principle:

> Build a thin vertical slice first, then improve each component with measurable ablations.

---

# Phase 0 - Project Governance and Source-of-Truth Cleanup

## Goal

Make the project understandable to yourself, LLMs, future collaborators, and paper reviewers.

## Why This Phase Matters

If documentation, folder structure, datasets, and implementation paths disagree, the system becomes hard to debug and impossible to reproduce.

## Tasks

### 0.1 Finalize documentation index

Update `docs/00_INDEX.md` to include:

```markdown
| `08_PROJECT_STRUCTURE_AND_FILE_MAP.md` | Canonical folder structure, module responsibilities, and path conventions |
| `09_DATASET_AND_EVALUATION_FILES_GUIDE.md` | Dataset files, golden examples, few-shot bank, behavioral evaluation, and benchmark usage |
| `10_FULL_DEVELOPMENT_ROADMAP_ZERO_TO_SOTA.md` | Full phased roadmap from MVP to state-of-the-art system |
```

### 0.2 Mark old docs as legacy

If `docs/Developer Documents/` still exists, create:

```text
docs/Developer Documents/README.md
```

Suggested content:

```markdown
# Legacy Developer Documents

These files are historical references. The current source of truth is the Research-Grade documentation suite in `docs/00_INDEX.md` and the current `src/`-based project structure.
```

### 0.3 Confirm canonical source layout

Current canonical layout:

```text
src/nlu              Persian understanding
src/schema           schema linking and join reasoning
src/retrieval        RAG/CAG, BM25, vector retrieval, reranking
src/generation       prompt building, local LLM, output parsing
src/sql_validation   SQL syntax/schema/safety/semantic validation
src/db               SQLite read-only execution and schema inspection
src/reflexion        critic, repair, retry memory
src/graph            LangGraph orchestration
src/output           Persian answer, chart, narrative, XAI
src/evaluation       benchmark, ablation, metrics, reports
src/core             types, contracts, enums, exceptions
src/config           settings, paths, feature flags
src/utils            shared utilities
```

## Deliverables

```text
[ ] docs/00_INDEX.md updated
[ ] docs/08_PROJECT_STRUCTURE_AND_FILE_MAP.md added
[ ] docs/09_DATASET_AND_EVALUATION_FILES_GUIDE.md added
[ ] docs/10_FULL_DEVELOPMENT_ROADMAP_ZERO_TO_SOTA.md added
[ ] legacy docs clearly marked
```

## Definition of Done

A new LLM or developer can understand the project structure in under 10 minutes.

---

# Phase 1 - Environment, Reproducibility, and Config Hardening

## Goal

Ensure that the project runs predictably on Windows with Python 3.12 and can be reproduced later.

## Tasks

### 1.1 Freeze working requirements

After successful install:

```powershell
pip freeze > requirements-lock-working.txt
```

Keep:

```text
requirements.txt                  editable direct dependencies
requirements-lock-working.txt     exact working environment snapshot
```

### 1.2 Add project path bootstrap for scripts

Already created:

```text
scripts/_bootstrap_path.py
```

Use this pattern in every script under `scripts/`:

```python
from _bootstrap_path import PROJECT_ROOT
```

### 1.3 Harden `.env.example`

Must include:

```env
VTD_DB_PATH=data/db/vtd_health_research_v1.db
VTD_SCHEMA_PATH=data/db/vtd_health_research_schema.sql
VTD_SCHEMA_SNAPSHOT_PATH=data/schema/schema_snapshot.json
VTD_SCHEMA_GRAPH_PATH=data/schema/schema_graph.json
VTD_COLUMN_ALIASES_PATH=data/schema/column_aliases.fa.json
VTD_BUSINESS_GLOSSARY_PATH=data/schema/business_glossary.fa.json
VTD_METRIC_DEFINITIONS_PATH=data/schema/metric_definitions.json
VTD_GOLDEN_EXAMPLES_PATH=data/golden_sql/golden_examples.jsonl
VTD_INDEXED_EXAMPLES_PATH=data/rag/indexed_examples.jsonl
VTD_CHROMA_PATH=data/rag/chroma
VTD_MAIN_LLM_PATH=models/qwen2.5-coder-7b-instruct-q4_k_m.gguf
VTD_FALLBACK_LLM_PATH=models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf
VTD_EMBEDDING_MODEL_PATH=models/embedding/multilingual-e5-small
VTD_RERANKER_MODEL_PATH=models/reranker/bge-reranker-base
VTD_MAX_RETRIES=3
VTD_DEFAULT_LIMIT=100
VTD_LOG_LEVEL=INFO
```

### 1.4 Add smoke test script

Create:

```text
scripts/smoke_test_environment.py
```

It should check:

```text
Python version
DB exists
schema files exist
models exist
imports work
sqlite opens read-only
schema linker returns columns
```

## Deliverables

```text
[ ] requirements-lock-working.txt
[ ] scripts/smoke_test_environment.py
[ ] .env.example complete
[ ] imports work from scripts
```

## Acceptance Criteria

```powershell
python scripts/smoke_test_environment.py
```

returns:

```text
✅ Python OK
✅ DB OK
✅ Schema artifacts OK
✅ Models visible
✅ Core imports OK
✅ Read-only SQLite OK
✅ Schema linker OK
```

---

# Phase 2 - Data and Schema Quality Foundation

## Goal

Make schema and benchmark files trustworthy before adding LLM complexity.

## Tasks

### 2.1 Compare manual schema snapshot and generated schema snapshot

Create:

```text
scripts/compare_schema_snapshots.py
```

Compare:

```text
data/schema/schema_snapshot.json
data/schema/schema_snapshot.generated.json
```

Detect:

```text
missing tables
missing columns
extra hallucinated columns
type mismatches
foreign key mismatches
```

### 2.2 Generate schema documentation

Create:

```text
scripts/export_schema_markdown.py
```

Output:

```text
docs/generated/SCHEMA_REFERENCE.md
```

Each table should include:

```text
table name
description
columns
types
semantic type
aliases
common question examples
join paths
anti-hallucination notes
```

### 2.3 Validate dataset SQL against DB

Create:

```text
scripts/validate_dataset_sql.py
```

Input:

```text
data/questions/full/vtd_total_500_dataset_package.json
```

Validate:

```text
all positive SQLs parse
all positive SQLs are SELECT-only
all positive SQLs execute
all referenced tables exist
all referenced columns exist
behavioral examples do not require SQL when should_generate_sql=false
```

Output:

```text
results/data_quality/dataset_sql_validation_report.md
results/data_quality/invalid_examples.jsonl
```

### 2.4 Convert JSON to JSONL

Create:

```text
scripts/convert_dataset_to_jsonl.py
```

Outputs:

```text
data/questions/full/vtd_total_500_dataset_package.jsonl
data/questions/full/vtd_question_sql_400_merged_validated.jsonl
data/questions/special/vtd_evaluation_special_100.jsonl
```

## Deliverables

```text
[ ] schema diff report
[ ] generated schema reference
[ ] dataset validation report
[ ] JSONL copies of datasets
```

## Acceptance Criteria

```text
100% positive SQL examples are SELECT-only
100% executable positive SQLs either pass or are documented as invalid
0 undocumented schema mismatch
```

---

# Phase 3 - Persian NLU and Intent Routing

## Goal

Before generating SQL, the system must understand whether SQL should be generated at all.

## Components

```text
src/nlu/persian_normalizer.py       already started
src/nlu/number_normalizer.py        already started
src/nlu/date_normalizer.py          already started
src/nlu/colloquial_mapper.py
src/nlu/term_extractor.py
src/nlu/intent_classifier.py
src/nlu/ambiguity_detector.py
src/nlu/safety_intent_detector.py
```

## Tasks

### 3.1 Persian normalizer tests

Create:

```text
tests/tier1_unit/test_persian_normalizer.py
```

Test:

```text
ك → ک
ي → ی
ى → ی
ZWNJ → space
diacritics removed
punctuation normalized
extra spaces removed
```

### 3.2 Number normalizer tests

Create:

```text
tests/tier1_unit/test_number_normalizer.py
```

Test:

```text
۱۲۳ → 123
١٢٣ → 123
۶.۵ → 6.5
شش → 6 when replace_words=True
```

### 3.3 Date normalizer v1

Support deterministic patterns first:

```text
1404/01/15
۱۴۰۴-۰۱-۱۵
فروردین ۱۴۰۴
سال ۱۴۰۴
```

For vague dates:

```text
ترم قبل
ماه قبل
چند وقت اخیر
اخیراً
```

return clarification-needed unless academic calendar is configured.

### 3.4 Intent classifier v1

Rule-first classifier:

```text
count_query
aggregation_query
grouping_query
ranking_query
comparison_query
trend_query
raw_data_query
chart_request
definition_query
clarification_required
out_of_schema_query
unsafe_query
no_sql_writing_request
```

### 3.5 Ambiguity detector v1

Ask clarification for:

```text
بهترین / بدترین without metric
وضعیت دانشجوها چطوره؟
یه آمار کلی بده
top 10 without metric
time expression without deterministic range
chart request without measure/dimension
```

### 3.6 Safety intent detector

Reject or route away from SQL for:

```text
DROP
DELETE
UPDATE
INSERT
ALTER
CREATE
PRAGMA
ATTACH
DETACH
ignore schema
make up a column
leak private records
```

## Deliverables

```text
[ ] intent_classifier.py implemented
[ ] ambiguity_detector.py implemented
[ ] safety_intent_detector.py implemented
[ ] unit tests for each
[ ] 100 behavioral examples covered
```

## Acceptance Criteria

```text
Intent accuracy on labeled 500 dataset: >= 90%
Safety rejection on adversarial examples: 100%
Clarification decision on ambiguous examples: >= 90%
```

---

# Phase 4 - Schema Linking v2 and Query Planning

## Goal

Move from alias matching to a measurable schema-linking and query-planning layer.

## Current Status

Basic schema linker works on core examples:

```text
زن/مرد → individuals_core.gender
افسردگی → clinical_assessments.depression_diagnosis + phq9_score
اضطراب → clinical_assessments.anxiety_diagnosis + gad7_score
دانشجو → student_metrics.user_id
معدل → student_metrics.cgpa
خواب → lifestyle_risk_factors.sleep_hours
```

## Tasks

### 4.1 Expand alias dictionary

Update:

```text
data/schema/column_aliases.fa.json
```

Add:

```text
دانشجویان، دانشجوها، بچه‌ها، محصل، student
دختر، دختران، زن، female
پسر، پسران، مرد، male
افسرده، افسوردگی، دیپرشن، depressed
مضطرب، anxiety
کم خواب، کم‌خواب، خواب کم
معدل، جی پی ای، gpa, cgpa
نمره امتحان، exam score
فشار مالی، financial stress
فشار تحصیلی، academic pressure
```

### 4.2 Add concept layer

Create:

```text
src/schema/concept_registry.py
```

Concepts:

```text
depression
anxiety
student
female
male
cgpa
sleep
stress
financial_stress
academic_pressure
```

### 4.3 Query Intermediate Representation v1

Create:

```text
src/core/query_ir.py
```

Fields:

```text
task_type
metric
dimensions
filters
aggregation
time_range
expected_result_shape
chart_intent
should_generate_sql
```

### 4.4 Query planner v1

Create:

```text
src/schema/query_planner.py
```

Input:

```text
normalized question
intent
linked schema
```

Output:

```text
QIR
```

### 4.5 Schema linking evaluation

Create:

```text
src/evaluation/schema_linking_metrics.py
scripts/evaluate_schema_linker.py
```

Metrics:

```text
table precision
column precision
table recall
column recall
F1
unresolved term rate
false positive column rate
```

## Deliverables

```text
[ ] expanded aliases
[ ] concept registry
[ ] QIR model
[ ] query planner
[ ] schema-linking evaluation script
```

## Acceptance Criteria

```text
Column recall >= 90% on positive examples
False-positive critical columns <= 5%
Known anti-hallucination examples pass
```

---

# Phase 5 - SQL Validation and Read-Only Execution

## Goal

Generated SQL must be treated as untrusted. Validation is deterministic first, LLM-assisted only later.

## Components

```text
src/sql_validation/syntax_validator.py
src/sql_validation/safety_validator.py
src/sql_validation/schema_validator.py
src/sql_validation/semantic_validator.py
src/sql_validation/sql_rewriter.py
src/sql_validation/validation_result.py
src/db/read_only_executor.py
src/db/sqlite_connection.py
src/db/result_serializer.py
```

## Tasks

### 5.1 Syntax validator

Use `sqlglot`.

Check:

```text
parseable SQL
SQLite dialect
single statement
no broken parentheses
no markdown fences
```

### 5.2 Safety validator

Reject:

```text
INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, REPLACE, MERGE
ATTACH, DETACH, PRAGMA, VACUUM, REINDEX
multiple statements
comments with injection content
SELECT * when disabled
```

### 5.3 Schema validator

Check:

```text
tables exist
columns exist
aliases resolve
no hallucinated table
no hallucinated column
join columns exist
```

### 5.4 Join validator

Check joins against:

```text
data/schema/schema_graph.json
```

Reject:

```text
cross joins unless explicitly allowed
join without known path
join on unrelated columns
```

### 5.5 Aggregation validator

Check:

```text
GROUP BY required dimensions
no AVG over categorical labels
COUNT is allowed
ranking has ORDER BY + LIMIT
raw retrieval has LIMIT
```

### 5.6 Read-only executor

Use SQLite URI:

```text
file:path/to/db?mode=ro
```

Add:

```text
timeout
row limit
result serialization
result hash
execution time
```

## Deliverables

```text
[ ] syntax validator
[ ] safety validator
[ ] schema validator
[ ] semantic validator v1
[ ] read-only executor
[ ] validator tests
```

## Acceptance Criteria

```text
100% unsafe examples rejected
100% fake columns detected
100% fake tables detected
valid gold SQL executes read-only
```

---

# Phase 6 - Minimal Local LLM Text-to-SQL Pipeline

## Goal

Create the first end-to-end pipeline:

```text
question → normalize → intent → schema link → prompt → local LLM → parse → validate → execute → answer
```

## Components

```text
src/generation/local_llm.py
src/generation/llm_engine.py
src/generation/prompt_builder.py
src/generation/output_parser.py
src/generation/prompts/sql_generation.j2
src/output/answer_formatter.py
scripts/run_query.py
```

## Tasks

### 6.1 Local LLM engine

Support:

```text
llama-cpp-python
Qwen2.5-Coder-7B GGUF
Qwen3 4B fallback
configurable context length
temperature 0.0-0.2
JSON-only output preference
```

### 6.2 Output parser

Parse:

```json
{
  "sql": "SELECT ...",
  "confidence": 0.82,
  "assumptions": [],
  "used_tables": [],
  "used_columns": [],
  "result_shape": "single_value",
  "needs_clarification": false,
  "clarification_question": null
}
```

Must handle:

```text
markdown fences
extra prose
invalid JSON
missing sql field
empty SQL
```

### 6.3 Prompt builder v1

Prompt sections:

```text
SYSTEM RULES
LINKED SCHEMA
JOIN HINTS
BUSINESS RULES
CURRENT QUESTION
OUTPUT JSON CONTRACT
```

### 6.4 `scripts/run_query.py`

Usage:

```powershell
python scripts/run_query.py "میانگین معدل دانشجویان مرد را بده"
```

Output:

```text
normalized question
intent
linked tables/columns
generated SQL
validation result
execution result
final answer
```

## Deliverables

```text
[ ] local_llm.py
[ ] prompt_builder.py
[ ] output_parser.py
[ ] run_query.py
[ ] smoke tests on 20 easy examples
```

## Acceptance Criteria

```text
At least 20 easy SQL-positive queries run end-to-end
Valid SQL Rate >= 70% on easy sample
No unsafe SQL reaches executor
```

---

# Phase 7 - Hybrid CAG/RAG Retrieval

## Goal

Improve local LLM accuracy by injecting high-value context only.

## Components

```text
src/retrieval/embedding_model.py
src/retrieval/chroma_store.py
src/retrieval/bm25_index.py
src/retrieval/hybrid_retriever.py
src/retrieval/reranker.py
src/retrieval/context_builder.py
src/retrieval/retrieval_scorer.py
scripts/build_rag_index.py
scripts/test_retrieval.py
```

## Retrieval Channels

```text
1. schema context from schema linker
2. golden examples
3. SQL skeletons
4. business rules
5. optional error memory later
```

## Tasks

### 7.1 Golden examples normalization

Ensure `data/golden_sql/golden_examples.jsonl` contains:

```text
id
question_fa
normalized_question
intent
tables
columns
sql
sql_skeleton
difficulty
recommended_visual
notes
```

### 7.2 Build BM25 index

Input:

```text
data/rag/indexed_examples.jsonl
```

Output:

```text
data/rag/bm25/index.pkl
```

### 7.3 Build Chroma vector index

Collection:

```text
vtd_golden_examples
```

Use:

```text
models/embedding/multilingual-e5-small
```

### 7.4 Hybrid score fusion

Start with:

```text
score = 0.30 * semantic_similarity
      + 0.25 * lexical_bm25_score
      + 0.20 * schema_overlap
      + 0.15 * intent_match
      + 0.10 * skeleton_match
```

Make weights configurable through YAML.

### 7.5 Diversity filter

Rules:

```text
max 2 examples with same skeleton
max 2 examples with same main table set
prefer same intent
prefer same metric
prefer different difficulty if useful
```

### 7.6 Retrieval evaluation

Metrics:

```text
Recall@3 schema
Recall@5 schema
Intent@k
Skeleton@k
MRR
Diversity score
```

## Deliverables

```text
[ ] BM25 retriever
[ ] Chroma retriever
[ ] hybrid fusion
[ ] context builder
[ ] retrieval evaluation report
```

## Acceptance Criteria

```text
Schema Recall@3 >= 80%
Intent@3 >= 80%
Retrieval improves EX over no-RAG baseline
```

---

# Phase 8 - LangGraph Orchestration

## Goal

Replace linear scripts with a stateful, debuggable, retry-aware graph.

## Components

```text
src/graph/state.py
src/graph/routes.py
src/graph/workflow.py
src/graph/checkpoints.py
src/graph/nodes/*.py
```

## Graph Flow

```text
initialize_trace
→ normalize_input
→ classify_intent
→ build_qir
→ route_pre_generation
→ link_schema
→ retrieve_context
→ build_prompt
→ generate_sql
→ parse_llm_output
→ validate_sql
→ execute_sql
→ semantic_result_check
→ format_answer
→ recommend_chart
→ log_benchmark_record
```

Alternative routes:

```text
unsafe → reject_safely
ambiguous → ask_clarification
out_of_schema → explain_scope_limitation
invalid_sql → try_surgeon or critic loop
max_retries → fail_gracefully
```

## Tasks

### 8.1 Implement graph state

Use existing `src/core/types.py`, but create graph-specific state:

```text
src/graph/state.py
```

### 8.2 Implement nodes as thin wrappers

Each node should call existing services:

```text
normalize_node.py → PersianNormalizer
schema_linking_node.py → SchemaLinker
retrieval_node.py → HybridRetriever
generation_node.py → LocalLLM + PromptBuilder
validation_node.py → validators
execution_node.py → ReadOnlyExecutor
```

### 8.3 Add checkpointing

Use SQLite checkpointing for:

```text
trace replay
benchmark debugging
failed case reproduction
```

### 8.4 Generate graph diagram

Create:

```text
scripts/export_graph_diagram.py
```

Output:

```text
docs/generated/langgraph_workflow.mmd
```

## Deliverables

```text
[ ] VTDState
[ ] graph nodes
[ ] routing functions
[ ] compiled graph
[ ] checkpointing
[ ] graph diagram
```

## Acceptance Criteria

```text
python scripts/run_query.py works through LangGraph
Each query produces trace_id
Each failed query stores attempts
```

---

# Phase 9 - Reflexion, SQL Surgeon, and Semantic Critic

## Goal

Improve final execution accuracy by repairing invalid or semantically wrong SQL.

## Components

```text
src/reflexion/critic.py
src/reflexion/repair_planner.py
src/reflexion/transition_memory.py
src/reflexion/error_taxonomy.py
src/reflexion/retry_policy.py
src/sql_validation/sql_rewriter.py
src/sql_validation/semantic_validator.py
```

## Tasks

### 9.1 Error taxonomy

Categories:

```text
OUTPUT_FORMAT_ERROR
SYNTAX_ERROR
SAFETY_ERROR
SCHEMA_TABLE_ERROR
SCHEMA_COLUMN_ERROR
JOIN_ERROR
AGGREGATION_ERROR
TYPE_ERROR
SEMANTIC_ERROR
EMPTY_RESULT_WARNING
TIMEOUT_ERROR
AMBIGUITY_ERROR
LOOP_DETECTED
```

### 9.2 SQL Surgeon v1

Allowed deterministic repairs:

```text
strip markdown fences
remove trailing semicolon
add LIMIT for raw retrieval
replace gpa → cgpa if schema confirms
fix simple alias errors
add missing GROUP BY when dimension is clear
```

Not allowed:

```text
guessing a metric
inventing join path
changing depression to anxiety
adding unknown columns
```

### 9.3 Critic feedback builder

Input:

```text
question
QIR
linked schema
failed SQL
validation errors
previous attempts
```

Output:

```text
structured repair instruction
```

### 9.4 Anti-loop memory

Stop if:

```text
same SQL generated twice
same error type appears 3 times
SQL similarity > 0.92 and error unchanged
invalid JSON twice
surgeon repair makes SQL worse
```

### 9.5 Semantic validator

Check:

```text
QIR aggregation matches SQL aggregation
QIR metric appears in SQL
QIR dimension appears in SELECT/GROUP BY
ranking has ORDER BY and LIMIT
expected result shape matches actual result
```

## Deliverables

```text
[ ] critic
[ ] repair planner
[ ] SQL surgeon
[ ] anti-loop detection
[ ] semantic validator
[ ] retry route in graph
```

## Acceptance Criteria

```text
Retry Success Rate measured
Reflexion improves EX@final over EX@first
No infinite retry loop
```

---

# Phase 10 - Benchmark Runner and Evaluation Framework

## Goal

Turn the project from an app into a measurable research system.

## Components

```text
src/evaluation/benchmark_runner.py
src/evaluation/metrics.py
src/evaluation/error_analyzer.py
src/evaluation/report_generator.py
scripts/run_benchmark.py
```

## Tasks

### 10.1 Dataset loader

Support:

```text
vtd_total_500_dataset_package.json/jsonl
vtd_question_sql_400_merged_validated.json/jsonl
vtd_evaluation_special_100.json/jsonl
```

### 10.2 Benchmark modes

```text
positive_sql_only
behavioral_eval_only
full_500
sample_n
by_difficulty
by_category
by_intent
```

### 10.3 Metrics

Main:

```text
Execution Accuracy
Exact Match
Valid SQL Rate
Intent Accuracy
Schema Linking Accuracy
Safety Rejection Accuracy
Clarification Accuracy
No-SQL Action Accuracy
Retry Success Rate
Latency median/p95
```

### 10.4 Execution comparison

Compare generated SQL result with gold SQL result:

```text
normalize rows
sort if order not semantically relevant
compare scalar/rows/tables
handle floating tolerance
```

### 10.5 Benchmark output folder

Each run:

```text
results/benchmark/{timestamp}_{config_id}/
├── config.json
├── predictions.jsonl
├── benchmark_results.csv
├── summary.md
├── failures.jsonl
├── attempts.jsonl
├── retrieval_metrics.csv
├── schema_linking_metrics.csv
├── error_taxonomy.csv
└── paper_tables.md
```

## Deliverables

```text
[ ] benchmark runner
[ ] metrics module
[ ] reports
[ ] failure logs
[ ] sample benchmark run
```

## Acceptance Criteria

```text
Can run 20-sample benchmark
Can run full 500 benchmark
Every result is traceable
Every failure has reason
```

---

# Phase 11 - Ablation, Error Analysis, and Research Metrics

## Goal

Prove which components actually improve the system.

## Ablation Matrix

```text
A0 Rule-only / templates
A1 Local LLM zero-shot with full schema
A2 + Persian normalization
A3 + schema linking
A4 + golden examples RAG
A5 + hybrid retrieval
A6 + QIR
A7 + Reflexion
A8 + SQL Surgeon
A9 Full PARS-SQL
```

## Tasks

### 11.1 Experiment configs

Create YAML files:

```text
experiments/configs/A0_rule_only.yaml
experiments/configs/A1_zero_shot.yaml
experiments/configs/A2_norm.yaml
experiments/configs/A3_schema_linking.yaml
experiments/configs/A4_rag_examples.yaml
experiments/configs/A5_hybrid_retrieval.yaml
experiments/configs/A6_qir.yaml
experiments/configs/A7_reflexion.yaml
experiments/configs/A8_surgeon.yaml
experiments/configs/A9_full.yaml
```

### 11.2 Ablation runner

Create:

```text
scripts/run_ablation.py
src/evaluation/ablation_runner.py
```

### 11.3 Statistical tests

Create:

```text
src/evaluation/statistical_tests.py
```

Support:

```text
bootstrap confidence interval
McNemar test
per-difficulty significance
```

### 11.4 Error analysis report

Generate:

```text
results/error_analysis/{timestamp}/error_report.md
```

Breakdown:

```text
intent error
schema linking error
retrieval error
SQL syntax error
wrong aggregation
wrong filter
join error
semantic metric error
safety failure
clarification failure
```

## Deliverables

```text
[ ] ablation configs
[ ] ablation runner
[ ] statistical tests
[ ] error report
[ ] paper-ready tables
```

## Acceptance Criteria

```text
Ablation table is generated automatically
EX@final reported with confidence intervals
At least 20 representative failures documented
```

---

# Phase 12 - Output, Chart Recommendation, and Data Storytelling

## Goal

Make the system useful as an intelligent dashboard backend, not just an SQL generator.

## Components

```text
src/output/answer_formatter.py
src/output/chart_recommender.py
src/output/narrative_generator.py
src/output/explanation_builder.py
```

## Tasks

### 12.1 Answer formatter

Support:

```text
KPI answer
table answer
ranking answer
distribution answer
empty result answer
clarification answer
unsafe/out-of-schema answer
```

### 12.2 Chart recommender

Rules:

```text
single scalar → kpi
category + count → bar
time + metric → line
two numeric variables → scatter
part-to-whole with few categories → bar preferred, pie optional only if explicitly allowed
top N → horizontal bar
```

### 12.3 Explanation builder

Include:

```text
which metric was used
which filters were applied
which tables were joined
main assumptions
confidence
trace_id
```

### 12.4 Storytelling hint

Use dataset metadata:

```text
recommended_visual
storytelling_hint_fa
```

## Deliverables

```text
[ ] chart recommender
[ ] Persian answer formatter
[ ] explanation builder
[ ] output tests
```

## Acceptance Criteria

```text
Chart accuracy >= 85% on chart evaluation examples
No hallucinated narrative beyond result
Persian answer is concise and traceable
```

---

# Phase 13 - Optimization, Robustness, and Edge-Readiness

## Goal

Make the system fast, stable, and usable on local/edge machines.

## Tasks

### 13.1 Caching

Cache:

```text
normalized question
schema linking result
retrieval result
LLM prompt hash
successful SQL per question fingerprint
```

### 13.2 Latency optimization

Measure:

```text
normalization latency
schema linking latency
retrieval latency
LLM latency
validation latency
execution latency
end-to-end latency
```

### 13.3 Model comparison

Compare:

```text
Qwen2.5-Coder-7B
Qwen3-4B
Qwen3.5-4B
possibly smaller coding models if available locally
```

Metrics:

```text
EX
Valid SQL Rate
Latency
VRAM/RAM
tokens/sec
retry rate
```

### 13.4 Robustness tests

Test:

```text
typos
Finglish
colloquial Persian
mixed Persian-English
ambiguous prompts
unsafe prompts
out-of-schema prompts
long noisy prompts
prompt injection
```

## Deliverables

```text
[ ] latency profiler
[ ] cache layer
[ ] model comparison report
[ ] robustness report
```

## Acceptance Criteria

```text
Median latency acceptable for CLI/demo
No unsafe SQL executes
Robustness report generated
```

---

# Phase 14 - State-of-the-Art Upgrades

## Goal

Move from research-grade to SOTA-style architecture.

This does not necessarily mean beating all global benchmarks. It means adopting the strongest patterns from modern Text-to-SQL systems and making them work in a Persian, privacy-preserving, local setting.

## Upgrade 14.1 Multi-candidate generation + ranking

Instead of one SQL:

```text
generate N candidates
validate all
execute safe candidates
rank by semantic alignment
choose best
```

Candidate sources:

```text
LLM candidate 1 low temperature
LLM candidate 2 different prompt
skeleton-based candidate
retrieval-nearest SQL adapted candidate
surgeon-repaired candidate
```

## Upgrade 14.2 Cross-consistency execution

For semantically equivalent candidates:

```text
if multiple candidates return same result → increase confidence
if candidates disagree → run semantic critic or ask clarification
```

## Upgrade 14.3 Value retrieval

Before SQL generation, retrieve possible values from DB:

```text
unique gender values
unique category labels
valid country names
valid mental_health_risk values
valid diagnosis values
```

This reduces wrong filters like:

```text
WHERE gender = 'زن'
```

instead of:

```text
WHERE gender = 'Female'
```

## Upgrade 14.4 Schema graph embeddings

Create embeddings for:

```text
table descriptions
column descriptions
business concepts
aliases
join paths
example questions
```

Use graph-aware retrieval:

```text
question → concept candidates → columns → join paths → examples
```

## Upgrade 14.5 Learning-to-rank retriever

Train or tune a reranker using your benchmark:

```text
positive pair: question + correct example
negative pair: question + misleading example
```

Start with heuristic scoring; later use a reranker.

## Upgrade 14.6 Fine-tuning / LoRA / Distillation

Only after benchmark is stable.

Options:

```text
SFT on question → SQL
SFT on question + schema context → JSON SQL contract
LoRA on Qwen coder model if hardware allows
Distill from stronger cloud model using synthetic data only
```

Important:

```text
Do not fine-tune before evaluation is reliable.
Bad gold SQL teaches bad behavior.
```

## Upgrade 14.7 Interactive clarification loop

Support multi-turn:

```text
User: بهترین دانشجوها رو بده
System: منظورتان بهترین از نظر معدل، کمترین افسردگی، بیشترین حضور یا معیار دیگری است؟
User: از نظر معدل
System: generates SQL with cgpa ranking
```

## Upgrade 14.8 Agentic database exploration

For difficult queries:

```text
inspect schema
sample distinct values
check candidate filters
run safe dry-runs
revise query
```

Keep it read-only and bounded.

## Upgrade 14.9 Test-time compute policy

Use more compute only for hard cases:

```text
easy → single candidate
medium → 2 candidates
hard → 3 candidates + semantic critic
complex → multi-candidate + cross-consistency + reflexion
```

## Upgrade 14.10 Benchmark against external standards

Adapt ideas from:

```text
Spider-style exact and execution accuracy
BIRD-style efficiency and external knowledge
Spider 2.0-style real workflow complexity
multilingual Text-to-SQL evaluation
```

But keep your core contribution:

```text
Persian-first
local/private
mental-health/student-lifestyle domain
schema-grounded
reflexive
benchmark-driven
```

## Deliverables

```text
[ ] multi-candidate generator
[ ] candidate ranker
[ ] value retriever
[ ] graph-aware retriever
[ ] reranker training data
[ ] optional LoRA/fine-tuning experiment
[ ] interactive clarification loop
[ ] SOTA comparison report
```

## Acceptance Criteria

```text
Full system beats RAG-only and zero-shot baselines significantly
Hard/complex query performance improves
No increase in unsafe behavior
Latency remains explainable and measured
```

---

# Phase 15 - Research Packaging, Paper, GitHub, and PhD Portfolio

## Goal

Turn the project into a credible research artifact.

## Tasks

### 15.1 GitHub-ready cleanup

Include:

```text
README.md
LICENSE
.env.example
requirements.txt
requirements-lock-working.txt
docs/
scripts/
tests/
small sample DB or synthetic DB
sample benchmark subset
```

Do not include:

```text
large GGUF models
private data
large generated logs
unreviewed clinical claims
```

### 15.2 Reproducibility script

Create:

```text
scripts/reproduce_paper_results.py
```

It should run:

```text
schema validation
data validation
benchmark sample
ablation sample
report generation
```

### 15.3 Paper assets

Create:

```text
docs/paper/
├── method_diagram.mmd
├── architecture_figure.png
├── ablation_table.md
├── error_taxonomy_table.md
├── qualitative_examples.md
└── limitations.md
```

### 15.4 Blog / portfolio series

Suggested posts:

```text
1. Building a Persian Text-to-SQL system for mental-health analytics
2. Why schema linking matters for small local LLMs
3. How Reflexion and SQL validation reduce hallucination
4. Designing a Persian NL2SQL benchmark
5. Running local LLMs for private health data analysis
```

### 15.5 Paper positioning

Candidate title:

```text
PARS-SQL: A Persian-Aware Reflexive Text-to-SQL Framework for Privacy-Preserving Mental Health Data Analysis on Edge Devices
```

Core claims to test:

```text
Persian normalization improves schema linking accuracy.
Schema graph linking reduces hallucinated columns.
Hybrid CAG improves execution accuracy over vector-only RAG.
QIR improves semantic alignment for aggregation and ranking queries.
Reflexion improves final execution accuracy.
SQL Surgeon reduces repair latency compared to LLM-only repair.
```

## Deliverables

```text
[ ] public README
[ ] reproducibility guide
[ ] demo video script
[ ] paper draft
[ ] benchmark report
[ ] ablation report
[ ] GitHub release
```

## Acceptance Criteria

```text
A reviewer can reproduce main results
A PhD supervisor can understand the research contribution
A developer can run demo from README
```

---

# Suggested Timeline

## 12-Week Practical Timeline

```text
Week 1:  Phase 0-1   docs, config, smoke tests
Week 2:  Phase 2     schema/data validation
Week 3:  Phase 3     NLU, intent, ambiguity, safety
Week 4:  Phase 4     schema linking v2 + QIR
Week 5:  Phase 5     SQL validators + read-only executor
Week 6:  Phase 6     minimal local LLM pipeline
Week 7:  Phase 7     hybrid retrieval
Week 8:  Phase 8     LangGraph integration
Week 9:  Phase 9     reflexion + surgeon + semantic critic
Week 10: Phase 10    benchmark runner
Week 11: Phase 11    ablation + error analysis
Week 12: Phase 12-15 packaging, optimization, paper assets
```

## More Realistic 16-Week Research Timeline

```text
Weeks 1-2:    foundation, docs, schema/data QA
Weeks 3-4:    NLU, schema linking, QIR
Weeks 5-6:    SQL validation and executor
Weeks 7-8:    local LLM and minimal pipeline
Weeks 9-10:   RAG/CAG and LangGraph
Weeks 11-12:  reflexion, semantic critic, SQL surgeon
Weeks 13-14:  benchmark, ablation, error analysis
Weeks 15-16:  optimization, paper draft, GitHub release
```

---

# Priority Matrix

## Must-Have for MVP

```text
Persian normalization
schema linking
local LLM generation
SQL validation
read-only execution
run_query.py
```

## Must-Have for Research-Grade

```text
500 benchmark examples
benchmark runner
ablation runner
error taxonomy
retrieval metrics
schema linking metrics
full trace logging
```

## Must-Have for SOTA-Style

```text
multi-candidate generation
value retrieval
cross-consistency
graph-aware schema retrieval
semantic critic
interactive clarification
statistical significance tests
```

---

# Final Target Architecture

```text
Persian user question
  → trace/session manager
  → Persian normalizer
  → number/date normalizer
  → colloquial mapper
  → intent classifier
  → ambiguity/safety router
  → QIR builder
  → schema graph linker
  → value retriever
  → hybrid CAG retriever
  → prompt builder
  → multi-candidate local LLM generator
  → output parser
  → syntax/schema/safety validator
  → SQL surgeon
  → semantic critic
  → read-only executor
  → cross-consistency ranker
  → answer formatter
  → chart/storytelling recommender
  → trace logger
  → benchmark/error analysis store
```

---

# Definition of State-of-the-Art for This Project

The project can be considered SOTA-style when it satisfies all of these:

```text
[ ] End-to-end EX is measured on full 500+ benchmark.
[ ] Full system significantly beats zero-shot and RAG-only baselines.
[ ] Schema linking accuracy is measured separately.
[ ] Retrieval Recall@k is measured separately.
[ ] Reflexion improvement is measured as EX@first vs EX@final.
[ ] Unsafe SQL execution rate is 0.
[ ] Ambiguous/no-SQL behavior is evaluated.
[ ] System runs locally with private DB.
[ ] Every result is reproducible from config.
[ ] Paper tables are generated from actual runs.
[ ] GitHub README can reproduce a sample run.
```

---

# Immediate Next 10 Implementation Tasks

Given the current state, do these next:

```text
1. Create scripts/smoke_test_environment.py
2. Create scripts/compare_schema_snapshots.py
3. Create scripts/validate_dataset_sql.py
4. Create tests for PersianNormalizer, NumberNormalizer, DateNormalizer
5. Implement src/nlu/intent_classifier.py
6. Implement src/nlu/ambiguity_detector.py
7. Implement src/nlu/safety_intent_detector.py
8. Implement src/sql_validation/safety_validator.py
9. Implement src/sql_validation/syntax_validator.py
10. Implement src/db/read_only_executor.py
```

Only after these should you focus heavily on the local LLM.



---

# v2.3 Execution-Ready Roadmap Addendum

## A. Phase 0 Must Happen Before Any New Feature Work

Phase 0 is not documentation work only. It is the execution gate.

Required Phase 0 outputs:

```text
schema_snapshot.generated.json
phase0_50q_audit.csv
phase0_50q_audit_report.md
README.md with Feature Decision Matrix
DATASET_CARD.md
GitHub commit
```

## B. Correct First Build Order

```text
Schema freeze
-> 50Q gold SQL audit
-> Persian/number/date normalizer tests
-> intent/safety/ambiguity router
-> schema/value linker
-> SQL validators
-> read-only executor
-> small-model baseline
-> Milestone 1.5 stress-test
-> CAG/RAG
-> LangGraph research runtime
-> multi-candidate/reliability/reflexion
```

## C. Milestone 1 Is Not Enough

Milestone 1:

```text
50 simple SQL-positive questions
small model 1.5B/1.7B
no CAG
EX@1 >= 40%
Valid SQL Rate >= 70%
```

Milestone 1.5 must immediately follow:

```text
10 Finglish/typo
5 Jalali date
5 unsafe/adversarial
Unsafe rejection = 100%
```

## D. First Paper Scope

Do not run A0-A12 for the first paper unless automation makes it cheap.

Minimum first paper:

```text
A0 direct prompt
A1 + Persian normalization
A2 + schema linking
A3 + value linking
A4 + CAG examples
A7 + validation stack
```

Optional extension:

```text
A8 multi-candidate consistency abstention
```

## E. Supervisor / PhD Portfolio Gate

Before emailing a supervisor, prepare a public GitHub repo with:

```text
README.md
DATASET_CARD.md
schema_snapshot.generated.json
50Q audit report
Milestone 1 or 1.5 report if available
```

A working Phase 0 repository is more persuasive than a long proposal alone.
