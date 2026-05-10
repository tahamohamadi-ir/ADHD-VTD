# README Phase 0 Snippet for ADHD-VTD / PARS-SQL

## Feature Decision Matrix

| Feature | Milestone |
|---|---|
| Schema freeze and schema snapshot | Phase 0 gate |
| 50-question gold SQL audit | Phase 0 gate |
| DATASET_CARD.md | Phase 0 gate |
| Persian/number/date normalization | MVP / Phase 1 |
| Safety and ambiguity routing | MVP / Milestone 1.5 |
| Value retrieval | MVP / Phase 2-3 |
| Basic local SQL generation | Milestone 1 |
| CAG retrieval | After Milestone 1.5 |
| LangGraph full pipeline | Research runtime |
| Multi-candidate abstention | Paper 1 extension / Paper 2 |
| SQL Surgeon / Reflexion | After validation stack |
| Edge state machine | Edge-later |

## Phase 0 Checklist

```text
[ ] Freeze current SQLite schema.
[ ] Generate schema_snapshot.generated.json.
[ ] Select 50 SQL-positive questions.
[ ] Execute gold SQL against current DB.
[ ] Write data/audit/phase0_50q_audit_report.md.
[ ] Create DATASET_CARD.md.
[ ] Commit Phase 0 artifacts.
```
