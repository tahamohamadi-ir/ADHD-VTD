---
name: persian-nlu-schema-linking
description: Use this skill for Persian normalization, colloquial and Finglish mapping, ambiguity detection, intent routing, schema linking, value linking, and metric definitions.
---

# Skill: Persian NLU and Schema Linking

## Purpose

Use this skill for Persian normalization, colloquial/Finglish mapping, ambiguity detection, intent routing, schema linking, value linking, and metric definitions.

## Required context

Read:

- `AGENTS.md`
- `docs/context-hub/QUERY_SHAPE_CONTRACTS.md`
- `data/schema/column_aliases.fa.json`
- `data/schema/business_glossary.fa.json`
- `data/schema/metric_definitions.json`
- `data/schema/value_dictionary.generated.json`
- `src/nlu/`
- `src/schema/`

## Persian rules

Handle:

- Persian digits
- Arabic/Persian character variants
- half-space issues
- colloquial Persian
- common typos
- Finglish
- mixed Persian-English
- domain terms such as depression, anxiety, stress, CGPA, sleep, treatment, prevalence

## Schema-linking rules

1. Prefer single-domain routing.
2. Do not hallucinate columns.
3. Use aliases and glossary before guessing.
4. Use metric definitions for rates and averages.
5. If a term maps to multiple domains, ask clarification unless context disambiguates.
6. Record unresolved terms.

## Value-linking rules

1. Resolve categorical values only when confidence is high.
2. Keep alternatives.
3. Ask clarification for ambiguous values.
4. Do not invent values not present in value dictionary unless explicitly allowed.
5. For binary flags, respect metric definitions.

## Tests required

- `tests/unit/test_persian_normalizer.py`
- `tests/unit/test_colloquial_mapper.py`
- `tests/unit/test_ambiguity_detector.py`
- `tests/unit/test_intent_classifier.py`
- `tests/unit/test_schema_linker.py`
- `tests/unit/test_value_linker.py`

## Output format

Return:

- normalized terms
- schema candidates
- value candidates
- unresolved terms
- confidence
- tests