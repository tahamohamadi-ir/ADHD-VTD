# پوشه `tests`

این پوشه test suite پروژه است. تست‌ها فقط برای bug نیستند؛ در این پروژه قراردادهای safety، schema grounding، Persian NLU و read-only execution را enforce می‌کنند.

## زیرپوشه‌ها

- `tier1_unit/`: تست‌های سریع و deterministic.
- `tier2_integration/`: تست‌هایی که چند component را با هم اجرا می‌کنند.
- `tier3_benchmark/`: تست‌های benchmark و regression سنگین‌تر.
- `fixtures/`: داده‌های کوچک و کنترل‌شده برای تست.

## اولویت تست

طبق `task.md`، این تست‌ها باید در اولویت تکمیل یا بازبینی باشند:

- `test_date_normalizer.py`
- `test_colloquial_mapper.py`
- `test_safety_detector.py`
- `test_ambiguity_detector.py`
- `test_value_linker.py`

اجرای پایه:

```powershell
pytest tests/tier1_unit -v
```

## نکته فنی

هر چیزی که deterministic است باید در tier 1 تست شود. تست‌هایی که مدل LLM یا benchmark کامل لازم دارند باید وارد tier 3 شوند تا unit suite کند و شکننده نشود.
