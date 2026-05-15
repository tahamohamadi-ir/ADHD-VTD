# پوشه `docs`

این پوشه حافظه معماری و پژوهشی پروژه است. اگر `src/` پاسخ می‌دهد «کد چه کار می‌کند»، `docs/` پاسخ می‌دهد «چرا این معماری انتخاب شده، چه چیزی باید ساخته شود، و موفقیت با چه metricهایی سنجیده می‌شود».

## سندهای source-of-truth

- `00_INDEX.md`: نقشه کل سندها و قوانین غیرقابل مذاکره.
- `01_RESEARCH_GRADE_ARCHITECTURE.md`: معماری PARS-SQL و لایه‌های سیستم.
- `02_LANGGRAPH_WORKFLOW_SPEC.md`: state، nodeها، routeها و قرارداد LangGraph.
- `03_PERSIAN_NLU_AND_SCHEMA_LINKING.md`: NLU فارسی، value linking، ambiguity و schema linking.
- `04_RAG_CAG_AND_RETRIEVAL_DESIGN.md`: CAG/RAG، retrieval score، context packing و retrieval metrics.
- `05_SQL_GENERATION_VALIDATION_REFLEXION.md`: generation contract، validation stack، SQL Surgeon، reflexion و safe execution.
- `06_EVALUATION_ABLATION_AND_PAPER_PLAN.md`: EX، Reliability Score، ablation، error taxonomy و paper plan.
- `07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md`: ترتیب ساخت و milestone gateها.
- `08_PROJECT_STRUCTURE_AND_FILE_MAP.md`: ساختار canonical پوشه‌ها.
- `09_DATASET_AND_EVALUATION_FILES_GUIDE.md`: dataset، golden examples، behavioral eval و dataset governance.
- `10_FULL_DEVELOPMENT_ROADMAP_ZERO_TO_SOTA.md`: roadmap کامل از MVP تا SOTA-style.
- `THREAT_MODEL.md`: تهدیدها، privacy، safety و clinical disclaimer.

## زیرپوشه‌ها

- `generated/`: سندهای تولیدشده از artifactها، مثل schema reference.
- `phases/`: گزارش phaseهای انجام‌شده یا برنامه‌ریزی‌شده.

## ارتباط با نقشه توسعه

فایل `DEVELOPMENT_ROADMAP.md` در root، نسخه اجرایی و خلاصه‌شده همین docs است. وقتی می‌خواهیم تصمیم بگیریم «قدم بعدی چیست»، از این ترتیب استفاده می‌کنیم:

1. وضعیت واقعی کد و `task.md`.
2. قواعد source-of-truth در این پوشه.
3. اولویت‌های عملیاتی در `DEVELOPMENT_ROADMAP.md`.

اگر سندی feature پیشرفته‌ای پیشنهاد می‌کند اما roadmap آن را بعداً گذاشته، roadmap را برای اجرای فعلی ملاک بگیرید تا پروژه دچار drift نشود.
