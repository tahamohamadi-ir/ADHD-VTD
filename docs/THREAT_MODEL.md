# THREAT MODEL — PARS-SQL / VTD-Edge

> **Project:** PARS-SQL — Persian NL2SQL for Mental Health Research  
> **Data Domain:** ADHD / Mental Health / Student Well-being (Aggregate Research Datasets)  
> **Version:** 1.0 | **Date:** 2026-05-11  
> **Status:** Active — must be reviewed before any LLM integration

---

## 1. Data Classification

| Dataset | Sensitivity | Nature |
|---|---|---|
| `student_depression` | Aggregate/Synthetic | Public research dataset (India), no PII |
| `mental_health_general` | Aggregate/Synthetic | Simulated population-level data |
| `university_student_mental_health` | Aggregate/Anonymous | Survey data, no individual identifiers |
| `student_habits_performance` | Aggregate/Synthetic | Academic performance, no PII |
| `country_prevalence_long/wide` | Public | WHO/IHME-style global statistics |

**Conclusion:** No personally identifiable information (PII) is stored. All data is aggregate, synthetic, or anonymized public research data.

---

## 2. Threat Surface

### T1 — SQL Injection via Natural Language
**Risk:** Malicious user embeds SQL commands inside Persian query (e.g., `"نتایج رو نشون بده; DROP TABLE student_depression"`)  
**Mitigations:**
- `safety_intent_detector.py` — detects forbidden SQL keywords in NL input
- `safety_validator.py` — rejects any non-SELECT statement before execution
- `read_only_executor.py` — SQLite opened in read-only URI mode (`?mode=ro`)
- No write permissions granted at DB level

### T2 — Schema Hallucination
**Risk:** LLM generates SQL referencing non-existent tables/columns (`phq9_score`, `patient_id`, etc.), causing misleading results or errors  
**Mitigations:**
- `schema_validator.py` — checks every table/column in generated SQL against `schema_snapshot.json`
- Old-table detection (e.g., `phq9_score`, `adhd_score` flagged as hallucinated)
- Schema locked via `phase0_freeze_schema.py` — any drift triggers CI alert
- Tests in `tests/tier1_unit/test_schema_validator.py` must cover hallucinated columns

### T3 — Sensitive Individual-Level Output
**Risk:** Query returns individual-level rows that could re-identify a person (e.g., `SELECT * FROM student_depression WHERE age=17 AND city='Mumbai'`)  
**Mitigations:**
- `SELECT *` is forbidden — `safety_validator.py` blocks it
- `read_only_executor.py` enforces `LIMIT 50` on raw retrieval queries
- `reliability_gate.py` abstains on queries that would expose <5 rows in filtered context
- Aggregate-first behavior enforced: COUNT/AVG/GROUP BY preferred over raw rows

### T4 — Destructive SQL (DROP / DELETE / UPDATE)
**Risk:** LLM generates destructive SQL despite system prompt instructions  
**Mitigations:**
- `safety_validator.py` — whitelist SELECT-only; any DML/DDL rejected with `UNSAFE` label
- Read-only SQLite connection — even if executed, writes fail at DB level
- Double-layer: NL safety check (pre-generation) + SQL safety check (post-generation)

### T5 — Prompt Injection via Data Values
**Risk:** Data values in DB contain adversarial strings that, when injected into LLM prompt, alter model behavior  
**Mitigations:**
- Value injection into prompts uses `value_linker.py` output, not raw DB rows
- Schema context passed as structured dict, not raw text
- Prompt templates use Jinja2 with auto-escaping for string values

### T6 — Clinical Misuse / Medical Decision-Making
**Risk:** User relies on system output for clinical diagnosis, medication, or treatment decisions  
**Mitigations:**
- All outputs include disclaimer: *"این سیستم ابزار تحقیقاتی است و برای تصمیم‌گیری بالینی مناسب نیست"*
- `DATASET_CARD.md` clearly states: Not a diagnostic tool
- `answer_formatter.py` appends clinical disclaimer to all mental health query results
- System abstains on individual-level clinical questions (e.g., "آیا این دانش‌آموز افسرده است؟")

### T7 — Ambiguous Clinical Queries
**Risk:** Vague clinical question gets answered with misleading aggregate statistic  
**Mitigations:**
- `ambiguity_detector.py` — flags underspecified queries for clarification
- Clarification response returned instead of SQL when `needs_clarification=True`
- `reliability_gate.py` — abstains when reliability_score < threshold

### T8 — Model/Prompt Leakage
**Risk:** System prompt or internal schema exposed to end users  
**Mitigations:**
- System prompt not returned in API response
- Schema context injected at inference time, not stored in accessible config
- Prompt templates versioned but not exposed via public endpoints

---

## 3. Security Controls Summary

| Control | Layer | Status |
|---|---|---|
| No SELECT * | SQL Validator | ✅ Implemented |
| Read-only DB connection | DB Layer | ✅ Implemented |
| No DML/DDL | SQL Validator | ✅ Implemented |
| LIMIT enforcement | Executor | ✅ Implemented |
| Schema hallucination detection | Schema Validator | ✅ Implemented |
| NL injection detection | NLU Layer | ✅ Implemented |
| Clinical disclaimer in output | Output Layer | ⬜ Phase 12 |
| Aggregate-first behavior | Reliability Gate | ⬜ Phase 13 |
| Prompt injection resistance | Prompt Builder | ⬜ Phase 5 |
| Abstention on ambiguous clinical | Reliability Gate | ⬜ Phase 13 |

---

## 4. Out of Scope

- Authentication / Authorization (this is a research tool, not a production service)
- Network security / TLS (runs locally)
- GDPR / HIPAA compliance (no real patient data used)
- Adversarial model attacks (red-teaming planned for Phase 15)

---

## 5. Clinical Disclaimer (Standard)

> **⚠️ این سیستم یک ابزار تحقیقاتی است.**  
> خروجی‌های این سیستم صرفاً برای تحلیل داده‌های پژوهشی مورد استفاده قرار می‌گیرند.  
> این سیستم **ابزار تشخیص بالینی نیست** و نباید برای تصمیم‌گیری پزشکی، روان‌پزشکی، یا درمانی استفاده شود.  
> تمام داده‌ها Synthetic یا Aggregate هستند و هیچ اطلاعات فردی شناسایی‌پذیری ندارند.

---

## 6. Review Schedule

- **Pre-LLM Integration:** Review T1, T2, T3, T4 controls — ✅ Required before Phase 5
- **Pre-CAG Integration:** Review T5 (prompt injection via retrieved examples) — Required before Phase 7
- **Pre-Publication:** Full review + red-team session — Required before Phase 15
