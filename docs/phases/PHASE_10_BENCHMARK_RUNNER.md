# Phase 10 - Benchmark Runner

**Status:** In progress  
**Updated:** 2026-05-15  
**Scope:** Reproducible benchmark command, artifact layout, Markdown/JSON summaries, and initial non-LLM benchmark modes.

## Goal

Phase 10 turns the project from a demoable agent into a measurable system. Every run should produce enough evidence to answer:

- Which dataset and config were used?
- What did the system predict for each case?
- Which cases failed or missed?
- Which metrics were computed?
- Can the run be repeated later from the same command?

## Implemented Files

| File | Role |
|---|---|
| `scripts/run_benchmark.py` | CLI entry point for reproducible benchmark runs |
| `src/evaluation/report_generator.py` | Generic benchmark Markdown report generation |
| `src/evaluation/retrieval_metrics.py` | Retrieval metric summary used by retrieval mode |
| `src/evaluation/error_analyzer.py` | Basic failure grouping by error, difficulty, and category |
| `results/benchmark/README.md` | Artifact contract for benchmark outputs |

## Modes

### `retrieval`

Measures evidence retrieval quality before full SQL generation. It builds a `RetrievalQuery` from the question and gold SQL schema references, retrieves top-k examples, then reports:

- `retrieval_hit_rate`
- `retrieval_miss_rate`
- `schema_recall_at_k`
- `intent_match_at_k`
- `skeleton_match_at_k`

This mode is part of Phase 7 validation. It is not an execution accuracy benchmark.

### `gold`

Runs a non-LLM sanity benchmark. It executes each gold SQL as both generated SQL and reference SQL, then compares result hashes. This validates:

- read-only executor
- SQL safety gate
- result serialization/hash comparison
- metric/report artifact generation

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 20 --top-k 3
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset dev --sample 20
```

Supported dataset aliases:

- `dev`
- `test`
- `positive400`
- `behavior_dev`
- `behavior_test`
- `phase0`

Use `--path <dataset.json>` for a custom dataset.

## Artifact Layout

```text
results/benchmark/<timestamp>_<config_id>/
  config.json
  predictions.jsonl
  failures.jsonl
  summary.json
  summary.md
  retrieval_metrics.json   # retrieval mode only
```

## Current Limitations

- No full `agent` mode yet; LangGraph end-to-end benchmarking remains next work.
- `attempts.jsonl` is not generated yet because retry/reflexion trace capture is not standardized.
- Error taxonomy is still basic and must be aligned with `docs/06_EVALUATION_ABLATION_AND_PAPER_PLAN.md`.
- Value-link-aware retrieval metrics need gold value labels.

## Next Work

1. Add `--mode agent` using the LangGraph workflow.
2. Save prompt, validation, retry and execution attempts to `attempts.jsonl`.
3. Expand `error_analyzer.py` with research-grade taxonomy.
4. Add CSV/table exports for paper-ready reporting.
5. Add benchmark configs for ablation runs.
