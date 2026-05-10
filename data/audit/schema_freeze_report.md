# Schema Freeze Report

**Generated at UTC:** 2026-05-10T19:14:44.504813+00:00  
**Database:** `data\db\vtd_health_research_v1.db`  
**SQLite version:** 3.49.1  
**Table count:** 8  

## Table Summary

| Table | Rows | Columns | Foreign Keys | Indexes |
|---|---:|---:|---:|---:|
| `country_prevalence_long` | 32100 | 7 | 0 | 3 |
| `country_prevalence_wide` | 6420 | 10 | 0 | 1 |
| `dim_source` | 6 | 5 | 0 | 1 |
| `mental_health_general` | 10000 | 15 | 0 | 2 |
| `student_depression` | 27901 | 21 | 0 | 4 |
| `student_habits_performance` | 1000 | 17 | 0 | 2 |
| `university_student_mental_health` | 101 | 13 | 0 | 1 |
| `workplace_mental_health_survey` | 1259 | 31 | 0 | 2 |

## Freeze Decision

- [ ] Review `data/schema/schema_snapshot.generated.json`.
- [ ] If accepted, copy/update `data/schema/schema_snapshot.json`.
- [ ] Regenerate value dictionary.
- [ ] Re-run 50Q audit after any schema change.
