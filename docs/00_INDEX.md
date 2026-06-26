# VTD-Edge Research-Grade Documentation Suite

**Status:** Paper 1 execution documentation suite, updated with artifact-backed B0/B1 status  
**Last Updated:** 2026-06-26 (gold closeout, behavioral100, full bounded no-template run, retrieval, full positive400 ablation, full 400-case authoritative semantic judge)
**Project:** VTD-Edge / ADHD-VTD Persian Text-to-SQL System  
**Target:** Research-grade and edge-deployable, offline, privacy-preserving, Persian-first Text-to-SQL pipeline  
**Primary Goal:** Build a measurable, reliable, and publishable local/edge NL2SQL system for mental-health and student-lifestyle analytics while keeping data private.  
**Recommended Research Orchestrator:** LangGraph for benchmark and research runtime.  
**Recommended Edge Runtime:** a lightweight custom Python/mobile state machine after the research pipeline stabilizes.

---

## 1. How to Use This Documentation

This documentation is both **human-readable** and **LLM-friendly**. You can give any file to an LLM coding assistant as implementation context, but the implementation order must follow the roadmap and governance rules.

The current source-of-truth principle is:

```text
Architecture docs explain the target system.
Execution governance decides what to build first.
The Phase 0 audit decides whether the schema and benchmark are actually usable.
```

Non-negotiable documentation principles:

1. Every component has a clear responsibility.
2. Every node has explicit inputs and outputs.
3. Every LLM call is surrounded by deterministic guards.
4. The database schema is treated as a first-class object.
5. Persian language processing is a research contribution, not a UI detail.
6. Evaluation includes reliability, abstention, safety, and robustness, not only EX.
7. Every claim must be measurable through benchmark artifacts.
8. Research features and edge features must not be mixed without a milestone decision.

---

## 2. Documentation Map

| File | Purpose |
|---|---|
| `01_RESEARCH_GRADE_ARCHITECTURE.md` | Full target architecture, research contribution, system layers, value retrieval, reliability gate, edge/research split |
| `02_LANGGRAPH_WORKFLOW_SPEC.md` | LangGraph state, nodes, routing, multi-candidate generation, abstention, retry policy, research runtime contracts |
| `03_PERSIAN_NLU_AND_SCHEMA_LINKING.md` | Persian normalization, Finglish/typo handling, Jalali date handling, value linking, ambiguity/safety routing |
| `04_RAG_CAG_AND_RETRIEVAL_DESIGN.md` | CAG/RAG retrieval, schema context, value retrieval, adaptive context compression, retrieval metrics |
| `05_SQL_GENERATION_VALIDATION_REFLEXION.md` | SQL generation, validation, consistency-based abstention, SQL Surgeon, semantic critic, error disclosure |
| `06_EVALUATION_ABLATION_AND_PAPER_PLAN.md` | Reliability Score, EX/EM, abstention metrics, modular evaluation, robustness tests, ablation scope, paper plan |
| `07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md` | Implementation-first roadmap, Phase 0 gate, 50-question audit, Milestone 1/1.5, requirements, commands |
| `08_PROJECT_STRUCTURE_AND_FILE_MAP.md` | Canonical current folder structure, module responsibilities, data contracts, path conventions, repo gates |
| `09_DATASET_AND_EVALUATION_FILES_GUIDE.md` | Dataset files, golden examples, few-shot bank, behavioral evaluation, human agreement, dataset card |
| `10_FULL_DEVELOPMENT_ROADMAP_ZERO_TO_SOTA.md` | Full phased roadmap from current state to research-grade and SOTA-style local/edge Text-to-SQL |
| `11_SEMANTIC_BUSINESS_LOGIC_EVALUATION.md` | Specification and current artifact-backed status for Phase 16: Semantic/business correctness evaluation using LLM-as-a-Judge, OpenRouter live pilots and judge agreement, separate from SQL execution correctness |
| `PARS_SQL_PAPER1_IMPLEMENTATION_PLAN.md` | Current source of truth for Paper 1 execution status, completed artifacts, remaining work, and commands |
| `PARS_SQL_PAPER1_RESULTS_SUMMARY.md` | Artifact-backed status summary for current Paper 1 evidence; not final until B1.3/B1.5 closeout |
| `PARS_SQL_PAPER1_REPRODUCIBILITY.md` | Commands and artifact paths needed to reproduce current Paper 1 runs |
| `DATASET_CARD.md` | Current dataset card for positive400 + behavioral100, including limitations and safety scope |
| `paper/limitations.md` | Paper 1 limitations draft covering clinical scope, dataset limits, overfit risk, and reranker caveats |
| `phases/PHASE_13_RELIABILITY_GATE.md` | Current Phase 13 reliability-gate contract, annotation-only benchmark wiring, anti-overfit policy, and verification commands |
| `phases/PHASE_18_7_ZERO_SHOT_MASTERY.md` | Phase 18.7 plan for the final anti-overfit zero/few-shot push beyond 65%: template safety, schema gating, one-shot surgeon, validator fixes, vector/reranker ablations and reliability-gate verification |
| `BENCHMARK_AND_TEST_GUIDE.md` | Practical guide for running tests, retrieval/gold/agent benchmarks, balanced sampling, reading artifacts, and debugging failures |
| `VTD_Edge_PARS_SQL_Proposal_FINAL_v2_3_Execution_Ready_FA.docx` | Final implementation-first mini proposal / execution guide |
| `requirements-vtd-edge-research.txt` | Suggested additional/updated Python dependencies for the research-grade version |

