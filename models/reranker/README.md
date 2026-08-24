# پوشه `models/reranker`

این پوشه مدل‌های reranker را نگه می‌دارد.

## کاربرد

بعد از اینکه BM25 یا vector search چند candidate برگرداند، reranker می‌تواند بهترین مثال‌ها یا contextها را دوباره رتبه‌بندی کند.

## نکته فنی

Reranker معمولاً کندتر از retrieval اولیه است، اما می‌تواند context misleading را کم کند. اثر آن باید با metricهایی مثل Intent@k، Schema Recall@k و Example Helpfulness@k سنجیده شود.
