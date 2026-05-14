# Phase 2 — Data & Schema Quality Hardening — Task List

> **وضعیت:** 🔜 آماده برای شروع  
> **پیش‌نیاز:** Phase 1 ✅ تکمیل‌شده  
> **هدف:** اطمینان از صحت و کیفیت داده‌ها، اسکیما، و gold SQL قبل از شروع LLM pipeline  
> **معیار تکمیل:** همه 400 gold SQL در DB اجرا شوند + dataset splits ساخته شوند + golden examples expand شوند

---

## ۱. Schema Validation Scripts

### ۱.۱. `scripts/compare_schema_snapshots.py`
- [ ] diff بین `data/schema/schema_snapshot.json` و `schema_snapshot.generated.json`
- [ ] گزارش تفاوت‌ها: جدول‌های اضافه/حذف‌شده، ستون‌های تغییریافته
- [ ] خروجی: `results/data_quality/schema_diff_report.md`
- [ ] exit code: 0 اگر یکسان، 1 اگر تفاوت وجود دارد

**راهنمای پیاده‌سازی:**
- هر دو فایل JSON را load کن
- مقایسه tables, columns, types, primary keys, foreign keys
- خروجی markdown با جدول diff

### ۱.۲. `scripts/export_schema_markdown.py`
- [ ] تولید `docs/generated/SCHEMA_REFERENCE.md` از schema_snapshot.json
- [ ] شامل: جدول‌ها، ستون‌ها، type ها، row count، foreign keys
- [ ] ساخت directory `docs/generated/` در صورت عدم وجود

**راهنمای پیاده‌سازی:**
- از `SchemaRegistry` استفاده کن
- هر جدول یک section با لیست ستون‌ها
- FK relationships به شکل mermaid ER diagram

---

## ۲. Dataset Validation Scripts

### ۲.۱. `scripts/validate_dataset_sql.py`
- [ ] همه 400 SQL از `vtd_question_sql_400_merged_validated.json` را در DB اجرا کن
- [ ] برای هر SQL ثبت کن: OK/FAIL/SYNTAX_ERROR/SCHEMA_ERROR/EMPTY_RESULT
- [ ] خروجی: `results/data_quality/dataset_sql_validation_report.md`
- [ ] خروجی JSONL: `results/data_quality/sql_validation_results.jsonl`
- [ ] summary: تعداد pass/fail/error + لیست failed cases

**راهنمای پیاده‌سازی:**
- از `ReadOnlyExecutor` استفاده کن
- از `SQLSafetyValidator` و `SQLSchemaValidator` قبل از اجرا استفاده کن
- از `src/utils/jsonl.py` برای write results استفاده کن
- از `src/utils/timing.py` برای measure total time استفاده کن

### ۲.۲. `scripts/convert_dataset_to_jsonl.py`
- [ ] تبدیل `vtd_question_sql_400_merged_validated.json` → JSONL
- [ ] تبدیل `vtd_total_500_dataset_package.json` → JSONL
- [ ] تبدیل `vtd_question_sql_140_colloquial_additions_validated.json` → JSONL
- [ ] تبدیل `vtd_evaluation_special_100.json` → JSONL
- [ ] ذخیره در مسیرهای parallel (`.jsonl` کنار `.json`)

**راهنمای پیاده‌سازی:**
- از `src/utils/jsonl.py` (`write_jsonl`) استفاده کن
- validate هر رکورد دارای `id` و `question_fa` باشد

### ۲.۳. `scripts/check_duplicate_questions.py`
- [ ] بررسی duplicate IDs در همه dataset files
- [ ] بررسی duplicate questions (exact match + normalized match)
- [ ] گزارش: تعداد duplicates + لیست آن‌ها
- [ ] خروجی: `results/data_quality/duplicate_check_report.md`

**راهنمای پیاده‌سازی:**
- از `PersianNormalizer` برای normalized duplicate check استفاده کن
- both exact و normalized match بررسی شود

### ۲.۴. `scripts/check_schema_column_references.py`
- [ ] همه gold SQL ها را parse کن
- [ ] هر table و column reference را با schema_snapshot مقایسه کن
- [ ] لیست hallucinated columns (ستون‌هایی که در SQL هست اما در schema نیست)
- [ ] خروجی: `results/data_quality/hallucinated_columns_report.md`

**راهنمای پیاده‌سازی:**
- از `sqlglot` برای parse SQL استفاده کن
- از `SchemaRegistry.has_table()` و `has_column()` استفاده کن
- گزارش شامل: case_id, SQL, hallucinated columns

### ۲.۵. `scripts/validate_dataset.py`
- [ ] wrapper script که همه validation scripts را به ترتیب اجرا می‌کند
- [ ] ترتیب: schema_diff → duplicates → column_references → sql_validation
- [ ] خروجی نهایی: `results/data_quality/full_validation_summary.md`
- [ ] exit code: 0 اگر همه pass، 1 اگر هر کدام fail

---

## ۳. Dataset Splits

### ۳.۱. Train/Dev/Test Split
- [ ] از 400 example اصلی: 280 train / 60 dev / 60 test
- [ ] split stratified بر اساس `difficulty` و `category`
- [ ] ذخیره در:
  - `data/questions/train/train.json` + `train.jsonl`
  - `data/questions/dev/dev.json` + `dev.jsonl`
  - `data/questions/test/test.json` + `test.jsonl`
