# پوشه `tests`

این پوشه test suite پروژه است. تست‌ها فقط برای bug نیستند؛ در این پروژه قراردادهای safety، schema grounding، Persian NLU و read-only execution را enforce می‌کنند.

## زیرپوشه‌ها

- `tier1_unit/`: تست‌های سریع و deterministic.
- `tier2_integration/`: تست‌هایی که چند component را با هم اجرا می‌کنند.
- `tier3_benchmark/`: تست‌های benchmark و regression سنگین‌تر.
- `fixtures/`: داده‌های کوچک و کنترل‌شده برای تست.

## اولویت تست

طبق `task.md`، تست‌های Phase 10 و قرارداد benchmark در اولویت‌اند:

- `test_dataset_loader_sampling.py`
- `test_metrics_bootstrap.py`
- `test_graph_attempt_trace.py`
- `test_benchmark_artifact_contract.py`

تست‌های NLU/validation پایه همچنان مهم‌اند:

- `test_date_normalizer.py`
- `test_colloquial_mapper.py`
- `test_safety_detector.py`
- `test_ambiguity_detector.py`
- `test_value_linker.py`

اجرای پایه:

```powershell
pytest tests/tier1_unit -v
```

اجرای پیشنهادی سریع:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit -q
```

تست integration قرارداد artifactهای agent benchmark:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier2_integration\test_agent_benchmark_trace.py -q
```

این تست LLM واقعی را اجرا نمی‌کند؛ workflow را mock می‌کند و فقط بررسی می‌کند runner خروجی‌های لازم مثل `predictions.jsonl`, `attempts.jsonl`, `summary` و `config` را درست بسازد.

راهنمای کامل اجرای تست‌ها و benchmarkها:

```text
docs/BENCHMARK_AND_TEST_GUIDE.md
```

## نکته فنی

هر چیزی که deterministic است باید در tier 1 تست شود. تست‌هایی که مدل LLM یا benchmark کامل لازم دارند باید وارد tier 3 شوند تا unit suite کند و شکننده نشود.
