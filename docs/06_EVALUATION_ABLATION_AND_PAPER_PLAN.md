# 06 - Evaluation, Ablation, Error Analysis, and Paper Plan

**Status:** Finalized evaluation plan aligned with PARS-SQL / VTD-Edge v2.3 Execution-Ready proposal  
**Version:** v2.3 Execution-Ready alignment  
**Updated focus:** reliability-first evaluation, abstention, modular metrics, robustness, human agreement, and realistic first-paper scope.

---

## 1. Why Evaluation Comes First

For a publishable and executable project, architecture alone is not enough. The system must prove that each component improves a measurable outcome.

The evaluation philosophy is:

```text
Do not measure only whether the system answers.
Measure whether it knows when to answer, when to ask clarification, and when to abstain.
```

Required evaluation dimensions:

1. SQL correctness
2. Reliability and abstention
3. Schema/value linking quality
4. Safety and refusal behavior
5. Robustness to Persian variation
6. Latency and edge feasibility
7. Ablation contribution of each component
8. Human agreement / annotation quality
9. Semantic/business correctness of the generated SQL
10. Full prompt/response traceability for every benchmark claim

---

## 2. Benchmark Dataset Design

Current canonical dataset package:

```text
400 SQL-positive examples
100 behavioral evaluation examples
Total: 500 items
```

The 400 SQL-positive examples are used for SQL generation evaluation. The 100 behavioral examples test ambiguity, out-of-schema behavior, no-SQL behavior, adversarial prompts, typo/Finglish, multi-turn behavior, chart selection, and storytelling.

Required fields for SQL-positive examples:

```json
{
  "id": "VTD-001",
  "question_fa": "...",
  "difficulty": "easy | medium | hard | complex",
  "category": "count | average | distribution | ...",
  "pattern": "simple_count | group_count | ...",
  "sql": "SELECT ...",
  "recommended_visual": "kpi | bar | line | ...",
  "safe_sql": true,
  "dialect": "sqlite"
}
```

Required fields for behavioral examples:

```json
{
  "id": "VTD-EVAL-001",
  "evaluation_type": "ambiguous | out_of_schema | no_sql | adversarial | typo_synonym | multi_turn | chart_storytelling",
  "user_utterance_fa": "...",
  "should_generate_sql": false,
  "expected_action": "ask_clarification | refuse_sql_explain_schema_gap | refuse_unsafe_sql | answer_without_sql | generate_sql",
  "expected_sql": null
}
```

---

## 3. Phase 0 Benchmark Audit Before Pipeline Development

Before building the LLM pipeline, run a manual/automated audit on 50 SQL-positive questions.

### Purpose

Avoid building a pipeline around incorrect or schema-misaligned gold SQL.

### Required 50Q audit checks

| Check | Meaning |
|---|---|
| SQL executes | gold SQL runs on current SQLite DB |
| Schema aligned | tables/columns exist in current schema |
| Result shape correct | KPI/table/chart shape matches metadata |
| Visual metadata reasonable | recommended chart fits result shape |
| Persian question aligned | question actually asks what SQL answers |
| No leakage or unsafe field | no sensitive raw data accidentally exposed |

### Deliverable

```text
data/audit/phase0_50q_audit.csv
data/audit/phase0_50q_audit_report.md
```

Do not start CAG/RAG or Reflexion until this audit is clean enough.

---

## 4. Main Metrics

### 4.1 Standard Text-to-SQL Metrics

| Metric | Definition |
|---|---|
| `Execution Accuracy (EX)` | generated SQL result equals gold SQL result |
| `Exact Match (EM)` | generated SQL exactly matches normalized gold SQL |
| `Valid SQL Rate` | SQL parses and executes without error |
| `EX@first_attempt` | execution accuracy before repair/retry |
| `EX@final_attempt` | execution accuracy after validation/repair/reflexion |
| `Latency` | end-to-end runtime |
| `Tokens/sec` | generation speed for local models |

Important separation:

```text
execution_correct != semantic_business_correct
```

`execution_correct` only means the generated SQL result matches the gold SQL result on the current database. `semantic_business_correct` means the SQL logic actually answers the Persian user question. A query may execute and match a result accidentally while still using a wrong metric, wrong filter, or wrong business interpretation. Reports must keep these fields separate.

### 4.2 Reliability Score

Inspired by healthcare Text-to-SQL reliability settings, PARS-SQL uses a Reliability Score that rewards both correct SQL and correct abstention.

For each query:

