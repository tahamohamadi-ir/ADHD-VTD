# PARS-SQL — Persian NLU, Schema Linking, and Value Linking Rules

Apply this rule when working on:

- `src/nlu/**`
- `src/schema/**`
- `data/schema/**`
- Persian normalization,
- colloquial mapping,
- ambiguity detection,
- intent classification,
- schema linking,
- value linking,
- metric definitions.

## Persian/NLU requirements

Handle:

- Persian digits,
- Arabic/Persian character variants,
- half-space,
- colloquial Persian,
- common typos,
- Finglish,
- mixed Persian-English,
- domain terms: depression, anxiety, stress, sleep, CGPA, treatment, prevalence, mental-health risk.

## Schema-linking rules

1. Use `column_aliases.fa.json`, `business_glossary.fa.json`, and `metric_definitions.json` before guessing.
2. Do not hallucinate tables or columns.
3. Prefer single-domain routing.
4. If a term maps to multiple domains, ask clarification unless context disambiguates.
5. Record unresolved terms.
6. Do not create joins not allowed by schema graph.
7. Schema linking must support role labels: metric, dimension, filter, temporal, identifier, sensitive.

## Value-linking rules

1. Use `value_dictionary.generated.json` and manual aliases.
2. Resolve categorical values only when confidence is high.
3. Keep alternatives when ambiguous.
4. Ask clarification for ambiguous values.
5. Do not invent values not present in the value dictionary unless explicitly documented.
6. For binary flags, follow metric definitions.

## Ambiguity rules

Ask clarification for:

- vague rankings without metric,
- "best/worst" without criterion,
- chart request without measure/dimension,
- causal proof requests,
- context-dependent follow-ups,
- unclear domain/table,
- ambiguous sensitive values.

## Required tests

- `tests/unit/test_persian_normalizer.py`
- `tests/unit/test_colloquial_mapper.py`
- `tests/unit/test_ambiguity_detector.py`
- `tests/unit/test_intent_classifier.py`
- `tests/unit/test_term_extractor.py`
- `tests/unit/test_schema_linker.py`
- `tests/unit/test_value_linker.py`
