---
name: artifact-reproducibility
description: Use this skill for manifests, artifact verification, paper table generation, reproducibility scripts, dataset hashes, and release packaging.
---

# Skill: Artifact Reproducibility

## Purpose

Use this skill for manifests, artifact verification, paper table generation, reproducibility scripts, dataset hashes, and release packaging.

## Required context

Read:

- `AGENTS.md`
- `docs/context-hub/ARTIFACT_RULES.md`
- latest artifact manifest
- `scripts/run_benchmark.py`
- `scripts/check_release_readiness.py` if present
- `scripts/verify_artifact.py` if present
- `scripts/package_dual_policy_evidence.py` when semantic/business evidence is in scope
- `scripts/judge_benchmark_artifact.py` when judge artifact evidence is in scope
- `scripts/plan_dual_policy_judge_ablation.py` when judge ablation planning is in scope
- promotion registry in `docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md` when paper
  claims or final-result eligibility are in scope

## Artifact validity

A final artifact must include:

- config
- predictions
- benchmark results
- summary json
- summary md
- failures if any
- manifest
- dataset hash
- selected cases hash
- model identity
- prompt version
- git commit

## Verifier must check

1. total predictions match summary
2. failure count matches summary
3. EX numerator/denominator consistent
4. valid SQL rate consistent
5. unsafe SQL count consistent
6. deterministic_templates flag explicit
7. run is not smoke unless labeled smoke
8. judge outputs match judge summary
9. no mock judge cited as authoritative
10. no placeholder reranker cited as real reranker
11. paper promotion registry does not mark diagnostic, smoke, mock, pending,
    shadow, SPL, failed, or dry-run artifacts as final

## Required scripts

- `scripts/verify_artifact.py`
- `scripts/check_release_readiness.py`
- `scripts/run_benchmark.py`
- `scripts/package_dual_policy_evidence.py` when semantic/business evidence is in scope
- `scripts/judge_benchmark_artifact.py` when judge artifact evidence is in scope
- `scripts/plan_dual_policy_judge_ablation.py` when judge ablation planning is in scope
- dataset hash verification script if present
- paper table generation script if present
- `scripts/check_release_readiness.py --promotion-doc <doc>` before final
  paper-facing claims

## Output format

Return:

- artifact rule implemented
- verifier checks added
- tests added
- reproduction command
