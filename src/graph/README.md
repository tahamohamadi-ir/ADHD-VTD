# پوشه `src/graph`

این پوشه runtime پژوهشی پروژه را با LangGraph تعریف می‌کند. هدف آن traceability، retry، conditional routing و benchmark-friendly state management است.

## فایل‌ها

- `state.py`: مدل `VTDState` و stateهای میانی مثل `SQLAttempt` و `LinkedSchema`.
- `workflow.py`: ساخت graph و اتصال nodeها.
- `routes.py`: routeهای deterministic برای pre-generation، validation و execution.
- `checkpoints.py`: محل checkpointing آینده.
- `nodes/`: nodeهای workflow.

## وضعیت فعلی

طبق `task.md`، LangGraph orchestration پیاده‌سازی شده و nodeهای اصلی فعلاً در `nodes/base_nodes.py` قرار دارند. چند فایل node جداگانه هنوز placeholder هستند.

## گام‌های بعد

- اتصال `retrieve_context` به Phase 7.
- انتقال output واقعی به `src/output`.
- افزودن `generate_candidates` و `check_candidate_consistency` برای Phase 13.
- افزودن reliability object و routeهای `answer | clarify | abstain | warn`.

## نکته فنی

Graph باید business logic را فقط orchestrate کند. منطق سنگین باید در packageهای تخصصی مثل `nlu`، `schema`، `retrieval`، `generation`، `sql_validation`، `reflexion` و `output` بماند.
