# PARS-SQL Agent Rules

## Mission

PARS-SQL is a Persian-aware, local/private, reliability-first Text-to-SQL framework for mental-health and student-lifestyle analytics.

The goal is not only to generate SQL. The goal is to produce safe, auditable, reproducible, privacy-aware analytical answers.

## Non-negotiable rules

1. Never generate or approve destructive SQL.
   Allowed SQL is only:
   - SELECT ...
   - WITH ... SELECT ...

2. Never allow INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE, ATTACH, DETACH, PRAGMA, VACUUM, REINDEX, EXEC, CALL.

3. Never execute SQL outside the read-only executor.

4. Never use SELECT * in user-visible final projections.
   COUNT(*) is allowed.

5. Never create synthetic cross-domain joins.
   Cross-domain joins are forbidden unless `data/schema/schema_graph.json` explicitly allows the edge.

6. For sensitive mental-health fields, suicidality, high-risk individuals, or personal information:
   - prefer aggregate analysis,
   - refuse row-level disclosure,
   - never expose names, IDs, emails, phone numbers, or individual rows.

7. Behavioral cases are not strict EX cases.
   Do not mix behavioral expected-action accuracy with SQL-positive execution accuracy.

8. Main paper results must not use deterministic template packs unless the table explicitly says so.
   For the main local no-template run, `deterministic_templates=false`.

9. Do not cite smoke runs, config-only runs, dry runs, failed judge runs, or placeholder reranker runs as final paper results.

10. Every reported result must come from an artifact:
    - config
    - predictions
    - summary
    - manifest
    - paper table
    - hash or run ID

11. Do not modify dataset files without:
    - updating dataset version,
    - updating hashes,
    - documenting the change,
    - updating the manifest.

12. Prefer clarification over hallucination.
    If schema, value, metric, domain, or user intent is ambiguous, ask clarification or abstain.

## Development workflow

Before making changes:

1. Read this file.
2. Read `docs/context-hub/INDEX.md`.
3. Load only the relevant context file for the task.
4. Identify affected modules.
5. Add or update tests first when possible.
6. Make the smallest safe change.
7. Run the smallest relevant test suite.
8. Report:
   - changed files,
   - tests run,
   - metrics affected,
   - risks,
   - next step.

## Project architecture

Core modules:

- `src/nlu/` Persian normalization, colloquial mapping, intent, ambiguity, safety intent
- `src/schema/` schema loading, schema linking, value linking, schema graph
- `src/retrieval/` BM25/vector/hybrid retrieval and context packing
- `src/generation/` prompt building, local LLM, output parsing
- `src/sql_validation/` syntax, safety, schema, join, aggregation, semantic, shape validation
- `src/db/` read-only SQLite execution
- `src/evaluation/` metrics, action normalization, reliability, trace, judging
- `src/graph/` LangGraph workflow and nodes
- `scripts/` benchmark, ablation, judging, artifact verification
- `data/schema/` frozen schema, graph, aliases, glossary, metrics, value dictionary
- `data/questions/` benchmark and behavioral datasets
- `results/` generated benchmark artifacts

## Coding standards

- Python 3.12.
- Use type hints.
- Prefer small pure functions.
- Keep side effects explicit.
- Avoid hidden global state.
- Do not hard-code dataset paths outside `src/config/paths.py`.
- Do not hard-code metrics inside paper text.
- Do not duplicate metric formulas across scripts.
- Prefer dataclasses or Pydantic models for runtime contracts.
- Keep prompts versioned.
- Keep experiment configs immutable after publication.

## Testing standards

Every meaningful change must include at least one of:

- unit test,
- integration test,
- artifact consistency test,
- benchmark smoke run,
- manual audit note.

Required tests for critical modules:

- safety validator
- schema validator
- join validator
- shape validator
- output parser
- dataset loader
- action normalizer
- reliability gate
- read-only executor
- benchmark artifact verifier

## Paper/reporting rules

Use careful wording:

Allowed:
- "reliability-first"
- "local/private"
- "Persian-aware"
- "benchmark and framework"
- "strict execution accuracy"
- "semantic/business correctness under judge"
- "behavioral expected-action accuracy"

Forbidden unless directly proven:
- "state-of-the-art"
- "high accuracy"
- "clinical decision support"
- "diagnostic system"
- "guarantees privacy"
- "solves Persian Text-to-SQL"
- "schema linking significantly improves EX"
- "value linking significantly improves EX"

## Default response format for the agent

When completing a task, always return:

1. Summary
2. Files changed
3. Tests added/updated
4. Commands run
5. Risks
6. Next recommended step

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
## Codex Skills

Use installed Codex skills automatically when they are relevant to the task.
Before solving a task, compare the task with available skill descriptions and activate the most specific matching skill.
Prefer repo-level skills in `.agents/skills` over generic user-level skills.
Do not activate unrelated skills.
If no installed skill matches the task, continue normally.