# Recommended PARS-SQL Phase Order

## Phase 0 - Confirm Rules And Context

Use prompt: `.codex/prompts/00_task_planning.md`

Exit gate: Codex summarizes non-negotiable constraints correctly.

## Phase 1 - Query Shape Contract

Use prompt: `.codex/prompts/19_phase1_query_shape_core.md`

Exit gate: scalar-intent tests never accept grouped SQL.

## Phase 2 - Scalar Prompt

Use prompt: `.codex/prompts/20_scalar_prompt_refactor.md`

Exit gate: scalar prompt forbids hidden `GROUP BY` and hidden `WHERE`.

## Phase 3 - Safety Tests

Use prompt: `.codex/prompts/04_safety_privacy.md`

Exit gate: destructive SQL, `SELECT *`, comments, multiple statements, and
illegal joins are rejected.

## Phase 4 - Artifact Verifier

Use prompt: `.codex/prompts/07_artifact_verifier.md`

Exit gate: invalid artifacts fail verification.

## Phase 5 - Benchmark Metrics Audit

Use prompt: `.codex/prompts/06_benchmark_metrics_audit.md`

Exit gate: strict EX, conservative EX, valid SQL, and behavioral metrics remain
separate.

## Phase 6 - Route Prompts

Use prompt: `.codex/prompts/08_route_specific_prompts.md`

Exit gate: scalar and grouped prompts are separate and parser-compatible.

## Phase 7 - Candidate Verifier

Use prompt: `.codex/prompts/09_candidate_generation_verifier.md`

Exit gate: candidates are scored only with runtime signals and no gold leakage.

## Phase 8 - Human Audit

Use prompt 12 in `CODEX_PROMPTS.md`.

Exit gate: annotation schema and agreement pipeline are ready.
