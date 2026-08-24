# PARS-SQL — Paper Claim Governance Rules

Apply this rule when writing or editing:

- paper sections,
- abstract,
- results,
- discussion,
- limitations,
- README claims,
- dataset card,
- artifact summary,
- paper tables.

## Allowed careful wording

Use:

- Persian-aware,
- reliability-first,
- local/private,
- benchmark and framework,
- strict execution accuracy,
- valid SQL rate,
- semantic/business correctness under LLM judge,
- behavioral expected-action accuracy,
- abstention precision/recall,
- safety rejection,
- artifact-backed evaluation.
- Metric families must be reported separately because they use different
  denominators.

## Claim restrictions unless new artifacts prove them

Do not make:

- leaderboard superiority claims,
- broad accuracy claims,
- claims that Persian Text-to-SQL is solved,
- clinical decision-making claims,
- diagnosis-system claims,
- privacy guarantee,
- semantic judge proves correctness,
- claims that schema linking improves EX without verified ablation evidence,
- claims that value linking improves EX without verified ablation evidence,
- all modules improve accuracy.

## Numeric claim rules

1. Every number must come from an artifact.
2. Include numerator and denominator.
3. Include dataset/split.
4. Include model/config.
5. Include whether templates were enabled.
6. Keep strict EX separate from semantic/business judge.
7. Do not call LLM judge "human evaluation".
8. Mention human spot-check status if available.
9. Do not hide low EX.
10. Mention limitations clearly.
11. Paper tables must include `dataset_hash`, `selected_cases_hash`, and
artifact provenance such as config, predictions, summary, benchmark CSV,
manifest, or judge summary.

## Correct framing

Frame the paper as:

- benchmark,
- reliability-first system,
- local/private evaluation,
- safety/abstention protocol,
- failure analysis,
- artifact-backed reproducibility.

Do not frame as:

- leaderboard-style superiority,
- production-grade Text-to-SQL accuracy,
- clinical AI.

## Result interpretation rule

If ablation shows CAG is the largest driver, say so directly.

If schema/value linking do not independently improve EX, do not claim they do. Instead say they support control, traceability, grounding, and future reliability evaluation unless new evidence proves otherwise.
