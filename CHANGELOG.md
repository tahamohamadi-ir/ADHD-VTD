# Changelog

All notable changes to PARS-SQL are documented here.

## [0.2.0] - 2026-08-25

### Added (etude-mining quick wins; see docs/IMPROVEMENT_IDEAS_FROM_VTD_COLLECTION.md)

- Deterministic SQL surgeon (`src/sql_validation/surgeon.py`): parse-gated
  syntax-level strategies (code-fence strip, trailing-semicolon strip,
  balanced-quote fix) with confidence tracking and idempotency guarantees.
- Typed repair hints: `RepairHint` dataclass in `validation_result.py`; schema
  validator now suggests closest known table/column via difflib for unknown
  identifiers (qualified and unqualified paths, deduplicated per identifier).
- Multi-attempt repair memory: `repair_attempt_history()` exposes the last 3
  failed (sql, error) pairs through `reflexion_updates` state payloads.
- Prompt rules module (`src/generation/prompt_rules.py`) wired into
  `PromptBuilder` behind flags `SIMPLICITY_FIRST_PROMPT` and
  `REPAIR_CORRECTION_KB`: anti-overengineering generation rule plus curated
  broken-to-fixed SQL correction examples injected into the repair template.
- Feature presets `preset_minimal/default/full()` in `src/config/features.py`
  for named ablation configurations.
- Exact binomial McNemar test (`exact_mcnemar_test`) and partial-credit
  semantic score (`partial_credit_semantic_score`, 30/20/50 formula) in
  `src/evaluation`.
- Deterministic EGIR intent-vs-shape critic (`src/sql_validation/egir.py`):
  Persian intent detection (aggregate/split/trend/list) checked against SQL
  structure and result shape, emitting typed issues with Persian repair
  feedback; wired into the `check_consistency` graph node as advisory
  `egir_report` payloads (severity=warning until ablated).
- Partial-credit reporting: per-case `partial_credit_semantic` in agent-mode
  predictions and `partial_credit_semantic_mean/coverage` summary metrics as a
  separate metric family; paper-table and report renderers are now scalar-safe.
- Ground-truth recalibration CLI (`scripts/recalibrate_ground_truth.py`):
  re-executes gold SQL via the read-only executor, writes a NEW versioned
  dataset file plus a `.recalibration.json` audit report with SHA-256 trail;
  never mutates the input dataset.
- Negative-result ledger added to `docs/context-hub/FAILURE_PATTERNS.md`
  (section 0): components measured to hurt, with deltas, per the omni/VTD
  etude evidence.
- Viz-intent classifier `classify_viz_intent(sql)` with fallback-only
  integration into `recommend_chart(sql=...)`.
- Narrative number-grounding guard `find_ungrounded_numbers` with opt-in
  warning suffix via `generate_narrative(rows=...)`.
- Read-only executor now registers NULL-safe `MEDIAN/STDDEV/VARIANCE`
  SQLite aggregates on every connection.
- LLM-free CI tier: `tests/tier2_integration/test_gold_minibench_llm_free.py`
  runs loader + gold execution path without any model.
- New tests across evaluation, sql_validation, graph payloads, output and db
  modules (suite grew from 674 to 790 passing tests).

## [0.1.0] - 2026-08-22

### Added

- Phase 18.7 tooling: model-backed `CrossEncoderReranker` (bge-reranker-base/v2-m3) with
  identity fallback, agent-mode retrieval backend/reranker propagation, 18.7c0/c1/c2
  full400 + smoke configs.
- Phase 18.7d: `reliability_gate_routing` ablation flag with annotation-only vs routed
  gate configs (full400 + smoke).
- Anti-overfit holdout: rule-based Persian paraphrase generator
  (`scripts/generate_holdout_paraphrase.py`) and seeded difficulty-stratified
  `phase18_7_holdout_paraphrase48.json`.
- Latency budget guard (`scripts/check_latency_budget.py`) for the p95 <= 65.1s
  acceptance check.
- Judge adjudication import (human CSV or third-judge dir) and human spot-check
  package/import pipeline with Cohen's kappa.
- Central paper table pack builder (`scripts/build_paper_table_pack.py`,
  `src/evaluation/paper_pack.py`) regenerating `results/reports/paper_tables.md`
  and artifact manifests from the promotion registry.
- Phase 12 completion: Persian narrative generator wired into answer payloads;
  output unit tests (answer formatter, chart recommender, explanation builder,
  narrative generator).
- Phase 8 residue: SQLite graph checkpointing helper and Mermaid workflow diagram
  export (`scripts/export_graph_diagram.py`, `docs/graph_workflow.mmd`).
- Phase 14 prototype: node/component latency profiler (`scripts/profile_node_latency.py`),
  thread-safe question/SQL caches, deterministic `EdgePipeline` state machine.
- Phase 15 packaging: release bundle builder (`scripts/make_release_bundle.py`),
  VERSION/LICENSE/CHANGELOG files.
- Release engineering: CI workflow (`.github/workflows/ci.yml`), pre-commit config,
  Dockerfile and `requirements-ci.txt`.
- Graph output chain nodes (`recommend_chart` -> `log_benchmark_record` -> `END`) and
  `--checkpoint-db` SQLite graph checkpointing CLI wiring.

### Fixed

- `pyproject.toml` pytest key typo `3pythonpath` -> `pythonpath`.
