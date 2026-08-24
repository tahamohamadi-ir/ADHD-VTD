# Changelog

All notable changes to PARS-SQL are documented here.

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
