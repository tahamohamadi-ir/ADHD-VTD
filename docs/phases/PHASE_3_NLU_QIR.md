# Phase 3 - NLU v2, Value Linking and QIR

**Status:** Completed  
**Updated:** 2026-05-15

## Goal

Phase 3 turns normalized Persian text into structured signals that later stages can use safely: concepts, schema links, resolved values and a QueryIR planning object.

## Implemented Files

| File | Role |
|---|---|
| `src/schema/concept_registry.py` | Domain concepts such as depression, anxiety, sleep, CGPA and student |
| `src/core/query_ir.py` | Pydantic QueryIR contract |
| `src/schema/query_planner.py` | Builds QueryIR from normalized question, intent and schema links |
| `src/schema/schema_linker.py` | Fuzzy schema/table/column linker with unresolved terms |
| `src/schema/value_linker.py` | Resolves natural-language values to DB values |
| `data/schema/column_aliases.fa.json` | Persian schema aliases |

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_concept_registry.py tests\tier1_unit\test_query_planner.py tests\tier1_unit\test_schema_linker.py tests\tier1_unit\test_value_linker.py -q
```

Covered behavior:

- concept lookup
- QueryIR construction
- schema linking confidence and unresolved terms
- gender, risk and depression flag value linking

## Remaining Work

No Phase 3 blocking item remains. Richer value labels for `Value Recall@k` move to Phase 11 research metrics.
