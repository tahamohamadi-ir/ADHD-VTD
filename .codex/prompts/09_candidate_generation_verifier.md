# 09 — Candidate Generation + Verifier

```text
Read AGENTS.md.
Read:
- docs/context-hub/QUERY_SHAPE_CONTRACTS.md
- docs/context-hub/ARTIFACT_RULES.md
- src/graph/workflow.py
- src/graph/state.py
- src/sql_validation/validation_pipeline.py

Task:
Design and implement a minimal candidate generation + verifier stage.

Do not implement a complex multi-agent system.
Start with N=3 candidates maximum.

Requirements:
1. Generate diverse SQL candidates only when enabled by config.
2. Validate each candidate with syntax, safety, schema, join, aggregation, and shape checks.
3. Execute only candidates that pass safety validation.
4. Score candidates using runtime signals only, not gold labels.
5. Select best candidate or abstain/clarify if disagreement is high.
6. Record candidate traces.
7. Add ablation flag.

Candidate score should consider:
- validation_ok
- execution_ok
- shape_ok
- schema coverage
- value coverage
- candidate agreement
- unsafe penalty
- schema error penalty
- shape error penalty

Add tests:
- candidate safety
- candidate selection
- candidate disagreement abstention
- no gold leakage

Return:
- design summary
- files changed
- tests
- benchmark impact
- risks
```

---
