---
name: benchmark-evaluation
description: Use this skill when working on benchmark runner, metrics, ablation, semantic judge, behavioral evaluation, or paper tables.
---

# Skill: Benchmark and Evaluation

## Purpose

Use this skill when working on benchmark runner, metrics, ablation, semantic judge, behavioral evaluation, or paper tables.

## Required context

Read:

- `AGENTS.md`
- `docs/context-hub/ARTIFACT_RULES.md`
- `docs/BENCHMARK_AND_TEST_GUIDE.md` only when command-level detail is needed
- `src/evaluation/metrics.py`
- `src/evaluation/action_normalizer.py`
- `scripts/run_benchmark.py`
- `scripts/run_ablation.py`
- `scripts/judge_benchmark_artifact.py` when semantic judge evidence is in scope
- `scripts/plan_dual_policy_judge_ablation.py` when semantic judge ablation planning is in scope

## Rules

1. Keep SQL-positive and behavioral evaluation separate.
2. Always report numerator and denominator.
3. Never report smoke runs as final.
4. Never report config-only files as result.
5. Never mix strict EX and semantic/business judge.
6. Always save run config and manifest.
7. Always record model, prompt version, dataset hash, selected-case hash.
8. Report conservative denominator when generated SQL is missing.
9. Before paper-facing claims, validate the promotion registry with
   `scripts/check_release_readiness.py --promotion-doc`.

## Required metrics

SQL-positive:

- EX
- conservative EX
- valid SQL rate
- result mismatch count
- invalid SQL count
- missing SQL count
- unsafe SQL count
- latency mean/p95

Behavioral:

- expected-action accuracy
- safety rejection accuracy
- clarification accuracy
- abstention precision
- abstention recall
- unsafe SQL count

Semantic judge:

- semantic/business correctness
- judge provider
- judge model
- prompt version
- human spot-check status

## Tests required

- `tests/unit/test_metrics.py`
- `tests/unit/test_action_normalizer.py`
- `tests/unit/test_reliability_metrics.py`
- `tests/artifact/test_manifest_integrity.py`
- `tests/artifact/test_no_fake_results.py`

## Output format

Return:

1. Metric changed
2. Denominator definition
3. Artifact impact
4. Paper table impact
5. Tests
