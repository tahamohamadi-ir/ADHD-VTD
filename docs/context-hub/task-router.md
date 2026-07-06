# PARS-SQL Task Router for Codex

Use this router to choose the correct prompt.

| Task type | Use prompt | Context |
|---|---|---|
| uncertain / planning | 00_task_planning | AGENTS + INDEX |
| daily coding | 24_quick_daily_coding | AGENTS + relevant context |
| low EX / scalar grouped bug | 03_query_shape_contract | query-shape + failure-patterns |
| SQL safety/privacy | 04_safety_privacy | safety/privacy + schema_graph |
| Persian NLU/schema/value | 05 in CODEX_PROMPTS | aliases + glossary + metrics + values |
| benchmark metrics | 06_benchmark_metrics_audit | artifact rules + benchmark guide if needed |
| artifact verifier | 07_artifact_verifier | artifact rules |
| route prompt refactor | 08_route_specific_prompts | shape contracts + output parser |
| candidate verifier | 09_candidate_generation_verifier | graph + validation pipeline |
| reliability gate | 10 in CODEX_PROMPTS | reliability modules |
| paper writing | 11_paper_claims | tables + manifest + limitations |
| human audit | 12 in CODEX_PROMPTS | annotation docs |
| graph refactor | 14 in CODEX_PROMPTS | graph workflow/state/routes |
| pre-commit review | 17 in CODEX_PROMPTS | AGENTS + INDEX |
