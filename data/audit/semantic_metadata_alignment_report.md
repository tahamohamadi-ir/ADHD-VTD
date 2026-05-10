# Semantic Metadata Alignment Report

**Generated at UTC:** 2026-05-10T19:49:21.800809+00:00
**Schema file:** `data\schema\schema_snapshot.json`
**Current table count:** 8
**Checks passed:** 11/11
**Checks failed:** 0

## Current Schema Tables

- `country_prevalence_long` (7 columns)
- `country_prevalence_wide` (10 columns)
- `dim_source` (5 columns)
- `mental_health_general` (15 columns)
- `student_depression` (21 columns)
- `student_habits_performance` (17 columns)
- `university_student_mental_health` (13 columns)
- `workplace_mental_health_survey` (31 columns)

## Forbidden Old Tables

The following old schema names must not appear in active metadata: `clinical_assessments, global_benchmarks, individuals_core, lifestyle_risk_factors, student_metrics`.

## Check Results

| Check | Status | Message |
|---|---|---|
| schema_graph nodes are current tables | ✅ PASS | All graph nodes are real current tables. |
| schema_graph edges reference valid tables/columns | ✅ PASS | All graph edges reference current schema. |
| column_aliases.fa.json references current schema | ✅ PASS | All alias references resolve to current schema. |
| schema_graph.json: embedded table.column refs | ✅ PASS | All embedded table.column refs resolve. |
| business_glossary.fa.json: embedded table.column refs | ✅ PASS | All embedded table.column refs resolve. |
| metric_definitions.json: embedded table.column refs | ✅ PASS | All embedded table.column refs resolve. |
| metric_definitions.json metric contracts | ✅ PASS | All metrics reference current tables/columns. |
| schema_graph.json: no active old-table references | ✅ PASS | No old table names found in active metadata. |
| column_aliases.fa.json: no active old-table references | ✅ PASS | No old table names found in active metadata. |
| business_glossary.fa.json: no active old-table references | ✅ PASS | No old table names found in active metadata. |
| metric_definitions.json: no active old-table references | ✅ PASS | No old table names found in active metadata. |

## Decision

✅ Semantic metadata is aligned with the current schema.

You may proceed to implement:

- `src/schema/value_linker.py`
- `src/nlu/intent_classifier.py`
- `src/nlu/ambiguity_detector.py`
- `src/nlu/safety_intent_detector.py`
- `src/sql_validation/safety_validator.py`
- `src/sql_validation/syntax_validator.py`