| Case | Score |
|---|---:|
| SQL should be generated and final SQL is correct | 1.0 |
| SQL should be generated but system abstains incorrectly | 0.0 or partial, depending on policy |
| SQL should not be generated and system correctly abstains/refuses/clarifies | 1.0 |
| SQL should not be generated but system generates SQL | 0.0 |
| SQL executes but semantic critic warns correctly | partial credit if warning is explicit |

A simple implementation:

```text
RS = (Correct_SQL + Correct_Abstention + Correct_Clarification + Correct_Safety_Refusal) / Total_Items
```

Report RS alongside EX. EX alone is not enough for healthcare or mental-health analytics.

### 4.3 Statistical Significance (Bootstrap CI)
To ensure research validity, all primary metrics (EX, RS) must report a 95% Confidence Interval using bootstrapping (e.g., N=1000 resamples). This prevents reporting lucky runs as significant improvements.

### 4.4 Balanced Sampling

For day-to-day debugging, the benchmark runner must support:

```powershell
python scripts/run_benchmark.py --mode agent --dataset dev --samples-per-level 5
```

This selects the same number of examples from each `difficulty` level and records the selection policy in `config.json`. This prevents a sample run from accidentally containing only easy or only complex examples.

### 4.5 Automated Research Artifacts (Benchmark Runner v2.5)

The `run_benchmark.py` runner now automatically generates:
- **`benchmark_results.csv`**: Raw per-case execution results.
- **`reliability_summary.csv`**: Aggregate RS, Abstention, and Error rates.
- **`error_taxonomy.csv`**: Distribution of failures based on the structured taxonomy.
- **`paper_tables.md`**: Publication-ready Markdown tables for EX, RS, and Latency.
- **`attempts.jsonl`**: Full process trace including generation, critic feedback, and repair plan for every iteration.

Required trace fields for paper-grade benchmark runs:

| Artifact | Must include |
|---|---|
| `config.json` | model name/path, model slug, config id, ablation id, module flags, dataset path, selection policy, git commit |
| `predictions.jsonl` | question, normalized question, QIR, linked schema, retrieval context, generated SQL, gold SQL, validation/execution results, final action |
| `attempts.jsonl` | exact prompt, raw model response, parsed payload, SQL, errors, critic feedback, repair plan |
| `summary.md` | model/config/module summary, metric tables, CI, latency summary, failure examples |
| `paper_tables.md` | publication-ready EX, RS, latency, ablation and CI tables |

### 4.6 Abstention Metrics

| Metric | Meaning |
|---|---|
| `Correct Abstention Rate` | unsafe/ambiguous/out-of-schema cases correctly not answered with SQL |
| `False Abstention Rate` | valid SQL questions incorrectly refused |
| `Unsafe Pass-through Rate` | unsafe requests that reach SQL generation/execution; target must be 0 |
| `Clarification Accuracy` | ambiguous cases that ask a useful clarification |
| `Warning Precision` | warnings that correspond to real semantic uncertainty |

---

## 5. Component-Level Modular Metrics

Inspired by modular NL2SQL evaluation frameworks, measure each layer separately.

| Component | Metric |
|---|---|
| Persian normalization | typo/Finglish/date normalization accuracy |
| Intent classifier | intent accuracy |
| Safety router | unsafe rejection accuracy |
| Ambiguity detector | clarification accuracy |
| Schema linker | table/column recall and precision |
| Value linker | value mapping accuracy |
| Retrieval | Schema Recall@k, Value Recall@k, Intent@k, Skeleton@k |
| SQL generator | EX@1, Valid SQL Rate, hallucinated column rate |
| Validator | unsafe SQL catch rate, schema error catch rate |
| SQL Surgeon | deterministic repair success rate |
| Reflexion | retry success rate |
| Output layer | chart recommendation accuracy, storytelling suitability |

---

## 6. Milestone 1 and Milestone 1.5

### Milestone 1: Raw Small-Model Baseline

```text
Model: Qwen2.5-Coder-1.5B or Qwen3-1.7B
Data: 50 simple SQL-positive questions
Pipeline: schema context only, no CAG, no Reflexion
Target: >=40% EX@1 and >=70% Valid SQL Rate
```

This milestone is intentionally small. Passing it does not mean the project is ready for advanced RAG.

### Milestone 1.5: Mini Stress-Test

Before Phase 2/CAG, run:

```text
10 Finglish/typo questions
5 Jalali-date questions
5 unsafe/adversarial questions
```

Pass criteria:

```text
Finglish/typo routing accuracy >= 70%
Jalali safe handling >= 80%
Unsafe rejection accuracy = 100%
No unsafe SQL reaches executor
```

