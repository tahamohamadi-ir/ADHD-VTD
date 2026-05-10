# 09 - Dataset and Evaluation Files Guide

**Status:** Updated with v2.3 audit, dataset card, human agreement, and reliability evaluation rules  
**Version:** v2.3 Execution-Ready alignment  
**Updated focus:** implementation-first, reliability-first, edge-aware, benchmark-auditable.


## 1. Purpose

This document explains the dataset and evaluation artifacts used in the ADHD-VTD / VTD-Edge Persian NL2SQL project.

The goal is to prevent confusion between:

- positive NL2SQL examples,
- few-shot examples,
- RAG/golden examples,
- behavioral evaluation cases,
- merged benchmark packages,
- schema and metadata artifacts.

This file should be treated as the canonical guide for the contents of `data/questions/`, `data/golden_sql/`, and `data/rag/`.

---

## 2. High-Level Dataset Strategy

The project uses two major kinds of examples:

1. **SQL-positive examples**
   - User question has a valid SQL answer.
   - Used for Text-to-SQL evaluation, RAG retrieval, few-shot prompting, and optional fine-tuning seed data.

2. **Behavioral evaluation examples**
   - User request may be ambiguous, unsafe, out of schema, adversarial, multi-turn, typo-heavy, or chart/storytelling-oriented.
   - Many of these examples intentionally should not generate SQL.
   - Used to evaluate routing, clarification, refusal, safety, hallucination prevention, and chart/storytelling behavior.

---

## 3. Current Canonical File Map

Recommended locations:

```text
ADHD-VTD/
├── data/
│   ├── questions/
│   │   ├── full/
│   │   │   ├── vtd_total_500_dataset_package.json
│   │   │   ├── vtd_question_sql_400_merged_validated.json
│   │   │   └── vtd_question_sql_140_colloquial_additions_validated.json
│   │   │
│   │   └── special/
│   │       └── vtd_evaluation_special_100.json
│   │
│   ├── golden_sql/
│   │   ├── golden_examples.jsonl
│   │   └── few_shot_bank.jsonl
│   │
│   └── rag/
│       └── indexed_examples.jsonl
```

---

## 4. File-by-File Explanation

### 4.1 `vtd_question_sql_400_merged_validated.json`

**Recommended path:**

```text
data/questions/full/vtd_question_sql_400_merged_validated.json
```

**Role:** Main SQL-positive NL2SQL benchmark file.

**Contains:**

- 400 validated Persian question-to-SQL examples.
- Balanced difficulty distribution:
  - 100 easy
  - 100 medium
  - 100 hard
  - 100 complex
- SQLite queries.
- Recommended visualization metadata.
- Storytelling hints.
- Safe SQL flags.

**Use this file for:**

- primary positive NL2SQL evaluation,
- RAG retrieval source,
- few-shot example mining,
- baseline experiments,
- optional synthetic fine-tuning seed data.

**Do not use this file for:**

- testing unsafe requests,
- testing clarification behavior,
- testing out-of-schema rejection,
- testing adversarial prompts.

For those behaviors, use `vtd_evaluation_special_100.json`.

---

### 4.2 `vtd_question_sql_140_colloquial_additions_validated.json`

**Recommended path:**

```text
data/questions/full/vtd_question_sql_140_colloquial_additions_validated.json
```

**Role:** Colloquial Persian extension set.

**Contains:**

- 140 validated examples.
- 35 examples per difficulty level:
  - easy
  - medium
  - hard
  - complex
- More conversational Persian questions.
- Spoken-style user phrasing.
- Validated SQLite SQL.

**Use this file for:**

- testing informal Persian understanding,
- improving Persian NLU coverage,
- augmenting the RAG/few-shot bank,
- stress-testing colloquial query handling.

**Important:**

This file is an addition set, not necessarily the final canonical benchmark by itself.
It should usually be consumed through the merged 400-example file or the total 500 package.

---

### 4.3 `vtd_total_500_dataset_package.json`

**Recommended path:**

```text
data/questions/full/vtd_total_500_dataset_package.json
```

**Role:** Complete packaged dataset for full evaluation.

**Contains:**

- 500 total items.
- 400 SQL-positive examples.
- 100 behavioral evaluation examples.

**Use this file for:**

- complete end-to-end evaluation,
- final benchmark runs,
- reporting full-system behavior,
- paper-ready experiments,
- comparing multiple pipeline configurations.

