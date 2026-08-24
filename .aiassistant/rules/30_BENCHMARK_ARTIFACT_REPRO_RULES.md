# PARS-SQL — Benchmark, Metrics, and Artifact Rules

Apply this rule when working on:

- `scripts/run_benchmark.py`
- `scripts/run_ablation.py`
- `scripts/analyze_*`
- `src/evaluation/**`
- `results/**`
- `data/questions/**`
- `docs/paper/**`
- manifests, summaries, paper tables, judge outputs

## Dataset separation

There are three evaluation families:

### SQL-positive

Use for:

- strict execution accuracy,
- valid SQL rate,
- result hash match,
- execution error rate,
- missing SQL.

### Semantic/business

Use for:

- semantic/business correctness,
- judge provider,
- judge model,
- prompt version,
- authoritative status,
- human spot-check status.

### Behavioral

Use for:

- expected-action accuracy,
- clarification accuracy,
- safety rejection,
- abstention precision/recall,
- no-SQL routing,
- unsafe SQL count.
- These behavioral metrics are reported separately from SQL-positive strict EX
  because they use different denominators.

Metric-family policy: SQL-positive, semantic/business, and behavioral
families use different denominators and must be reported separately. Do not mix
behavioral cases into strict EX.

## Metric rules

Always report:

- numerator,
- denominator,
- eligible cases,
- excluded cases,
- missing generated SQL count.

Strict EX and semantic/business correctness are separate and must be reported
separately.

## Final result restrictions

Never cite as final paper result:

- smoke runs,
- partial runs,
- failed runs,
- dry runs,
- config-only files,
- mock judge outputs,
- pilot judge if full judge exists,
- placeholder reranker outputs,
- deterministic template results as main local model results unless explicitly labeled.

## Main local run requirements

For main paper result:

- `deterministic_templates=false`,
- self-overlap retrieval excluded,
- config saved,
- predictions saved,
- summary saved,
- manifest saved,
- dataset hash saved,
- selected cases hash saved,
- model identity saved.

## Artifact validity

A valid benchmark artifact must include:

- config,
- predictions,
- benchmark results,
- summary json,
- summary md,
- failures if any,
- manifest entry,
- model,
- prompt version,
- dataset path/hash,
- selected cases hash,
- git commit if available.

## Paper table rule

All final paper tables must be generated from artifacts. Do not manually edit final numbers.

Final paper tables must include `dataset_hash`, `selected_cases_hash`, and
artifact provenance such as config, predictions, summary, benchmark CSV,
manifest, or judge summary.

## Required tests

- `tests/unit/test_metrics.py`
- `tests/unit/test_action_normalizer.py`
- `tests/unit/test_reliability_metrics.py`
- `tests/artifact/test_manifest_integrity.py`
- `tests/artifact/test_paper_table_consistency.py`
- `tests/artifact/test_no_fake_final_results.py`
