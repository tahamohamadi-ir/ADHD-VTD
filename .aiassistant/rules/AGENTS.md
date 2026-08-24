# PARS-SQL / ADHD-VTD — Global AI Assistant Rules

You are working on PARS-SQL / ADHD-VTD: a Persian-aware, local/private, reliability-first Text-to-SQL research system for mental-health and student-lifestyle analytics.

Your goal is to help build a publication-grade AI research codebase, not merely make code run.

## Core mission

- Build a safe, auditable, reproducible Persian Text-to-SQL framework.
- Prioritize reliability, validation, abstention, privacy, and artifact-backed evaluation.
- Improve strict execution accuracy without weakening safety, privacy, reproducibility, or scientific validity.
- Treat this project as a research artifact for publishable AI/NLP/Text-to-SQL papers.

## Non-negotiable safety rules

1. Never bypass SQL validation.
2. Never bypass read-only execution.
3. Only `SELECT` and `WITH ... SELECT` are allowed.
4. Reject `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `REPLACE`, `MERGE`, `ATTACH`, `DETACH`, `PRAGMA`, `VACUUM`, `REINDEX`, `EXEC`, `EXECUTE`, `CALL`.
5. Reject multiple SQL statements.
6. Reject SQL comments in generated SQL.
7. Reject top-level `SELECT *` and `table.*`.
8. `COUNT(*)` is allowed.
9. Never expose row-level sensitive mental-health data.
10. Never reveal names, student IDs, emails, phone numbers, addresses, exact personal rows, or all high-risk/suicidal individuals.
11. Never create cross-domain joins unless `data/schema/schema_graph.json` explicitly allows the edge.
12. Prefer clarification/refusal over hallucination.

## Research and benchmark rules

1. Keep SQL-positive evaluation and behavioral evaluation separate.
2. Keep strict EX separate from semantic/business judge correctness.
3. Do not cite smoke runs, partial runs, failed runs, mock judge outputs, config-only files, or placeholder reranker runs as final paper results.
4. Main local paper results must use `deterministic_templates=false` unless explicitly labeled otherwise.
5. Every reported number must come from artifacts: config, predictions, summary, manifest, paper table, or judge summary.
6. Always report numerator and denominator.
7. If generated SQL is missing, report missing count separately.
8. Do not change dataset files without updating version, hash, manifest, and documentation.
9. Do not overfit to test IDs, gold SQL, failure IDs, or benchmark-specific templates.

## Known current weaknesses

- Strict EX is modest.
- Semantic/business correctness is better than strict EX but still not high.
- Behavioral safety and abstention are strong.
- Behavioral SQL-positive execution is weak.
- Full positive400 ablation shows CAG/examples are the strongest performance driver.
- Schema linking and value linking need component-level evaluation before strong claims.
- Human validation / spot-check is needed for stronger publication claims.
- These weakness categories use different denominators and must be reported separately.

## Development workflow

Before editing:

1. Read this rule file.
2. Identify the task type: safety, query shape, benchmark, NLU/schema, prompt, paper claim, or architecture.
3. Load only the smallest relevant context.
4. Make a short plan.
5. Make the smallest safe patch.
6. Add or update tests for every behavior change.
7. Run the smallest relevant test suite.
8. Report changed files, tests, commands, risks, and next step.

## Response format after each task

Always report:

1. Summary
2. Files changed
3. Tests added or updated
4. Commands run
5. Results
6. Risks
7. Next recommended step


## Root note

This file mirrors the PyCharm AI Assistant global rule. Keep it in the repository root so coding agents that read AGENTS.md use the same constraints.
