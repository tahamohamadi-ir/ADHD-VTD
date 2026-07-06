# Project Rules

## Research identity

PARS-SQL is a research system for Persian local/private Text-to-SQL in sensitive mental-health and student-lifestyle analytics.

It is not a clinical system.

## Main research gap

Existing Text-to-SQL benchmarks and systems under-evaluate:

- Persian and mixed Persian-English questions,
- reliability and abstention,
- privacy-sensitive analytics,
- local/private model deployment,
- behavioral cases where SQL should not be generated.

## Core contribution

The contribution is:

1. Persian-aware benchmark design.
2. Reliability-first local Text-to-SQL framework.
3. Behavioral evaluation beyond strict execution.
4. Safety, privacy, and read-only execution.
5. Artifact-backed reproducibility and ablation.
6. Metric-family separation: SQL-positive, behavioral, and semantic/business
   evidence use different denominators and are reported separately.

## Current known weaknesses

The agent must not hide these weaknesses:

- strict EX is currently modest,
- semantic/business correctness is better than EX but still not high,
- behavioral SQL-positive execution is weak,
- CAG/examples are the strongest driver in ablation,
- schema/value linking need component-level evaluation,
- human validation is needed for stronger publication claims.
- These weakness categories use different denominators and are reported
  separately.

## Engineering priority

Do not add complexity randomly.

Highest-priority improvements:

1. Query-shape contracts.
2. Route-specific prompts.
3. Candidate generation + verifier.
4. Value grounding.
5. Human-audited holdout.
6. Artifact verification.
