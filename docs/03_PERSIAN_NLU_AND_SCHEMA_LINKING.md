# 03 - Persian NLU and Schema Linking

**Status:** Updated with v2.3 value linking, mini stress-test, and Persian-specific reliability requirements  
**Version:** v2.3 Execution-Ready alignment  
**Updated focus:** implementation-first, reliability-first, edge-aware, benchmark-auditable.


## 1. Purpose

This file defines the Persian-specific understanding layer. For this project, Persian support is a potential research contribution, not a UI detail.

The goal is to transform informal Persian questions into stable semantic signals that can be linked to the database schema.

---

## 2. Persian Normalization Pipeline

Recommended order:

```text
raw text
  → Unicode NFKC normalization
  → Arabic/Persian character unification
  → Persian/Arabic digit conversion
  → ZWNJ handling
  → punctuation normalization
  → whitespace cleanup
  → colloquial expression mapping
  → domain synonym expansion
  → date normalization
  → tokenization
```

---

## 3. Character Normalization Rules

| Input | Output | Reason |
|---|---|---|
| `ك` | `ک` | Arabic Kaf to Persian Kaf |
| `ي` | `ی` | Arabic Yeh to Persian Yeh |
| `ى` | `ی` | Alef Maqsura normalization |
| `ة` | `ه` | Arabic Ta Marbuta in mixed text |
| `ؤ`, `إ`, `أ` | normalized form | reduce spelling variation |
| ZWNJ `\u200c` | space or controlled marker | improve tokenization and retrieval |

Recommended implementation:

```python
import unicodedata
import regex as re

class PersianNormalizer:
    def normalize(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("ك", "ک").replace("ي", "ی").replace("ى", "ی")
        text = text.replace("ة", "ه")
        text = re.sub(r"\u200c+", " ", text)
        text = re.sub(r"[\t\n\r]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
```

---

## 4. Number Normalization

Convert all Persian and Arabic digits to Western digits before SQL generation.

```text
۰۱۲۳۴۵۶۷۸۹ → 0123456789
٠١٢٣٤٥٦٧٨٩ → 0123456789
```

Example:

```text
"دانشجوهای بالای ۲۵ سال" → "دانشجوهای بالای 25 سال"
```

---

## 5. Persian Date Normalization

If your table uses Gregorian dates but users ask in Persian/Jalali dates, create a dedicated `PersianDateNormalizer`.

Examples:

| User expression | Normalized output |
|---|---|
| `فروردین ۱۴۰۴` | `2025-03-21 <= date < 2025-04-21` |
| `سال ۱۴۰۳` | `2024-03-20 <= date < 2025-03-21` |
| `ماه قبل` | explicit date range based on runtime date |
| `ترم قبل` | requires project-specific academic calendar |

Important rule:

> If the mapping from Persian temporal phrase to date range is not deterministic, ask clarification instead of guessing.

---

## 6. Colloquial Persian Mapping

The benchmark should include formal, semi-formal, colloquial, typo-heavy, and Finglish variants.

| Colloquial | Formal | Semantic label |
|---|---|---|
| `چندتا` | `چند تعداد` | count |
| `چقدره` | `چقدر است` | value request |
| `دانشجوها` | `دانشجویان` | student |
| `افسردگی دارن` | `دارای افسردگی هستند` | depression condition |
| `اضطرابشون` | `اضطراب آن‌ها` | anxiety metric |
| `بیشترین` | `حداکثر / رتبه اول` | ranking desc |
| `کمترین` | `حداقل / رتبه آخر` | ranking asc |

---

## 7. Domain Semantic Lexicon

Create a versioned dictionary:

```json
{
  "concepts": {
    "depression": {
      "fa_aliases": ["افسردگی", "افسرده", "خلق پایین", "دیپرشن", "depression"],
      "columns": ["clinical_assessments.phq9_score", "clinical_assessments.depression_diagnosis"],
      "default_rule": "Use phq9_score for severity; use depression_diagnosis for diagnosis status."
    },
    "anxiety": {
      "fa_aliases": ["اضطراب", "نگرانی", "anxiety", "استرس اضطرابی"],
      "columns": ["clinical_assessments.gad7_score", "clinical_assessments.anxiety_diagnosis"]
    },
    "student": {
      "fa_aliases": ["دانشجو", "دانشجویان", "محصل", "student"],
      "tables": ["student_metrics"],
      "join_key": "user_id"
    },
    "gpa": {
      "fa_aliases": ["معدل", "جی پی ای", "GPA", "gpa", "cgpa"],
      "columns": ["student_metrics.cgpa"],
      "anti_hallucination": ["Do not use gpa; use cgpa."]
    }
  }
}
```

---

## 8. Schema Graph

Flat dictionaries are not enough for strong Text-to-SQL. Use a schema graph.

Recommended graph nodes:

```text
Table: individuals_core
Column: individuals_core.user_id
Column: individuals_core.age
Concept: student
Concept: depression
Alias: افسردگی
Alias: دانشجو
Join: individuals_core.user_id = student_metrics.user_id
```

Recommended graph edges:

```text
Alias --maps_to--> Concept
Concept --uses_column--> Column
Table --has_column--> Column
Table --joins_to--> Table
Column --foreign_key_to--> Column
Concept --requires_join--> Table
```

Implementation:

