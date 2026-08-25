# Improvement Ideas from VTD COLLECTION (Old Etudes Mining)

**Status:** Research input, not committed roadmap.
**Source:** `VTD COLLECTION/` (gitignored local archive), analyzed 2026-08-24 via four
parallel deep-reads: `VTD\` (148 py), `vtd-edge\` (142 py + Vue frontend),
`vtd_health_omni\` (180 py) + `VTD_V6\` (43 live py), `vtdm\` (planning docs) +
`vtd_mental_healthe\` (32 py).
**Rule:** every adopted idea must enter through the standard gates — feature flag,
ablation before default-on, artifact-backed measurement, read-only execution, and
no synthetic cross-domain joins (`AGENTS.md`).

---

## 1. Lineage lesson (why these etudes failed / survived)

| Etude | What died | What survived |
|---|---|---|
| `vtdm` | Pure-planning, zero code | Workstream decomposition W1–W6 (hardware/ETL/agentic/XAI/emergency) is a good checklist |
| `vtd_mental_healthe` | Monolith v30.x pipeline, cache-first design | Correction-KB pre-refiner, self-healing stage naming |
| `vtd_health_omni` | 25 empty placeholder files presented as features; FastAPI/Redis aspirational | Schema-RAG-v2 column chunks, hub-table JOIN hints (+5% EM measured), episodic memory, ablation mode matrix, documented NEGATIVE results (Planner −13.3%, CoT −6.7%) |
| `VTD` | Mock MCS shipped as real; retriever.py missing while imported; inflated README numbers | Surgeon strategies, EGIR, hybrid cache, PII abstraction, Streamlit+FastAPI patterns |
| `vtd-edge` | Advanced modules never wired into serving path; broken healthcheck/CORS | Trace-ID middleware, XAI response contract, feedback→gold harvesting, RTL/i18n shell, EmergencyHandler messages |
| `VTD_V6` (closest ancestor) | Regex parser beside sqlglot; voting disabled after 9x latency finding | Benchmark version-bump recalibration, strategy surgeon, GraphRouter, governance trio |

Meta-lesson encoded in this doc: **port components together with their kill-switch,
their ablation plan, and their honest measurement** — every failure above traces to
skipping one of those three.

---

## 2. Ranked adoption candidates

### Tier 1 — direct hits on known weaknesses (strict EX modest, behavioral weak)

| # | Idea | Evidence (collection path) | Target module | Effort |
|---|---|---|---|---|
| 1 | **Deterministic Surgeon pass before LLM reflexion**: strategy registry (add-GROUP-BY, quote-identifier, cast-timestamp, alias-rename, table-substitution) with confidence gates + validator-recheck-before-accept. Port only schema-grounded strategies; drop `ON 1=1` join guesser. | `VTD\src\core\surgeon.py`, `VTD_V6\src\core\surgeon.py` (9 strategies, stats) | `src/sql_validation/` + `src/graph/nodes/sql_repair_helpers.py` | M |
| 2 | **EGIR intent-vs-result-shape critic**: Persian keyword table (میانگین/تفکیک/روند/لیست) → expected construct (agg/GROUP BY/window/limit); typed issues (`MISSING_AGGREGATION`, …) with Persian feedback text fed to repair. Runs after successful execution, before judge. | `VTD\src\core\egir.py`, `VTD_V6\src\reflexion\semantic_feedback.py` | `src/sql_validation/semantic_validator.py`, `src/graph/nodes/reflexion_payloads.py` | L–M |
| 3 | **Typed validation errors + machine-readable RepairHint(action,target,suggestion,confidence)** consumed by both surgeon and repair-prompt builder. | `VTD_V6\src\validators\schema_validator.py` | `src/sql_validation/validation_result.py` | L |
| 4 | **Multi-attempt memory in repair prompt**: include accumulated (sql,error) pairs, not only last error. | `VTD\src\core\error_feedback.py:_build_correction_prompt` | `src/graph/nodes/reflexion_payloads.py` | L |
| 5 | **"SIMPLICITY FIRST" system-prompt block** (forbid unneeded CASE/subquery/CTE; Persian counter-examples; نسبیت→simple GROUP BY rules) + 5–10 pinned golden exemplars outside retrieval. Direct behavioral-case medicine. | `VTD\src\core\generator.py:134-197`, `VTD\src\config\golden_examples.py` | `src/generation/prompts/`, route-specific prompts | L |
| 6 | **Correction-KB few-shot block for the repair prompt**: curated broken→fixed pairs by error class (aggregate-in-WHERE→HAVING etc.). | `vtd_mental_healthe\src\validators\pre_refiner.py` | `src/generation/prompts/sql_repair.j2` context | L |
| 7 | **Result-based candidate voting**: fuzzy clustering of executed result sets (row-count ±10% AND value-Jaccard >0.7) instead of SQL-text equality; MD5-of-sorted-rows hash vote. Note V6 disabled voting on latency grounds — adopt behind flag with latency budget check first. | `VTD\src\core\mcs_generator.py`, `VTD_V6\src\generation\voting.py` | `src/evaluation/candidate_consistency.py`, `candidate_orchestrator.py` | M |

### Tier 2 — evaluation & dataset discipline

| # | Idea | Evidence | Target | Effort |
|---|---|---|---|---|
| 8 | **Ground-truth recalibration CLI**: re-execute gold SQL against current DB, write NEXT-version dataset + hashes + manifest entry automatically (`--bump-version`). Satisfies AGENTS rule 11 mechanically. | `VTD_V6\scripts\recalibrate_ground_truth.py`, omni `data\benchmark\generate_ground_truth.py` | new `scripts/recalibrate_ground_truth.py` + `src/evaluation/dataset_loader.py` | M |
| 9 | **Benchmark audit-report artifact**: duplicates, difficulty/category distribution, sampled execution test with per-query errors, written next to dataset version. | `VTD_V6\data\benchmark\validation_report.txt` producer | extend `scripts/check_duplicate_questions.py`, `validate_dataset.py` | L |
| 10 | **Paired significance testing**: McNemar between consecutive ablation arms + Cohen's d, rendered into ablation reports (bootstrap CI already exists). | `VTD\src\analysis\statistical_tests.py` | `src/evaluation/statistical_tests.py` (extend existing) | L |
| 11 | **Partial-credit semantic score** for near-miss result sets (row-ratio 30% / column-match 20% / value-overlap 50%) reported SEPARATELY from strict EX (rule 7 compliance). | `VTD\scripts\run_ablation_6mode.py::evaluate_result_semantic` | `src/evaluation/metrics.py` | L |
| 12 | **Negative-result ledger**: record removed/harmful components with measured deltas (omni's Planner −13.3% precedent). | omni `docs\8-Benchmark-System.md` | `docs/context-hub/FAILURE_PATTERNS.md` section | L |
| 13 | **LLM-free CI tier**: mini-benchmark validating via critic+executor without loading any model — fast PR gate. | `VTD_V6\tests\tier3_benchmark\run_mini_benchmark.py` | `tests/tier2_integration/` addition | S |
| 14 | **Named preset configs for ablations** (`default/minimal/full` PipelineConfig presets serialized into run manifest `to_dict()`). | `VTD_V6\src\config\features.py`, omni `ablation_config.py` | `src/config/features.py` | S |
| 15 | **External API baseline harness** (per-difficulty sampling, latency+cost columns) for paper comparison tables. | `VTD\scripts\model_comparison.py`, omni `openrouter_baseline.py` | `scripts/` | M |

### Tier 3 — serving, product surface, deployment

| # | Idea | Evidence | Target | Effort |
|---|---|---|---|---|
| 16 | **FastAPI service skeleton**: lifespan-managed engines, `TraceIDMiddleware` + `X-Trace-ID`, structlog JSON logs, `/health`; endpoints `/api/query`, `/api/schema`, `/api/models` wrapping the graph entry point. | `vtd-edge\backend\app\core\middleware.py`, `logger.py`; `VTD\api\main.py` | new `src/api/` | M |
| 17 | **XAI response contract** as Pydantic models: `{trace_id, sql, data≤100, narrative, viz_config, explanation{reasoning,data_source,limitations}, performance{per-stage ms}, error}`. | `vtd-edge\backend\app\api\routers\chat.py:38-67` | `src/api/schemas.py` + final-state mapping | S–M |
| 18 | **Human-feedback → gold-harvesting loop**: rating + corrected_sql persisted; rating≥4 ∧ correction ⇒ gold-candidate flag. Gives the pending human-review process a concrete artifact stream. | `vtd-edge\...\chat.py:212-234`, `VTD\src\core\unified_feedback.py` | `src/api/` + `data/feedback/` store (separate system DB) | M |
| 19 | **Persian web UI shell** (Streamlit fastest / Vue+Quasar richest): RTL, fa/en i18n, chat history, collapsible SQL, ChartSwitcher (recommended vs manual line/bar/table), KPI card for single-cell, CSV/JSON download, example-question chips. | `VTD\ui\app.py`, `vtd-edge\frontend\src\components\charts\*` | new top-level `ui/` | H |
| 20 | **Deterministic viz-intent classifier** (SQL shape → trend/comparison/distribution/kpi/ranking → x/y columns + Persian title) feeding existing `chart_recommender`. | `vtd-edge\backend\app\engine\intent.py`, `VTD\src\core\visualization.py:_detect_chart_type` | `src/output/chart_recommender.py` | S |
| 21 | **Narrative number-hallucination guard**: numerals >100 absent from result rows get flagged/logged. | `vtd-edge\backend\app\pipelines\narrative.py:_validate_numbers` | `src/output/narrative_generator.py` | S |
| 22 | **Deployment kit**: llama-server sidecar container + app image over HTTP (pattern: `VTD_V6` spawns bundled `bin\llama_cpp\llama-server.exe` on free port), bind-mounted models/data read-only, init→load→serve CMD chain, stdlib healthcheck (NOT curl-in-slim), nginx SPA proxy if UI adopted. | `VTD_V6\src\generation\llm_engine.py`, `vtd-edge\docker-compose.yml` | root compose + `deployment/` | M |
| 23 | **EmergencyHandler message catalog**: OOM→unload/downgrade, timeout>10s cancel, 2-consecutive-failure circuit-breaker, polite Persian retry/abstain texts wired to reliability-gate outputs. | `vtd-edge\backend\app\core\emergency.py`, `vtdm\W6-emergency.md` | `src/graph/` reliability node, `src/output/` templates | S–M |

### Tier 4 — runtime performance & capabilities

| # | Idea | Evidence | Target | Effort |
|---|---|---|---|---|
| 24 | **Hybrid exact+semantic answer cache** (hash + embedding-sim ≥0.85, TTL/LRU, hit-rate stats); invalidate on dataset/schema version bump. | `VTD\src\utils\cache.py` | new `src/runtime/caches.py` extension | M |
| 25 | **Episodic memory of verified successes**: ChromaDB store of Q→SQL gated by judge/reliability pass + result_hash; recall as extra candidate source. Privacy: aggregate-safe pairs only. | omni `src\core\critic_memory.py` | `src/retrieval/` | M |
| 26 | **Complexity router**: FAST(zero-shot)/ROBUST(RAG+CoT)/REPAIR/REFLECT paths with escalation-on-failure and per-path budgets; adaptive-k few-shot by classified difficulty. Measure with existing `profile_node_latency.py` before enabling. | `VTD_V6\src\choreography\router.py`, `core\query_classifier.py` | `src/graph/routes.py` conditional edges | M |
| 27 | **SQLite statistical aggregates**: register `MEDIAN/STDDEV/VARIANCE` so Persian median/stddev questions need no window gymnastics; add matching prompt note listing available functions. | `VTD_V6\src\utils\sqlite_stats.py` | `src/db/read_only_executor.py` registration + prompt note | S |
| 28 | **Hardware-profile loader** (psutil/NVML scan → High/Balanced/Edge ctx/threads/gpu-layers preset; warm-up prompt at boot). | `VTD_V6\src\utils\model_manager.py`, `system_scan.py`; `vtdm\W1-hardware.md` | `src/runtime/`, `src/config/settings.py` | S–M |
| 29 | **Skeleton-based example selection** (DAIL-SQL style structural skeletons) as an additional retrieval scorer beside BM25/vector/reranker. | `VTD\src\core\skeleton_extractor.py` | `src/retrieval/retrieval_scorer.py` | M |
| 30 | **Schema-linker hint header**: prepend deterministic `Tables/Columns` hint lines from alias index above schema context (measured +5% in omni when forced-JOIN variant used). | omni `schema_rag_v2.py:get_join_hints`, `VTD\run_ablation_6mode.py:373-385` | `src/schema/schema_linker.py` context builder | S |

### Tier 5 — privacy

| # | Idea | Evidence | Target | Effort |
|---|---|---|---|---|
| 31 | **Reversible PII abstraction pre-LLM**: Persian names, کد ملی (incl. Persian digits), Shamsi dates, 09xx phones → `PERSON_1`-style tokens with restore map; complements (not replaces) aggregate-only disclosure policy. Needs its own safety review before enabling. | `VTD\src\core\abstraction.py`, `VTD_V6\src\utils\pii_layer.py` | new `src/nlu/pii_abstractor.py` + graph normalize node hook | M |

---

## 3. Explicitly rejected (with reason)

| Rejected | Why |
|---|---|
| Omni's FastAPI/Redis/JWT/Prometheus stack | 0-byte stubs everywhere; aspirational only |
| Regex SQL parser alongside sqlglot | two parsers = drift; keep sqlglot single-source |
| `FixJoinSyntax ON 1=1` / blanket quote-identifier repairs | corruption risk (cartesian products) |
| Aggressive auto-correction defaults | measured degradation in `smart_verifier.py` v2.2 comments; corrections must be conservative + individually ablated |
| Keyword-blocklist gatekeeper as safety boundary | scope rejection stays in `safety_intent_detector`; blocklists are UX hint only |
| Hardcoded table/column maps inside code (`TableCorrectionStrategy.common_fixes`) | violates frozen-schema-as-data; any substitution maps must live in `data/schema/` |
| Excel-first logging/versioning rituals | superseded by git + hashed artifacts |
| Mock/simulated components presented as features | AGENTS rule 9 already forbids; historical caution only |
| Cloud-API baselines beyond comparison harness | local/private mission; harness (#15) is the only sanctioned cloud touchpoint |
| Session-context illusions (sessionId never sent) | either implement real sessions or none |

---

## 4. Suggested sequencing (post-paper-1 workstream sketch)

1. Quick wins (all low effort, high signal): #3 typed RepairHints → #4 multi-attempt memory → #10 McNemar → #11 partial credit → #13 LLM-free CI tier → #14 config presets → #20 viz-intent → #21 narrative guard.
2. EX-quality push: #1 Surgeon → #2 EGIR → #5/#6 prompt blocks → #7 voting (flagged) → measure each via existing ablation runner; expect behavioral-case gains from #5/#2.
3. Data discipline: #8 recalibration CLI → #9 audit report → #12 negative-result ledger.
4. Product track (after paper freeze): #16 API → #17 contract → #18 feedback loop → #19 UI → #22 deployment kit → #23 emergency messages.
5. Perf/privacy spikes behind flags: #24–#31, each with latency-budget + ablation gate.

Adoption of ANY item requires: feature-flag default-off, unit tests, one smoke
ablation run, and a Risks.md/task.md entry before default-on promotion.

---

## 5. Implementation status (2026-08-25)

Landed in v0.2.0 (all with unit tests; full suite 790 passing):

| Idea | Status | Where |
|---|---|---|
| #1 Deterministic surgeon | PARTIAL — syntax-level strategies landed (`strip_code_fence`, `trailing_semicolon`, `balanced_quote_fix`); schema-grounded GROUP-BY/table strategies still open | `src/sql_validation/surgeon.py` |
| #3 Typed RepairHint | DONE | `src/sql_validation/validation_result.py`, `schema_validator.py` (difflib suggestions, both qualified/unqualified paths) |
| #4 Multi-attempt repair memory | DONE | `src/graph/nodes/reflexion_payloads.py::repair_attempt_history` via `reflexion_updates` |
| #5 SIMPLICITY FIRST block | DONE, flag `SIMPLICITY_FIRST_PROMPT` | `src/generation/prompt_rules.py` + `prompt_builder.py` |
| #6 Correction KB for repair prompt | DONE, flag `REPAIR_CORRECTION_KB` | same module + `prompts/sql_repair.j2` |
| #2 EGIR intent-vs-result critic | DONE — wired into `check_consistency` graph node (advisory `egir_report`, severity=warning; gate behavior unchanged pending ablation) | `src/sql_validation/egir.py`, `src/graph/nodes/check_consistency_node.py` |
| #7 Result-hash voting | DONE, flag `ENABLE_RESULT_HASH_FUZZY_VOTING` (default off; V6's 9× latency warning respected) — fuzzy clustering fallback when exact-hash majority absent | `src/evaluation/result_voting.py`, `candidate_consistency.py::_select_candidate` |
| #8 Recalibration CLI | DONE | `scripts/recalibrate_ground_truth.py` (+ `.recalibration.json` report sidecar) |
| #10 Exact McNemar test | DONE | `src/evaluation/statistical_tests.py::exact_mcnemar_test` |
| #11 Partial-credit semantic score | DONE — per-case `partial_credit_semantic` in agent predictions + `partial_credit_semantic_mean/coverage` in summary metrics (separate family, excluded from EX/reliability); scalar-safe metric renderers | `src/evaluation/metrics.py`, `scripts/run_benchmark.py`, `export_utils.py`, `report_generator.py` |
| #12 Negative-result ledger | DONE | `docs/context-hub/FAILURE_PATTERNS.md` section 0 |
| #13 LLM-free CI tier | DONE | `tests/tier2_integration/test_gold_minibench_llm_free.py` |
| #14 Named config presets | DONE | `src/config/features.py::preset_minimal/default/full` |
| #20 Viz-intent classifier | DONE, fallback-only | `src/output/chart_recommender.py::classify_viz_intent` |
| #21 Narrative number guard | DONE, opt-in `rows=` param | `src/output/narrative_generator.py::find_ungrounded_numbers` |
| #27 SQLite stats aggregates | DONE | `src/db/read_only_executor.py::_register_stats_functions` |

Still open, in recommended order: promote EGIR warnings to gate-relevant
severity after one ablation → Tier 3 product track (#15–#23) → Tier 4/5
spikes.

Note on flags: `SIMPLICITY_FIRST_PROMPT` and `REPAIR_CORRECTION_KB` ship ON;
both are plain prompt-text additions with zero deterministic-behavior impact.
Run the existing ablation runner once before the next paper-facing benchmark
to confirm no EX shift, and flip them off via config if any regression shows.
