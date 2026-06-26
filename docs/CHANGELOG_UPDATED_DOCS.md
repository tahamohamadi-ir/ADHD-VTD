# VTD Docs v2.3 Execution-Ready - Change Log

This package contains corrected and completed documentation files aligned with the final v2.3 proposal.

## Updated Files

| File | Change |
|---|---|
| `00_INDEX.md` | Rewritten as the execution-ready documentation index with immediate Phase 0 actions |
| `01_RESEARCH_GRADE_ARCHITECTURE.md` | Added research/edge runtime split, value retrieval, reliability gate, abstention, decision rule |
| `02_LANGGRAPH_WORKFLOW_SPEC.md` | Added reliability state fields, candidate SQL model, consistency/abstention routes |
| `03_PERSIAN_NLU_AND_SCHEMA_LINKING.md` | Added Finglish/typo handling, value linking, Milestone 1.5, Persian-specific errors |
| `04_RAG_CAG_AND_RETRIEVAL_DESIGN.md` | Added value retrieval channel, adaptive context compression, retrieval calibration |
| `05_SQL_GENERATION_VALIDATION_REFLEXION.md` | Added multi-candidate generation, consistency-based abstention, error disclosure |
| `06_EVALUATION_ABLATION_AND_PAPER_PLAN.md` | Rewritten with Reliability Score, abstention metrics, robustness, Paper1/Paper2 ablation split, human agreement |
| `07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md` | Rewritten as implementation-first guide with Phase 0, Milestone 1/1.5, commands |
| `08_PROJECT_STRUCTURE_AND_FILE_MAP.md` | Added repository gates, required artifacts, suggested new source files |
| `09_DATASET_AND_EVALUATION_FILES_GUIDE.md` | Added dataset maturity, audit rules, human agreement, dataset card, reliability labels |
| `10_FULL_DEVELOPMENT_ROADMAP_ZERO_TO_SOTA.md` | Added v2.3 execution addendum, first-paper scope, supervisor/GitHub gate |
| `11_SEMANTIC_BUSINESS_LOGIC_EVALUATION.md` | Updated to reflect Phase 16 successful semantic judgement using DeepSeek V4-Flash |
| `phases/PHASE_18_7_ZERO_SHOT_MASTERY.md` | Added canonical Phase 18.7 anti-overfit plan for the final >65% zero/few-shot push |
| `task.md` | Added Phase 18.7 canonical task list, acceptance criteria, anti-overfit rules and benchmark commands |
| `DEVELOPMENT_ROADMAP.md` | Updated Phase 18 status and roadmap with the 61.25% baseline and stepwise 18.7 ablation plan |

## New Helper Files

| File | Purpose |
|---|---|
| `README_PHASE0_SNIPPET.md` | Copy into root README.md |
| `DATASET_CARD_DRAFT.md` | Starting point for root DATASET_CARD.md |
| `PHASE0_50Q_AUDIT_TEMPLATE.md` | CSV/report template for data audit |

## Data Files

The JSON/JSONL dataset files were not modified. They should be validated by Phase 0 audit before being treated as paper-ready.