---

## 3. Core Design Summary

The system is not a simple RAG chatbot. It is a **compiler-like, reliability-first, graph-orchestrated Text-to-SQL system**:

```text
Persian user question
  -> Persian normalization and number/date normalization
  -> intent, ambiguity, and safety routing
  -> QIR / query plan
  -> schema linking and value retrieval
  -> compact CAG context packing
  -> local small LLM candidate generation
  -> multi-candidate consistency check when enabled
  -> SQL validation and deterministic repair
  -> read-only execution
  -> semantic result checking
  -> answer formatting, chart recommendation, or explicit abstention/warning
  -> benchmark trace and error analysis
```

The recommended architecture is called:

> **PARS-SQL: Persian-Aware Reflexive Schema-grounded Text-to-SQL**

The project is intentionally designed for small local models and future edge deployment. Cloud/frontier models are used only as comparison baselines or synthetic-data upper bounds.

---

## 4. Execution Governance Rule

Every feature must be classified before implementation:

| Feature | Milestone decision |
|---|---|
| Persian normalization, number normalization, basic date normalization | MVP / Phase 1 |
| Schema freeze and schema registry | Phase 0 gate |
| 50-question manual audit | Phase 0 gate |
| Value retrieval | MVP / Phase 3, before heavy RAG |
| Basic safety/ambiguity routing | MVP / Phase 1.5 |
| LangGraph full pipeline | Research benchmark runtime, not edge runtime |
| CAG / RAG retrieval | Paper 1 after schema/value linking is stable |
| Consistency-based abstention | Paper 1 after multi-candidate generation exists |
| SQL Surgeon and Reflexion | Paper 1/2 depending on Phase 9 capacity |
| Custom edge state machine | Later edge-runtime phase, not before research pipeline is validated |

This rule prevents the project from drifting between product engineering and research exploration.

---

## 5. Non-Negotiable Rules

1. The LLM must never execute SQL directly.
2. The LLM must never decide whether SQL is safe.
3. Generated SQL is always treated as untrusted input.
4. Only validated `SELECT` queries may reach the executor.
5. The system must abstain or ask clarification when confidence/reliability is low.
6. If execution succeeds but semantic critic fails, show an explicit warning; do not silently present the result as reliable.
7. Every benchmark run must store full traces.
8. Every failed query must be categorized.
9. Every architecture improvement must be tested through ablation.
10. Data used with cloud/API baselines must be synthetic or de-identified.
11. Every benchmark artifact must record model name/path, config id, ablation id, enabled modules and disabled modules.
12. SQL execution correctness and semantic/business correctness must be reported as separate metrics.
13. Prompt and raw model response must be stored for every agent attempt used in research claims.

---

## 6. Immediate Next Action

Phase 0 and the initial Paper 1 blocker fixes are no longer the next step. The current source of truth is:

```text
docs/PARS_SQL_PAPER1_IMPLEMENTATION_PLAN.md
```

Current next actions for Paper 1:

```text
1. Decide whether to build a clean paraphrase holdout for anti-overfit claims.
2. Optionally human spot-check a sample of the 400 OpenRouter semantic/business judgments before final paper submission.
3. Refresh `paper1_review_package_20260622` after any new holdout or judge-review artifacts.
```
