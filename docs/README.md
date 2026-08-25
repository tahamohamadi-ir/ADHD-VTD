# PARS-SQL Docs

This directory contains project architecture, benchmark, dataset, paper, and
release-governance documentation.

## Canonical Starting Points

- `context-hub/INDEX.md`: tells agents which context file to load for each task.
- `context-hub/ARTIFACT_RULES.md`: canonical short protocol for benchmark,
  artifact, reproducibility, and paper-facing evidence.
- `context-hub/SAFETY_PRIVACY_RULES.md`: canonical short protocol for SQL
  safety, privacy, and read-only execution.
- `Risks.md`: open risk register. Keep only unresolved risks here.
- `BENCHMARK_AND_TEST_GUIDE.md`: operational test and benchmark commands.
- `DATASET_CARD.md`: dataset scope, intended use, audit posture, and limitations.
- `PARS_SQL_PAPER1_REPRODUCIBILITY.md`: current paper reproduction notes and
  artifact paths.
- `scripts/check_release_readiness.py`: centralized release gate for verified
  artifacts, dual-policy evidence, stale references, and explicit paper-claim docs.

## Architecture And Design Docs

- `00_INDEX.md`: broad documentation index.
- `01_RESEARCH_GRADE_ARCHITECTURE.md`: system architecture and research framing.
- `02_LANGGRAPH_WORKFLOW_SPEC.md`: graph state, nodes, and routing.
- `03_PERSIAN_NLU_AND_SCHEMA_LINKING.md`: Persian NLU, value linking, and schema linking.
- `04_RAG_CAG_AND_RETRIEVAL_DESIGN.md`: retrieval and context design.
- `05_SQL_GENERATION_VALIDATION_REFLEXION.md`: generation, validation, and repair.
- `06_EVALUATION_ABLATION_AND_PAPER_PLAN.md`: evaluation and ablation plan.
- `07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md`: implementation roadmap.
- `08_PROJECT_STRUCTURE_AND_FILE_MAP.md`: repository structure.
- `09_DATASET_AND_EVALUATION_FILES_GUIDE.md`: dataset and evaluation file guide.
- `10_FULL_DEVELOPMENT_ROADMAP_ZERO_TO_SOTA.md`: long-form historical roadmap.
- `11_SEMANTIC_BUSINESS_LOGIC_EVALUATION.md`: semantic/business judge workflow.
- `graph_workflow.mmd`: LangGraph Mermaid diagram (exported from `src/graph/workflow.py`).
- `PROJECT_INTRODUCTION_FOR_SUPERVISOR_FA.md`: فارسی معرفی پروژه برای سوپروایزر.
- `IMPROVEMENT_IDEAS_FROM_VTD_COLLECTION.md`: mined improvement candidates from the
  archived old etudes (`VTD COLLECTION/`, gitignored); ranked, evidence-linked, with
  anti-pattern catalog and adoption gates.

## Cleanup Rules

- Prefer updating canonical docs instead of adding new small one-off files.
- Do not manually edit final paper numbers.
- Do not cite diagnostic artifacts as final results.
- Keep SQL-positive, behavioral, and semantic/business evaluation separate.
- Move resolved risk notes out of `Risks.md` after mitigation is implemented and
  verified.