Milestone 1.5 prevents false progress after an easy SQL-only baseline.

---

## 7. Robustness Evaluation

The project must explicitly test robustness, not hide it under colloquial examples.

### 7.1 SQL2NL / Paraphrase Robustness

For selected gold SQL queries, create multiple Persian variants:

```text
formal Persian
colloquial Persian
typo-heavy Persian
Finglish mixed Persian-English
short vague user style
```

Metrics:

```text
EX drop under paraphrase
Schema linking stability
Value linking stability
Intent stability
Abstention stability
```

### 7.2 Persian-Specific Robustness Tags

| Tag | Example |
|---|---|
| `colloquial` | «چندتا دانشجو افسردگی دارن؟» |
| `finglish` | «cgpa بچه‌های depressed چنده؟» |
| `typo` | «افسوردگی دانشجوها چند درصده؟» |
| `jalali_date` | «در فروردین ۱۴۰۴...» |
| `ambiguous_best` | «بهترین دانشجوها رو بده» |

---

## 8. Ablation Study Matrix

Do not run all ablations for the first paper. Split them into Paper 1 and Paper 2.

| ID | Configuration | Persian Norm | Schema/Value Link | CAG | QIR | Validation | Reflexion | Paper Scope |
|---|---|---:|---:|---:|---:|---:|---:|---|
| A0 | Direct prompt + full schema | ❌ | ❌ | ❌ | ❌ | basic | ❌ | Paper 1 |
| A1 | + Persian normalization | ✅ | ❌ | ❌ | ❌ | basic | ❌ | Paper 1 |
| A2 | + schema linking | ✅ | schema only | ❌ | ❌ | basic | ❌ | Paper 1 |
| A3 | + value linking | ✅ | schema+value | ❌ | ❌ | basic | ❌ | Paper 1 |
| A4 | + CAG examples | ✅ | schema+value | examples | ❌ | basic | ❌ | Paper 1 |
| A5 | + SQL skeletons | ✅ | schema+value | examples+skeletons | ❌ | basic | ❌ | Paper 1 |
| A6 | + QIR | ✅ | schema+value | full | ✅ | basic | ❌ | Paper 1 |
| A7 | + validation stack | ✅ | schema+value | full | ✅ | full | ❌ | Paper 1 |
| A8 | + multi-candidate consistency | ✅ | schema+value | full | ✅ | full | ❌ | Paper 2 or extended Paper 1 |
| A9 | + SQL Surgeon | ✅ | schema+value | full | ✅ | full | partial | Paper 2 |
| A10 | + Reflexion loop | ✅ | schema+value | full | ✅ | full | ✅ | Paper 2 |
| A11 | adaptive context compression | ✅ | schema+value | adaptive | ✅ | full | ✅ | Paper 2 |
| A12 | edge state machine | ✅ | schema+value | compressed | ✅ | full | optional | Product/edge paper |

Minimum first-paper ablation:

```text
A0, A1, A2, A3, A4, A7
```

---

## 9. Error Analysis Taxonomy

Every failure must have one primary category and optional secondary categories.

| Category | Description |
|---|---|
| `INTENT_ERROR` | wrong query type |
| `PERSIAN_NORMALIZATION_ERROR` | failed Persian preprocessing |
| `DATE_NORMALIZATION_ERROR` | wrong Jalali/Gregorian mapping |
| `JALALI_MAPPING_ERROR` | unjustified or wrong Jalali range |
| `FINGLISH_RESOLUTION_ERROR` | mixed Persian-English term not resolved |
| `COLLOQUIAL_MISMATCH_ERROR` | colloquial expression misread |
| `SCHEMA_LINKING_ERROR` | wrong table/column mapping |
| `VALUE_LINKING_ERROR` | wrong database value mapping |
| `JOIN_ERROR` | missing/wrong join |
| `SQL_SYNTAX_ERROR` | invalid SQL |
| `AGGREGATION_ERROR` | wrong aggregate/grouping |
| `SEMANTIC_METRIC_ERROR` | wrong metric, e.g. anxiety instead of depression |
| `FILTER_ERROR` | missing/wrong WHERE condition |
| `RAG_RETRIEVAL_ERROR` | retrieved misleading examples |
| `REFLEXION_FAILURE` | failed to repair |
| `SAFETY_FAILURE` | unsafe SQL not rejected |
| `CLARIFICATION_FAILURE` | should have asked user |
| `UNSUPPORTED_QUERY` | query genuinely outside system capacity |

---

## 10. Human Agreement and Dataset Validity

