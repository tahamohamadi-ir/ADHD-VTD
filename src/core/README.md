# پوشه `src/core`

این پوشه زبان مشترک بین ماژول‌های پروژه را تعریف می‌کند. هر چیزی که چند بخش مختلف باید روی معنی آن توافق داشته باشند، اینجا قرار می‌گیرد.

## فایل‌ها

- `types.py`: مدل‌های Pydantic برای خروجی‌های مشترک مثل `SchemaLinkResult`، `ValidationResult`، `ExecutionResult` و رکوردهای benchmark.
- `query_ir.py`: نمایش میانی پرسش (`QueryIR`) بین NLU، schema linking و generation.
- `enums.py`: enumهای intent، safety، action، error type و stageها.
- `exceptions.py`: exceptionهای دامنه‌ای مثل unsafe SQL، ambiguity، retrieval و generation error.
- `contracts.py`: Protocolهای تایپی برای componentهایی مثل normalizer، schema linker، SQL validator و executor.

## نکته فنی

وجود contract باعث می‌شود ماژول‌ها به implementation خاص وابسته نشوند. مثلاً graph می‌تواند با هر `SQLValidator` سازگار کار کند، به شرطی که contract را رعایت کند.

## ضدالگو

این پوشه نباید محل business logic شود. اگر منطق مربوط به NLU است، در `nlu/` بماند؛ اگر مربوط به SQL است، در `sql_validation/` بماند.
