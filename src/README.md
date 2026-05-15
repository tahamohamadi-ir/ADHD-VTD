# پوشه `src`

این پوشه package اصلی پروژه است. معماری آن شبیه یک compiler برای Persian Text-to-SQL طراحی شده است: ورودی فارسی مرحله‌به‌مرحله normalize، route، schema-link، prompt، validate و execute می‌شود.

## جریان اصلی

```text
question
  -> nlu
  -> schema / QIR / value linking
  -> retrieval / CAG
  -> generation
  -> sql_validation
  -> db
  -> output
```

`graph/` این مراحل را به‌صورت workflow به هم وصل می‌کند و `evaluation/` کیفیت آن‌ها را اندازه می‌گیرد.

## زیرپوشه‌ها

- `config/`: مسیرها، تنظیمات و feature flagها.
- `core/`: مدل‌های مشترک، enumها، exceptionها و contractها.
- `nlu/`: normalization، intent، ambiguity و safety برای فارسی.
- `schema/`: schema registry، schema linker، value linker، QIR planning و join reasoning.
- `generation/`: prompt، مدل محلی و parser خروجی LLM.
- `sql_validation/`: rewriter، syntax/safety/schema/join/aggregation/semantic validation.
- `db/`: اتصال و اجرای read-only روی SQLite.
- `graph/`: orchestration پژوهشی با LangGraph.
- `retrieval/`: Phase 7، Hybrid CAG/RAG، فعلاً نیازمند تکمیل.
- `reflexion/`: ماژولار کردن critic/repair/retry، منطق پایه فعلاً در graph است.
- `output/`: Phase 12، پاسخ فارسی، chart و explanation، فعلاً نیازمند تکمیل.
- `evaluation/`: benchmark، metric، ablation و گزارش.
- `utils/`: logging، JSONL، hashing و timing.

## اصل طراحی

LLM فقط تولیدکننده SQL کاندید است. safety، schema correctness، execution permission و reliability باید deterministic یا audit-friendly باشند.

## وضعیت توسعه

طبق `task.md` و `docs/`, foundation اصلی ساخته شده است: Phase 2، 3، 4، 5، 6، 8 و منطق پایه Phase 9. مسیر فعلی توسعه این است:

1. تکمیل `retrieval/` برای Hybrid CAG/RAG.
2. تکمیل benchmark runner و ablation در `evaluation/`.
3. تکمیل output layer.
4. افزودن reliability gate و multi-candidate consistency.
5. آماده‌سازی edge/runtime و paper packaging.

برای ترتیب دقیق اجرا، `DEVELOPMENT_ROADMAP.md` را بخوانید.
