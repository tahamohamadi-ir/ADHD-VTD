# Phase 0 Evaluation Summary

## Dataset

| Metric | Value |
|---|---:|
| Total cases | 50 |
| SQL-positive | 50 |
| Behavioral / non-SQL | 0 |

## Gold SQL Execution

| Metric | Value |
|---|---:|
| Execution result rows | 50 |
| Successful | 50 |
| Failed | 0 |

## Metrics

| Metric | Value | Numerator | Denominator | Description |
|---|---:|---:|---:|---|
| `execution_accuracy` | 1.0000 | 50 | 50 | Correct execution result / total cases |
| `valid_sql_rate` | 1.0000 | 50 | 50 | Valid SQL / total generated SQL cases |
| `schema_linking_accuracy` | 0.0000 | 0 | 50 | Correct table/column linking / reviewed cases |
| `value_linking_accuracy` | 0.0000 | 0 | 50 | Correct value resolution / reviewed value cases |
| `clarification_accuracy` | 0.0000 | 0 | 0 | Correct clarification decisions |
| `safety_rejection_accuracy` | 0.0000 | 0 | 0 | Correct unsafe/adversarial refusals |
| `sql2nl_paraphrase_robustness` | 1.0000 | 50 | 50 | Paraphrase groups where all variants pass |
| `abstention_precision` | 0.0000 | 0 | 0 | Correct abstentions / predicted abstentions |
| `abstention_recall` | 0.0000 | 0 | 0 | Correct abstentions / required abstentions |

## Reliability Score

| Field | Value |
|---|---:|
| `score` | 50.0 |
| `normalized_score` | 1.0 |
| `total_cases` | 50 |
| `correct_sql` | 50 |
| `correct_abstention` | 0 |
| `wrong_sql` | 0 |
| `wrong_abstention` | 0 |
| `unsafe_sql` | 0 |

## Interpretation

This report is Phase-0/Phase-1 oriented. It validates dataset executability and evaluation infrastructure before full LLM benchmarking, CAG, LangGraph, or reflexion.
