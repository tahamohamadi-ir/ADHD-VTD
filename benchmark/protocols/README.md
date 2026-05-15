# پوشه `benchmark/protocols`

این پوشه پروتکل‌های ارزیابی را نگه می‌دارد: چه داده‌ای استفاده شود، چه metricهایی گزارش شود و چه چیزی pass/fail محسوب شود.

## مواردی که باید در protocol ثبت شود

- split مورد استفاده: train/dev/test/full/special.
- metricها: EX، Valid SQL Rate، Reliability Score، safety rejection، clarification accuracy.
- قوانین مقایسه resultها.
- policy برخورد با behavioral items که نباید SQL تولید کنند.

## نکته فنی

در این پروژه ۵۰۰ آیتم به معنی ۵۰۰ SQL task نیست. بخشی از benchmark رفتاری است و سیستم باید گاهی SQL تولید نکند. protocol باید این تفاوت را صریح کند.
