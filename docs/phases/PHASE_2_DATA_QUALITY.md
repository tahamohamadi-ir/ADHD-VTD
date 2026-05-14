# Phase 2 — Data Quality Hardening

**Status:** Completed  
**Goal:** Establish a pristine dataset baseline for evaluation and LLM fine-tuning/few-shot prompting by building robust validation and structuring pipelines.

## Achievements

1. **Dataset Validation Pipeline:**
   Created a fully automated Python script suite (`scripts/validate_dataset.py`) to enforce data quality standards:
   - **Schema Diff Checker:** Compared frozen vs. generated schemas to prevent drift.
   - **SQL Execution Validation:** Executed all 400 golden SQL queries against the read-only test database (`vtd_health_research_v1.db`).
   - **Hallucinated Reference Check:** Parsed SQL to ensure 100% of tables and columns exist in the active `schema_snapshot.json`.
   - **Duplicate Detection:** Identified duplicate queries, duplicate IDs, and cross-file duplications.
   
2. **Bug Fixes Discovered During Validation:**
   - Identified that `vw_unified_individual_mental_health`, `vw_student_dashboard`, and `vw_country_prevalence_pivot` views were present in the database but **missing from the `schema_snapshot.json`**, causing false-positive hallucination reports. Wrote a script to properly append them from the SQLite PRAGMA.
   - Restored inadvertently deleted queries after analyzing documentation rules (Phase 0 Audit Rules) that dictate the 400-query benchmark dataset must remain perfectly intact.
   - Identified overlapping entries between the colloquial 140 set and the merged 400 set, correctly adjusting the validation target to only process canonical benchmark files.

3. **Data Formatting & Splitting:**
   - **JSONL Conversion:** Extracted `examples` from raw JSON files into standard `.jsonl` for easier streaming and processing by the upcoming generation pipeline.
   - **Stratified Dataset Splitting:** Programmatically divided the 400 merged benchmark into:
     - `train.json` / `train.jsonl` (280 examples)
     - `dev.json` / `dev.jsonl` (60 examples)
     - `test.json` / `test.jsonl` (60 examples)
   - Split the behavioral dataset into 40 dev / 60 test.
   - Generated a 50-question Phase 0 Audit CSV.

4. **Example Bank Expansion:**
   - Sampled and generated **50 `golden_examples.jsonl`** focusing on verified schemas, correct intents, and executing SQL.
   - Derived **30 `few_shot_bank.jsonl`** skeletons (patterns, intents, schemas) for prompt building.
   - Constructed **50 `indexed_examples.jsonl`** complete with embedding text features for the RAG/CAG retrieval pipeline.

5. **Schema Documentation:**
   - Generated `docs/generated/SCHEMA_REFERENCE.md` with 11 tables and 167 columns to be used as a Markdown-based LLM reference manual.

## Results
- **Pass Rate:** 400 out of 400 queries (100.0%) executed successfully.
- **Hallucinations:** 0 hallucinated table or column references.
- **Duplicates:** 0 cross-file duplication issues within canonical benchmarks.
- All tasks in Phase 2 are complete and ready to support **Phase 3 (NLU v2)** and **Phase 4 (SQL Validation Stack)**.

## Next Steps (Phase 3)
We are now moving to **Phase 3: NLU v2 (Value Linking & QIR)**, where we will build:
1. The `ConceptRegistry` for domains like depression, anxiety, and student demographics.
2. The `QueryIR` data model to decouple NL understanding from raw SQL syntax.
3. The `SchemaLinker` enhancements using RapidFuzz for semantic column matching.
