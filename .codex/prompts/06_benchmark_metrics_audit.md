# 06 — Benchmark Metrics Audit

```text
Read AGENTS.md.
Read:
- docs/context-hub/ARTIFACT_RULES.md
- src/evaluation/metrics.py
- src/evaluation/action_normalizer.py
- scripts/run_benchmark.py

Task:
Audit benchmark metric computation for:

[DESCRIBE METRIC OR RUN]

Check:
1. SQL-positive and behavioral metrics are separate.
2. Strict EX denominator is explicit.
3. Conservative EX can be reported when generated SQL is missing.
4. Valid SQL rate matches predictions.
5. Unsafe SQL count matches predictions.
6. Missing SQL count is separate.
7. Semantic/business judge is not mixed with strict EX.
8. Summary matches prediction rows.
9. No smoke/config/mock run can be cited as final.

Do not change datasets.

Add/update artifact tests if needed.

Return:
- metric issues
- denominator definitions
- patch summary
- tests
- commands
- paper table impact
```

---