**Important distinction:**

Not every item in this file should generate SQL.
The evaluator must check fields such as:

```text
should_generate_sql
expected_action
expected_sql
```

A correct system must sometimes generate SQL, sometimes ask clarification, sometimes refuse unsafe SQL, and sometimes answer without SQL.

---

### 4.4 `vtd_evaluation_special_100.json`

**Recommended path:**

```text
data/questions/special/vtd_evaluation_special_100.json
```

**Role:** Behavioral evaluation set.

**Contains:**

- 100 special evaluation examples.
- 25 examples per difficulty level:
  - easy
  - medium
  - hard
  - complex
- Cases for:
  - ambiguity,
  - out-of-schema questions,
  - no-SQL requests,
  - adversarial prompts,
  - hallucination prevention,
  - multi-turn behavior,
  - typo/synonym/Finglish handling,
  - chart recommendation,
  - data storytelling.

**Use this file for:**

- intent routing evaluation,
- safety evaluation,
- clarification evaluation,
- refusal correctness,
- chart/storytelling behavior,
- testing whether the model avoids SQL when SQL is not appropriate.

**Important:**

A high-quality NL2SQL system should not maximize SQL generation on this file.
It should maximize the correct action.

Examples of expected actions:

```text
ask_clarification
refuse_sql_explain_schema_gap
answer_without_sql
refuse_unsafe_sql
refuse_hallucination
generate_sql
answer_chart_recommendation
```

---

### 4.5 `golden_examples.jsonl`

**Recommended path:**

```text
data/golden_sql/golden_examples.jsonl
```

**Role:** Curated high-quality examples for RAG and prompt grounding.

**Contains:**

- Selected question-SQL pairs.
- Usually fewer than the full benchmark.
- Should contain only high-confidence, reusable, representative examples.

**Use this file for:**

- top-quality few-shot examples,
- RAG context examples,
- teaching schema usage patterns,
- teaching preferred SQL style,
- reducing hallucinated columns.

**Selection criteria:**

A row should enter `golden_examples.jsonl` only if it is:

- validated,
- representative,
- schema-consistent,
- safe,
- useful as a pattern for future queries.

**Do not put everything here.**

The full benchmark can contain many examples, but the golden set should stay compact and high-quality.

---

### 4.6 `few_shot_bank.jsonl`

**Recommended path:**

```text
data/golden_sql/few_shot_bank.jsonl
```

**Role:** Prompt-ready few-shot example bank.

**Difference from `golden_examples.jsonl`:**

`golden_examples.jsonl` is the curated source of trusted examples.
`few_shot_bank.jsonl` is optimized for prompt assembly.

It may include additional metadata such as:

```text
intent
difficulty
pattern
sql_skeleton
tables
columns
why_relevant
prompt_text
```

**Use this file for:**

- prompt builder,
- retrieval context packing,
- selecting top-k examples for the LLM,
- building consistent few-shot prompts.

**Rule:**

If an example is wrong in `few_shot_bank.jsonl`, the LLM may learn the wrong behavior.
Validate this file carefully.

---

### 4.7 `indexed_examples.jsonl`

**Recommended path:**

```text
data/rag/indexed_examples.jsonl
```

**Role:** Retrieval-ready representation of examples.

**Contains:**

- text prepared for embedding,
- metadata for filtering,
- SQL or reference ID,
- linked tables/columns if available.

**Use this file for:**

- ChromaDB indexing,
- BM25 indexing,
- hybrid retrieval,
- schema-overlap retrieval,
- RAG evaluation.

**Typical record shape:**

```json
{
  "id": "VTD-001",
  "text_for_embedding": "query: ... intent: ... columns: ...",
  "metadata": {
    "intent": "count",
    "difficulty": "easy",
    "tables": ["student_depression"],
    "columns": ["depression_flag"]
  },
  "sql": "SELECT ..."
}
```

---

## 5. Recommended Source-of-Truth Policy

Use this hierarchy:

```text
vtd_total_500_dataset_package.json
  ├── positive_examples: canonical full SQL-positive set
  └── behavioral evaluation examples: canonical behavioral set

vtd_question_sql_400_merged_validated.json
  └── canonical SQL-positive subset

vtd_evaluation_special_100.json
  └── canonical behavioral evaluation subset

golden_examples.jsonl
  └── curated trusted examples for retrieval/few-shot

few_shot_bank.jsonl
  └── prompt-optimized examples derived from golden/validated data

indexed_examples.jsonl
  └── retrieval-index-ready projection of examples
```

