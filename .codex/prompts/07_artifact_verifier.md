# 07 — Artifact Verifier Implementation

```text
Read AGENTS.md.
Read:
- docs/context-hub/ARTIFACT_RULES.md

Implement or improve:
scripts/verify_artifact.py

It must check:
1. config exists
2. predictions file exists
3. summary json exists
4. manifest entry exists
5. prediction count matches summary total
6. failure count matches summary failures
7. EX numerator/denominator matches predictions
8. valid SQL count matches predictions
9. unsafe SQL count matches predictions
10. deterministic_templates flag is explicit
11. dataset hash is present
12. selected cases hash is present
13. run is not smoke unless labeled smoke
14. mock judge is not cited as authoritative
15. placeholder reranker is not cited as real reranker

Add tests under tests/artifact/.

Return:
- verifier checks added
- test fixtures
- commands to run
- known limitations
```

---
