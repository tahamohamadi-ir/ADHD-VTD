# پوشه `src/graph/nodes`

این پوشه nodeهای LangGraph را نگه می‌دارد.

## وضعیت فعلی

- `base_nodes.py`: پیاده‌سازی عملیاتی nodeهای اصلی از initialize تا format.
- فایل‌هایی مثل `retrieval_node.py`، `output_node.py`، `validation_node.py` و مشابه آن‌ها فعلاً placeholder هستند.

## برنامه تفکیک

1. منطق retrieval به `retrieval_node.py`.
2. منطق validation و repair به `validation_node.py` و `src/reflexion`.
3. منطق output به `output_node.py` و `src/output`.
4. منطق multi-candidate consistency به nodeهای جدید Phase 13.

تا وقتی این تفکیک کامل نشده، `base_nodes.py` منبع عملیاتی nodeها است.