If one person created all benchmark questions, this must be disclosed as a limitation.

Minimum requirement:

```text
At least 50 benchmark items should be reviewed by a second human reviewer
or by an independent **LLM-as-judge** model with a fixed rubric. Current
Phase 16 pilots use OpenRouter-hosted Qwen/DeepSeek as the first open-model
judge pair; expensive closed models should be reserved for small adjudication
subsets.
Report Cohen's Kappa or agreement percentage.
```

### 10.1 LLM-as-a-Judge Protocol (SOTA)
For SOTA evaluation, use a powerful cloud model to evaluate the "Semantic Business Logic" of the generated SQL. The judge receives:
1. User Question (Persian)
2. Linked Schema Context
3. Generated SQL
4. Gold SQL (for reference)
5. Sample Results (top 5 rows)

The judge provides:
- **Correctness Score (0-5)**: Does the SQL logic correctly represent the user's intent?
- **Business Reasoning**: Why is it correct or incorrect from a clinician/analyst perspective?
- **Actionability**: Is the result actually useful for the intended dashboard?

Current implementation note: the Phase 16 judge layer stores provider/model,
prompt version, token usage fields, canonical verdicts and an agreement report
from existing judgment artifacts. Partial/ambiguous rows are kept as review
required; they are not converted into semantic-correct paper claims.
- **Explanation Consistency**: Does the generated answer/explanation match the SQL logic?
- **Redaction Status**: Whether the result sample was redacted or aggregate-only.

Even a low agreement score is better than hiding the limitation.

Recommended review fields:

```text
question_sql_alignment
schema_correctness
expected_action_correctness
visual_recommendation_correctness
ambiguity_label_correctness
unsafe_label_correctness
```

---

## 11. Benchmark Runner Output

Each run should produce a timestamped directory (e.g., `results/benchmark/20260515_070000_agent_dev_qwen/`):
 
 ```text
 results/benchmark/{stamp}_{mode}_{dataset}_{model_slug}_{ablation_id}/
 ├── {prefix}_config.json
 ├── {prefix}_benchmark_results.csv
 ├── {prefix}_reliability_summary.csv
 ├── {prefix}_summary.md
 ├── {prefix}_summary.json
 ├── {prefix}_predictions.jsonl
 ├── {prefix}_failures.jsonl
 ├── {prefix}_attempts.jsonl
 ├── {prefix}_error_taxonomy.csv
 ├── {prefix}_paper_tables.md
 ├── {prefix}_judgments.jsonl              # if --use-judge
 ├── {prefix}_judge_reasoning.md           # if --use-judge
 ├── {prefix}_judge_costs.json             # if --use-judge
 └── {prefix}_semantic_business_summary.csv # if --use-judge
 ```

The folder name and `prefix` must make model/config comparisons easy. At minimum they should encode timestamp, benchmark mode, dataset, model slug and ablation id.

---

## 12. Baselines

### Local operational baselines

```text
Qwen2.5-Coder-0.5B
Qwen2.5-Coder-1.5B
Qwen2.5-Coder-3B
Qwen2.5-Coder-7B
Qwen3-0.6B
Qwen3-1.7B
Qwen3-4B
Phi-4-mini
Llama-3.2-1B
Llama-3.2-3B
SQLCoder-7B
```

### Cloud/API upper-bound baselines

Use only synthetic/de-identified data:

```text
openai/gpt-4.1
deepseek/deepseek-chat
qwen/qwen3-235b-a22b
```

Optional newer baselines may be added if available and documented.

---

## 13. Paper Structure

Suggested first paper title:

> PARS-SQL: A Persian-Aware Reliability-First Text-to-SQL Framework for Privacy-Preserving Mental Health Analytics on Local Devices

Suggested sections:

```text
1. Introduction
2. Related Work
3. Dataset and Annotation Protocol
4. Method
   4.1 Persian Normalization and Value Linking
   4.2 Schema Graph Linking
   4.3 Context-Augmented Retrieval
   4.4 Reliability-Aware SQL Generation
   4.5 Validation and Abstention
5. Experiments
   5.1 Models and Hardware
   5.2 Metrics: EX, RS, Abstention, Robustness
   5.3 Ablation Study
6. Results
7. Error Analysis
8. Ethics and Limitations
9. Conclusion
```

---

## 14. Future Work

1. BIRD-Interact-style evaluation for multi-turn clarification.
2. Process-supervised reward models for SQL repair.
3. Edge state machine benchmark against LangGraph runtime.
4. PostgreSQL/Oracle dialect portability.
5. More human-reviewed clinical-domain evaluation data.