- [ ] Script: `scripts/split_dataset.py`

**راهنمای پیاده‌سازی:**
- از `sklearn.model_selection.train_test_split` با `stratify` استفاده کن
- seed ثابت: `VTD_RANDOM_SEED=42`
- هر split باید representative باشد

### ۳.۲. Behavioral Split
- [ ] از 100 special cases: 40 dev / 60 test
- [ ] ذخیره در:
  - `data/questions/special/behavior_dev.json`
  - `data/questions/special/behavior_test.json`
- [ ] split بر اساس `evaluation_type` stratified

### ۳.۳. Audit Cases
- [ ] ساخت `data/questions/audit/phase0_50q_audit.csv`
- [ ] 50 سوال SQL-positive نمایانگر همه difficulty ها و category ها
- [ ] CSV با ستون‌ها: id, question_fa, gold_sql, difficulty, category, manual_pass

---

## ۴. Golden Examples Expansion

### ۴.۱. `data/golden_sql/golden_examples.jsonl`
- [ ] فعلاً ~2KB (تقریباً خالی) — گسترش به حداقل 50 example
- [ ] هر example باید شامل باشد:
  ```json
  {
    "id": "ge_001",
    "question_fa": "...",
    "sql": "SELECT ...",
    "intent": "count_query",
    "difficulty": "easy",
    "tables": ["student_depression"],
    "columns": ["depression_flag"],
    "result_hash": "sha256..."
  }
  ```

### ۴.۲. `data/golden_sql/few_shot_bank.jsonl`
- [ ] فعلاً ~2KB — گسترش به حداقل 30 example
- [ ] هر example باید شامل باشد:
  ```json
  {
    "id": "fs_001",
    "question_fa": "...",
    "sql": "SELECT ...",
    "intent": "aggregation_query",
    "skeleton": "SELECT AGG(col) FROM table WHERE condition",
    "tables": ["student_depression"],
    "difficulty": "easy"
  }
  ```

### ۴.۳. `data/rag/indexed_examples.jsonl`
- [ ] فعلاً ~2KB — گسترش به حداقل 50 example
- [ ] هر example باید شامل باشد:
  ```json
  {
    "id": "idx_001",
    "question_fa": "...",
    "sql": "SELECT ...",
    "text_for_embedding": "question + schema context combined",
    "intent": "count_query",
    "tables": ["student_depression"],
    "columns": ["depression_flag", "gender"],
    "metadata": {"difficulty": "easy", "category": "depression"}
  }
  ```

---

## ۵. خروجی نهایی

- [ ] `results/data_quality/schema_diff_report.md`
- [ ] `results/data_quality/dataset_sql_validation_report.md`
- [ ] `results/data_quality/sql_validation_results.jsonl`
- [ ] `results/data_quality/duplicate_check_report.md`
- [ ] `results/data_quality/hallucinated_columns_report.md`
- [ ] `results/data_quality/full_validation_summary.md`
- [ ] `docs/generated/SCHEMA_REFERENCE.md`

---

## ۶. معیارهای قبولی Phase 2

| معیار | هدف |
|---|---|
| Gold SQL Pass Rate | ≥ 95% از 400 SQL باید در DB اجرا شود |
| Duplicate Questions | 0 duplicate IDs |
| Hallucinated Columns | 0 hallucinated columns در gold SQL |
| Schema Snapshot Diff | ≤ 5 تفاوت minor (یا 0 تفاوت major) |
| Golden Examples Count | ≥ 50 examples |
| Few-Shot Bank Count | ≥ 30 examples |
| Dataset Split | 280/60/60 train/dev/test ساخته شده |

---

## ۷. ترتیب اجرای پیشنهادی

```
1. scripts/compare_schema_snapshots.py     ← اول schema diff
2. scripts/check_schema_column_references.py ← بعد hallucinated columns
3. scripts/check_duplicate_questions.py     ← duplicates
4. scripts/validate_dataset_sql.py         ← اجرای همه SQL ها
5. scripts/convert_dataset_to_jsonl.py     ← تبدیل به JSONL
6. scripts/split_dataset.py               ← ساخت splits
7. scripts/export_schema_markdown.py       ← تولید docs
8. scripts/validate_dataset.py            ← wrapper نهایی
9. Golden examples expansion              ← دستی/نیمه‌خودکار
10. Few-shot bank expansion               ← دستی/نیمه‌خودکار
```

---

## ۸. وابستگی‌ها از Phase 1

| ابزار Phase 1 | استفاده در Phase 2 |
|---|---|
| `src/utils/jsonl.py` | خواندن/نوشتن JSONL files |
| `src/utils/hashing.py` | `result_hash` برای golden examples |
| `src/utils/timing.py` | اندازه‌گیری زمان validation |
| `src/utils/logging.py` | logging در scripts |
| `src/core/exceptions.py` | error handling (`DatasetError`, `SchemaNotFoundError`) |
| `src/sql_validation/` | validators برای SQL validation |
| `src/db/read_only_executor.py` | اجرای gold SQL ها |
