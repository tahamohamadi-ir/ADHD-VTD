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

## Graph node architecture rules

- `src/graph/nodes/base_nodes.py` may keep the operational LangGraph node
  functions while the cleanup is incremental, but deterministic helper logic
  should move into small modules with focused tests.
- `src/graph/workflow.py` should import operational graph nodes from the
  dedicated `*_node.py` modules. Those modules may remain compatibility
  wrappers around `base_nodes.py` while extraction is incremental.
- SQL repair helpers must still call the normal validation pipeline and shape
  validation before a patched SQL string can be accepted.
- Current graph-local deterministic repair helpers live in
  `src/graph/nodes/sql_repair_helpers.py` and cover unknown-column alias repair
  plus narrow analytical-shape repair.
- Current graph-local candidate helper logic lives in
  `src/graph/nodes/candidate_helpers.py`; candidate inspection lives in
  `src/graph/nodes/candidate_inspector.py`; candidate orchestration lives in
  `src/graph/nodes/candidate_orchestrator.py`; execution attempt helpers live
  in `src/graph/nodes/execution_attempts.py`; SQL generation routing lives in
  `src/graph/nodes/generation_router.py`; output payload helpers live in
  `src/graph/nodes/output_payloads.py`; reflexion payload helpers live in
  `src/graph/nodes/reflexion_payloads.py`; validation attempt/retry helpers
  live in `src/graph/nodes/validation_attempts.py`. Candidate metadata must
  stay runtime-only and must not copy gold SQL, reference answers, strict
  labels, or semantic/business labels.
- Generation routing may select no-prompt, deterministic-template, single-LLM,
  or multi-candidate generation through injected dependencies, but it must not
  build prompts, validate SQL, execute SQL, score candidates, or promote
  artifacts/metrics.
- Candidate orchestration may coordinate generation, inspection, consistency,
  verifier scoring, latency budgets, and adoption gates, but must not promote
  diagnostic candidate evidence into paper metrics.
- `generate_candidates_node.py` is a deterministic policy-materialization
  compatibility node. It must not call an LLM, parse SQL candidates, validate
  candidates, or bypass the guarded `generate_sql` multi-candidate
  orchestrator.
- Candidate inspection must use injected validators and the read-only executor
  path; it must never add direct SQLite access or execute SQL before validation
  and shape validation pass.
- Validation attempt/retry helpers may build `SQLAttempt` records and classify
  retry decisions, but must not instantiate validators, rewrite SQL, execute
  SQL, or change safety/privacy semantics.
- Execution attempt helpers may attach read-only execution results to the
  latest attempt and build state update payloads, but must not instantiate
  executors, open SQLite connections, retry independently, or bypass
  `src/db/read_only_executor.py`.
- Output payload helpers may coordinate formatter/chart/explanation calls and
  graceful-failure payloads, but must not execute SQL, mutate attempts, compute
  benchmark metrics, or promote artifacts.
- Reflexion payload helpers may extract error context, seed transition memory,
  format repair error text, and attach critic feedback/repair plans to the
  latest attempt, but must not alter retry routing, instantiate
  validators/executors, or change repair prompt semantics.
- Refactors must preserve existing graph-node wrapper names when tests,
  monkeypatches, or external scripts rely on those symbols.
- Do not move execution into repair helpers. SQL execution remains the
  responsibility of `src/db/read_only_executor.py` through graph execution
  nodes only.

## Value-linking implementation rules

- A single Persian surface form can map to different target semantics depending
  on the candidate column. Example: depression can mean a binary
  `depression_flag`/`depression_diagnosis` value or the disorder value
  `depression`.
- Do not encode duplicate dictionary keys for those aliases. Keep the primary
  alias map unique and put column-specific duplicate surface forms in an
  explicit extra-alias list so both meanings remain testable.
- Dataset/table mentions such as `student_depression` or "depression dataset"
  must not become row filters unless the user explicitly asks for depressed
  individuals.
