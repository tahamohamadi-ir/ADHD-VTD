# 11 - Semantic Business Logic Evaluation (LLM-as-a-Judge)

## 1. Rationale

Execution Accuracy (EX) measures if the SQL returns the same result set as the gold query. However, in complex clinical and mental health domains:
1. Different SQL queries can return the same results on a specific dataset but have different business logic.
2. A query might be "technically correct" (executes) but "conceptually wrong" (e.g., uses the wrong metric for anxiety).
3. The generated explanation might contradict the SQL logic.

To achieve **State-of-the-Art (SOTA)** research quality, we introduce an LLM-as-a-Judge layer.

## 2. Methodology

The judge is a high-reasoning model (e.g., GPT-4o, o1-mini, or Claude 3.5 Sonnet) that acts as a "Senior Clinical Data Analyst".

### Input to the Judge
- **Original Persian Question**: Raw user intent.
- **Normalized Context**: The system's understanding of the question.
- **Linked Schema**: Tables and columns used.
- **Generated SQL**: The candidate produced by the local agent.
- **Gold SQL**: The ground-truth reference.
- **Execution Sample**: Top 5 rows of the result set.

### Judging Rubric (0-5 Scale)
| Score | Label | Description |
|---|---|---|
| 5 | Perfect | Logic is correct, efficient, and perfectly maps to the question. |
| 4 | Correct | Minor stylistic differences or slightly inefficient, but logic is sound. |
| 3 | Minor Logic Error | Result might be correct for this dataset, but the logic has a flaw (e.g., wrong join type). |
| 2 | Major Logic Error | The query uses the wrong columns or metrics but happens to execute. |
| 1 | Execution Failure / Hallucination | The query executes but is completely unrelated to the intent. |
| 0 | Catastrophic | Unsafe, toxic, or total gibberish. |

## 3. Technical Implementation

### Module: `src/evaluation/llm_judge.py`
- Uses `src.config.settings` for API keys.
- Implements async batching to reduce judge latency.
- Supports "Reasoning Traces": the judge must explain *why* a score was given.

### Integration: `run_benchmark.py --use-judge`
- When enabled, the runner sends failures and a sample of successes to the judge.
- Generates `judgments.jsonl` and `judge_reasoning.md`.

## 4. Paper Claims

By using this phase, we can report:
- **Human-Judge Correlation**: How well the local agent's self-critic matches a SOTA judge.
- **Logic vs. Execution Gap**: Percentage of queries that pass EX but fail Semantic Correctness.
- **Analyst Utility**: Qualitative analysis of why certain SQL patterns are hard for local models.

## 5. Security & Privacy

> [!CAUTION]
> **NEVER** send raw database rows containing PII (Personally Identifiable Information) to cloud judges.
> Only send de-identified sample results or aggregated statistics.
