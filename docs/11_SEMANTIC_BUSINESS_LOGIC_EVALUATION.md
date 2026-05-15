# 11 - Semantic Business Logic Evaluation (LLM-as-a-Judge)

**Status:** Phase 16 specification, not implemented yet  
**Dependency:** Phase 10 must first store complete prompt/response/SQL/result traces.

## 1. Rationale

Execution Accuracy (EX) measures if the SQL returns the same result set as the gold query. However, in complex clinical and mental health domains:
1. Different SQL queries can return the same results on a specific dataset but have different business logic.
2. A query might be "technically correct" (executes) but "conceptually wrong" (e.g., uses the wrong metric for anxiety).
3. The generated explanation might contradict the SQL logic.

To achieve **State-of-the-Art (SOTA)** research quality, we introduce an LLM-as-a-Judge layer.

This layer is intentionally separate from standard benchmark execution:

```text
Execution correctness: Did generated SQL return the same result as gold SQL?
Business correctness: Does generated SQL actually answer the user's question?
```

Both must be reported. Neither replaces the other.

## 2. Methodology

The judge is a high-reasoning model (e.g., GPT-4o, o1-mini, or Claude 3.5 Sonnet) that acts as a "Senior Clinical Data Analyst".

### Input to the Judge
- **Original Persian Question**: Raw user intent.
- **Normalized Context**: The system's understanding of the question.
- **Linked Schema**: Tables and columns used.
- **Generated SQL**: The candidate produced by the local agent.
- **Gold SQL**: The ground-truth reference.
- **Execution Sample or Hash**: Redacted top rows, aggregate preview, or result hash.
- **Validation Trace**: SQL validation issues, repair attempts, and final action.
- **Generated Explanation**: Final answer/explanation shown by the system, if available.

### Judging Rubric (0-5 Scale)
| Score | Label | Description |
|---|---|---|
| 5 | Perfect | Logic is correct, efficient, and perfectly maps to the question. |
| 4 | Correct | Minor stylistic differences or slightly inefficient, but logic is sound. |
| 3 | Minor Logic Error | Result might be correct for this dataset, but the logic has a flaw (e.g., wrong join type). |
| 2 | Major Logic Error | The query uses the wrong columns or metrics but happens to execute. |
| 1 | Execution Failure / Hallucination | The query executes but is completely unrelated to the intent. |
| 0 | Catastrophic | Unsafe, toxic, or total gibberish. |

Required boolean labels:

```text
semantic_business_correct
metric_correct
filter_correct
join_logic_correct
aggregation_correct
answer_explanation_consistent
needs_human_review
```

## 3. Technical Implementation

### Module: `src/evaluation/llm_judge.py`
- Uses `src.config.settings` and environment variables for API keys.
- Must never hardcode API keys or model names in code.
- Provides a common provider interface:
  - `OpenAIJudgeProvider`
  - `LocalJudgeProvider`
  - `MockJudgeProvider` for tests
- Implements batching where provider allows it.
- Supports reasoning summaries: the judge must explain why a score was given.
- Stores token/cost estimates when an online provider is used.

### Integration: `run_benchmark.py --use-judge`
- When enabled, the runner sends failures and a sample of successes to the judge.
- Generates:
  - `judgments.jsonl`
  - `judge_reasoning.md`
  - `judge_costs.json`
  - `semantic_business_summary.csv`

Required CLI flags:

```text
--use-judge
--judge-provider openai|local|mock
--judge-model <name>
--judge-sample-size N
--judge-failures-only
--judge-redact-results
```

## 4. Artifact Schema

Each row in `judgments.jsonl` should include:

```json
{
  "case_id": "VTD-001",
  "judge_provider": "openai",
  "judge_model": "configured-model-name",
  "judge_prompt_version": "semantic_business_v1",
  "question": "...",
  "generated_sql": "SELECT ...",
  "gold_sql": "SELECT ...",
  "execution_correct": true,
  "semantic_business_score": 4,
  "semantic_business_correct": true,
  "reasoning_summary": "...",
  "metric_correct": true,
  "filter_correct": true,
  "join_logic_correct": true,
  "aggregation_correct": true,
  "answer_explanation_consistent": true,
  "redaction_applied": true,
  "input_tokens": 0,
  "output_tokens": 0,
  "estimated_cost_usd": 0.0
}
```

## 5. Static vs Judge-Based Tests

Static tests still matter and must remain offline:

- generated SQL parses
- generated SQL is SELECT-only
- referenced tables/columns exist
- result hash matches gold SQL
- expected action matches behavioral label

LLM-as-a-Judge handles semantic/business questions that static checks cannot reliably decide:

- wrong metric with same result on a small dataset
- correct execution but wrong clinical/business interpretation
- answer text contradicts generated SQL
- ambiguity that should have caused clarification

## 6. Paper Claims

By using this phase, we can report:
- **Human-Judge Correlation**: How well the local agent's self-critic matches a SOTA judge.
- **Logic vs. Execution Gap**: Percentage of queries that pass EX but fail Semantic Correctness.
- **Analyst Utility**: Qualitative analysis of why certain SQL patterns are hard for local models.
- **Judge Cost and Coverage**: How many cases were judged, how much it cost, and which cases still need human review.

## 7. Security & Privacy

> [!CAUTION]
> **NEVER** send raw database rows containing PII (Personally Identifiable Information) to cloud judges.
> Only send de-identified sample results or aggregated statistics.

Required privacy controls:

1. Default cloud judge mode sends schema, question, SQL and aggregate/hash preview only.
2. Raw row previews require explicit `--judge-redact-results false` and must still be blocked if PII fields are detected.
3. Every judgment row stores `redaction_applied`.
4. If privacy checks fail, benchmark must skip judge for that case and record `judge_skipped_reason`.

## 8. Definition of Done

Phase 16 is done when:

- `run_benchmark.py --use-judge --judge-provider mock` works in tests without network.
- Online judge provider is config-driven and optional.
- `judgments.jsonl`, `judge_reasoning.md`, `judge_costs.json` and `semantic_business_summary.csv` are produced.
- Reports show execution correctness and semantic/business correctness separately.
- Cases where EX passes but business correctness fails are explicitly listed.
- Privacy redaction status is recorded for every judged case.