---

## 6. Recommended Naming Rules

### Positive NL2SQL items

Use IDs like:

```text
VTD-001
VTD-002
...
VTD-400
```

### Behavioral evaluation items

Use IDs like:

```text
VTD-EVAL-001
VTD-EVAL-002
...
VTD-EVAL-100
```

### Golden examples

Use IDs like:

```text
gold_001
gold_002
```

or preserve original source IDs:

```text
VTD-001
VTD-017
```

If preserving source IDs, include:

```json
{
  "source_file": "vtd_question_sql_400_merged_validated.json",
  "source_id": "VTD-017"
}
```

---

## 7. How Each Pipeline Component Should Use These Files

| Component | Files Used | Purpose |
|---|---|---|
| Persian NLU | `vtd_evaluation_special_100.json`, colloquial additions | test typos, colloquial expressions, Finglish |
| Schema linker | 400 positive set, golden examples | evaluate expected tables/columns |
| Retriever | `indexed_examples.jsonl`, `golden_examples.jsonl`, `few_shot_bank.jsonl` | retrieve relevant context |
| Prompt builder | `few_shot_bank.jsonl` | inject compact examples |
| SQL generator | retrieved examples + schema context | generate candidate SQL |
| SQL validator | positive examples | validate SQL correctness and safety |
| Behavioral router | special 100 | test clarification/refusal/no-SQL routing |
| Chart recommender | all files with `recommended_visual` | evaluate visualization choice |
| Benchmark runner | total 500 package | full-system evaluation |

---

## 8. Evaluation Rules

### For SQL-positive examples

A correct system should:

1. generate SQL,
2. use only valid schema columns,
3. generate read-only SQLite SELECT,
4. execute successfully,
5. match gold SQL result by Execution Accuracy,
6. optionally match normalized SQL by Exact Match.

### For behavioral evaluation examples

A correct system should follow `expected_action`, not blindly generate SQL.

Examples:

```text
ambiguous → ask clarification
out_of_schema → explain schema gap and do not hallucinate
adversarial → refuse unsafe SQL
no_sql → answer without SQL
chart_storytelling → recommend chart/storytelling approach
multi_turn without context → ask clarification
```

---

## 9. Common Mistakes to Avoid

### Mistake 1: Treating all 500 items as SQL-generation tasks

Wrong.
The total package has both SQL-positive and behavioral examples.
Many behavioral examples intentionally should not generate SQL.

### Mistake 2: Using the whole 400-example file as few-shot context

Wrong.
Only retrieve top-k relevant examples.
Local models are sensitive to prompt noise.

### Mistake 3: Letting wrong examples into `golden_examples.jsonl`

Dangerous.
Golden examples directly influence LLM behavior.
Bad examples cause repeated hallucinations.

### Mistake 4: Confusing `golden_examples.jsonl` and `indexed_examples.jsonl`

`golden_examples.jsonl` is human-curated.
`indexed_examples.jsonl` is retrieval-optimized.

### Mistake 5: Measuring only Execution Accuracy

Insufficient.
Also measure:

```text
Intent Accuracy
Schema Linking Accuracy
Valid SQL Rate
Clarification Accuracy
Safety Rejection Accuracy
No-SQL Action Accuracy
Chart Recommendation Accuracy
Retry Success Rate
```

---

## 10. Recommended Data Quality Checks

Create scripts for:

```text
scripts/validate_dataset.py
scripts/convert_dataset_to_jsonl.py
scripts/build_few_shot_bank.py
scripts/build_indexed_examples.py
scripts/check_gold_sql_execution.py
scripts/check_duplicate_questions.py
scripts/check_schema_column_references.py
```

Minimum checks:

1. Every SQL-positive item has valid SQL.
2. Every positive item has `safe_sql = true`.
3. Every SQL-positive item executes on `vtd_health_research_v1.db`.
4. No exact duplicate question exists.
5. No hallucinated table or column exists in gold SQL.
6. Every behavioral item has `expected_action`.
7. If `should_generate_sql = false`, then `expected_sql` should usually be null.
8. If `should_generate_sql = true`, then `expected_sql` should not be null.
9. `recommended_visual` should be compatible with result shape.
10. All IDs should be unique.

---

## 11. Recommended Future Improvements

