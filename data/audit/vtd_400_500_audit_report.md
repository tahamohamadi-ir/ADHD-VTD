# VTD 400/500 Dataset Audit Report

Date: 2026-05-10

## Positive SQL Dataset

| Metric | Value |
|---|---:|
| Base positive examples | 260 |
| New colloquial additions | 140 |
| Final positive SQL examples | 400 |
| Easy | 100 |
| Medium | 100 |
| Hard | 100 |
| Complex | 100 |
| New SQL execution errors | 0 |
| New unsafe SQL | 0 |
| New empty result queries | 0 |
| Duplicate normalized questions in final 400 | 0 |
| Duplicate normalized SQL in final 400 | 0 |
| New max execution seconds | 0.1354 |

## Feature Coverage in Final 400
- JOIN: 51
- GROUP BY: 303
- ORDER BY: 332
- CASE: 98
- CTE/WITH: 146
- Window: 91
- Subquery: 157
- HAVING: 47
- LIMIT: 64
- Rate/Pct: 213
- Year/Time: 85

## Behavioral Evaluation Dataset

| Metric | Value |
|---|---:|
| Special evaluation examples | 100 |
| Easy | 25 |
| Medium | 25 |
| Hard | 25 |
| Complex | 25 |
| Expected to generate SQL | 17 |
| Expected not to generate SQL / clarification / refusal | 83 |
| Expected SQL execution errors | 0 |

## Evaluation Type Counts
- adversarial: 15
- ambiguous: 19
- chart_storytelling: 14
- multi_turn: 5
- no_sql: 9
- out_of_schema: 20
- typo_synonym: 3
- typo_synonym_or_multi_turn: 15
