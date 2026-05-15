# راهنمای آموزشی پوشه‌های پروژه

این فایل نقشه سریع READMEهای محلی پروژه است. هدف READMEهای داخل هر پوشه این است که پروژه علاوه بر کد اجرایی، مثل یک پروژه آموزشی هم خوانده شود: هر پوشه توضیح می‌دهد چه نقشی دارد، چه فایل‌هایی در آن مهم‌اند، چه نکته فنی باید از آن یاد گرفت و مرحله بعد توسعه آن چیست.

## ترتیب پیشنهادی مطالعه

1. `README.md` ریشه برای هدف پروژه و اجرای سریع.
2. `DEVELOPMENT_ROADMAP.md` برای نقشه راه اجرایی از وضعیت فعلی به نسخه research-grade.
3. `task.md` برای checklist خام phaseها.
4. `docs/00_INDEX.md` برای نقشه سندهای معماری.
5. `docs/08_PROJECT_STRUCTURE_AND_FILE_MAP.md` برای source-of-truth ساختار پوشه‌ها.
6. `docs/09_DATASET_AND_EVALUATION_FILES_GUIDE.md` برای source-of-truth dataset و evaluation artifacts.
7. `src/README.md` برای معماری کد و مسیر pipeline.
8. `src/retrieval/README.md` برای جزئیات Hybrid RAG و نحوه بازیابی مثال‌ها.
9. `src/graph/README.md` برای منطق LangGraph و نودهای اجرایی.
10. `data/README.md` برای دیتابیس، schema، dataset، golden SQL و RAG artifacts.
11. `tests/README.md` و `results/README.md` برای ارزیابی، regression و گزارش‌گیری.

## محدوده پوشش

برای پوشه‌های مالکیت‌پذیر پروژه README محلی اضافه شده است: `src`، `data`، `docs`، `scripts`، `tests`، `benchmark`، `experiments`، `results`، `models`، `archive`، `logs`، `scratch` و زیرپوشه‌های کاربردی آن‌ها.

پوشه‌های cache و محیط مثل `.git`، `.venv`، `.idea`، `.pytest_cache`، `.ruff_cache`، `__pycache__` و `.cache/huggingface` عمداً README آموزشی مستقل نگرفته‌اند؛ این‌ها منطق پروژه نیستند و با ابزارها بازتولید می‌شوند.

## اصل طراحی آموزشی

این پروژه را مثل یک pipeline شبیه compiler بخوانید:

```text
Persian question
  -> normalization / intent / safety / ambiguity
  -> QIR and schema/value linking
  -> compact CAG context
  -> local LLM candidate SQL
  -> deterministic validation and repair
  -> read-only execution
  -> reliability-aware output
  -> benchmark trace and error analysis
```

## منبع‌های تصمیم‌گیری

- ساختار پوشه‌ها: `docs/08_PROJECT_STRUCTURE_AND_FILE_MAP.md`
- dataset و فایل‌های ارزیابی: `docs/09_DATASET_AND_EVALUATION_FILES_GUIDE.md`
- ترتیب build و gateها: `docs/07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md`
- validation/reflexion/safe execution: `docs/05_SQL_GENERATION_VALIDATION_REFLEXION.md`
- evaluation و ablation: `docs/06_EVALUATION_ABLATION_AND_PAPER_PLAN.md`
- وضعیت taskهای فعلی: `task.md`
- نقشه اجرایی جدید: `DEVELOPMENT_ROADMAP.md`