1. Convert major JSON files to JSONL for easier streaming and Git diffs.
2. Add `expected_tables` and `expected_columns` to all SQL-positive examples.
3. Add `expected_intent` consistently.
4. Add `sql_skeleton` for each positive example.
5. Add `result_shape` for chart recommendation.
6. Add `requires_clarification_reason` for ambiguous cases.
7. Add `safety_category` for adversarial cases.
8. Add train/dev/test split files.
9. Add benchmark protocol files under `benchmark/protocols/`.
10. Add dataset cards for publication readiness.

---

## 12. Suggested Train/Dev/Test Split

Recommended split for the 400 SQL-positive examples:

```text
train: 280 examples
 dev:  60 examples
 test: 60 examples
```

Recommended split for the 100 behavioral examples:

```text
behavior_dev: 40 examples
behavior_test: 60 examples
```

For paper results, keep the test split fixed and do not tune prompts on it.

---

## 13. Dataset Card Summary

**Dataset name:** VTD Health Intelligent Dashboard NL2SQL Dataset  
**Language:** Persian, with some English/Finglish mixed terms  
**Task:** Persian NL2SQL and behavioral routing for health-dashboard analytics  
**Database:** SQLite, `vtd_health_research_v1.db`  
**Domain:** student lifestyle, mental health, workplace mental health, global prevalence data  
**Main benchmark size:** 500 items  
**SQL-positive examples:** 400  
**Behavioral evaluation examples:** 100  
**Important safety note:** This dataset is for research and educational evaluation. It should not be used for individual medical decision-making.

---

## 14. Where This File Fits in the Documentation Suite

Recommended documentation order:

```text
00_INDEX.md
01_RESEARCH_GRADE_ARCHITECTURE.md
02_LANGGRAPH_WORKFLOW_SPEC.md
03_PERSIAN_NLU_AND_SCHEMA_LINKING.md
04_RAG_CAG_AND_RETRIEVAL_DESIGN.md
05_SQL_GENERATION_VALIDATION_REFLEXION.md
06_EVALUATION_ABLATION_AND_PAPER_PLAN.md
07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md
08_PROJECT_STRUCTURE_AND_FILE_MAP.md
09_DATASET_AND_EVALUATION_FILES_GUIDE.md
```

This file complements `06_EVALUATION_ABLATION_AND_PAPER_PLAN.md` by documenting the actual dataset artifacts and their intended usage.


---

## 15. v2.3 Dataset Governance Additions

### 15.1 Dataset Maturity Levels

| Level | Meaning | Allowed use |
|---|---|---|
| Draft | generated or manually created but not executed | development only |
| SQL-audited | gold SQL executes against current DB | Milestone 1 / SQL evaluation |
| Behavior-audited | expected actions verified | routing/safety evaluation |
| Second-reviewed | reviewed by human 2 or independent judge | paper tables |
| Paper-ready | audited + reviewed + documented limitations | publication |

### 15.2 50-Question Phase 0 Audit

Before pipeline development, select 50 SQL-positive items and verify:

```text
SQL executes
columns/tables exist
question matches SQL intent
visual recommendation matches result shape
no unsafe raw sensitive output
```

Store results in:

```text
data/audit/phase0_50q_audit.csv
data/audit/phase0_50q_audit_report.md
```

### 15.3 Human Agreement / Single-Annotator Limitation

If the benchmark was created by one person, say so.

Minimum paper-ready requirement:

```text
Review at least 50 items with a second person or independent LLM-as-judge.
Report Cohen's Kappa or agreement percentage.
```

Recommended columns:

```text
item_id
reviewer_1_action
reviewer_2_action
action_agreement
sql_alignment_agreement
schema_agreement
notes
```

### 15.4 Reliability Labels

Every behavioral item should support reliability-aware scoring:

```text
should_generate_sql
expected_action
expected_sql
expected_clarification_fa
unsafe_expected
abstention_expected
```

### 15.5 Dataset Card Requirement

Create root-level `DATASET_CARD.md` with:

```text
dataset name
version
schema version
source and generation method
synthetic/de-identified policy
number of SQL-positive examples
number of behavioral examples
annotation/review process
known limitations
clinical disclaimer
license or sharing policy
```

### 15.6 Do Not Treat 500 Items as 500 SQL Tasks

The total package contains SQL-positive and behavioral items. Behavioral items often must not generate SQL. Evaluation must distinguish EX from Reliability Score.