```python
import networkx as nx

schema_graph = nx.MultiDiGraph()
```

---

## 9. Schema Linking Algorithm

Input:

```text
"میانگین افسردگی دانشجوهای دختر چقدره؟"
```

Algorithm:

```text
1. Normalize Persian text.
2. Extract candidate terms.
3. Exact-match terms against semantic lexicon.
4. Fuzzy-match terms with RapidFuzz.
5. Embedding-match unresolved terms if needed.
6. Expand concepts to columns.
7. Infer required tables and join paths.
8. Generate compact schema context.
9. Return confidence and unresolved terms.
```

Output:

```json
{
  "tables": ["individuals_core", "student_metrics", "clinical_assessments"],
  "columns": [
    "individuals_core.gender",
    "student_metrics.user_id",
    "clinical_assessments.phq9_score"
  ],
  "join_paths": [
    "individuals_core.user_id = student_metrics.user_id",
    "individuals_core.user_id = clinical_assessments.user_id"
  ],
  "filters": [
    {"column": "individuals_core.gender", "operator": "=", "value": "Female"}
  ],
  "confidence": 0.94,
  "unresolved_terms": []
}
```

---

## 10. Ambiguity Rules

Ask clarification when:

1. A metric can map to multiple columns and no default is safe.
2. A time expression is unclear.
3. The word “بهترین” does not specify metric.
4. User asks a domain concept not in schema.
5. Ranking query lacks ranking metric.
6. Chart request lacks measure/dimension.

Examples:

```text
User: بهترین دانشجوها رو بده
System: منظورتان از بهترین، بالاترین معدل، کمترین افسردگی، بیشترین حضور، یا معیار دیگری است؟
```

---

## 11. Unit Tests

Minimum tests:

```text
test_arabic_kaf_to_persian_kaf
test_arabic_yeh_to_persian_yeh
test_zwnj_to_space
test_persian_digits_to_western
test_colloquial_count_mapping
test_depression_to_phq9_score
test_gpa_does_not_map_to_fake_gpa_column
test_student_requires_student_metrics_join
test_ambiguous_best_requires_clarification
test_finglish_gpa_maps_to_cgpa
```

---

## 12. LLM-Friendly Implementation Prompt

```text
Implement the Persian NLU and schema linking modules from 03_PERSIAN_NLU_AND_SCHEMA_LINKING.md. Use deterministic rules first, RapidFuzz second, embeddings only as fallback. Every mapping must return confidence and evidence. Do not silently guess ambiguous terms. Add unit tests for each normalization, semantic mapping, and ambiguity rule.
```


---

## 13. v2.3 Additions: Finglish, Value Linking, and Mini Stress-Test

### 13.1 Value Linking

Schema linking must be extended with value linking. This is separate from column linking.

| User expression | Column candidate | Database value / rule |
|---|---|---|
| `زن`, `دختر`, `female` | `gender` | `Female` |
| `مرد`, `پسر`, `male` | `gender` | `Male` |
| `افسرده`, `depressed` | depression columns | diagnosis flag or PHQ-9 rule depending on table |
| `اضطرابی`, `anxious` | anxiety columns | diagnosis flag or GAD-7 rule depending on table |
| `کم خواب`, `کم‌خواب` | sleep columns | threshold rule, usually requires clarification if not specified |

Value linking output should include confidence and source:

```json
{
  "surface": "زن",
  "column": "individuals_core.gender",
  "value": "Female",
  "confidence": 1.0,
  "source": "lexicon"
}
```

### 13.2 Finglish and Typo Handling

Add a small controlled lexicon before embedding fallback:

```json
{
  "depression": ["depression", "depresion", "depreshen", "دیپرشن", "افسوردگی"],
  "anxiety": ["anxiety", "anxity", "استرس", "اضتراب"],
  "student": ["student", "daneshjoo", "دانشجوها", "دانشجویان"],
  "cgpa": ["gpa", "cgpa", "سی جی پی ای", "معدل"]
}
```

The system should keep typo/finglish mappings auditable. Do not silently add aggressive fuzzy mappings without logging.

### 13.3 Milestone 1.5 Mini Stress-Test

Before moving from basic generation to CAG/RAG or Reflexion, run this stress-test:

| Subset | Count | Expected behavior |
|---|---:|---|
| Finglish / typo | 10 | normalize and route correctly |
| Jalali date | 5 | convert deterministically or ask clarification |
| Unsafe / adversarial | 5 | refuse or abstain, no SQL execution |

Pass criteria:

```text
Finglish/typo routing accuracy >= 70%
Jalali date safe handling >= 80%
Unsafe rejection accuracy = 100%
No unsafe SQL reaches executor
```

### 13.4 Persian-Specific Error Categories

Add these categories to the error taxonomy:

| Error | Meaning |
|---|---|
| `JALALI_MAPPING_ERROR` | wrong Jalali-to-Gregorian mapping or unjustified date assumption |
| `COLLOQUIAL_MISMATCH_ERROR` | colloquial Persian phrase mapped to wrong intent/concept |
| `FINGLISH_RESOLUTION_ERROR` | Finglish/typo expression not resolved or resolved incorrectly |
| `VALUE_LINKING_ERROR` | user-facing value mapped to wrong DB value |
| `CLINICAL_TERM_AMBIGUITY_ERROR` | clinical term maps to multiple metrics without safe default |
