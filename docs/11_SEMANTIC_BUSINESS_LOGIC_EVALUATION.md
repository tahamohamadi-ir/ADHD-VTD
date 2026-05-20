# 11 - Semantic Business Logic Evaluation (LLM-as-a-Judge)

**Status:** Phase 16 in progress - deterministic mock provider, OpenRouter provider, standalone artifact judge, `run_benchmark.py --use-judge` integration, live Qwen/DeepSeek pilots, canonical all-failure reruns, judge-agreement reporting, conservative consensus, redaction policy, and semantic policy v1 are implemented; local judge, v1 reruns, and larger review remain open  
**Dependency:** Phase 10 must first store complete prompt/response/SQL/result traces.

## 1. Rationale

Execution Accuracy (EX) measures if the SQL returns the same result set as the gold query. However, in complex clinical and mental health domains:
1. Different SQL queries can return the same results on a specific dataset but have different business logic.
2. A query might be "technically correct" (executes) but "conceptually wrong" (e.g., uses the wrong metric for anxiety).
3. The generated explanation might contradict the SQL logic.

To achieve **State-of-the-Art (SOTA)** research quality, we introduce an LLM-as-a-Judge layer.

This layer is intentionally separate from standard benchmark execution:

```text
Execution correctness: Did generated SQL return the same result as gold SQL?
Business correctness: Does generated SQL actually answer the user's question?
```

Both must be reported. Neither replaces the other.

Current semantic policy version: `phase16_sql_business_logic_v1`.

Under v1, semantic/business correctness means: **does the generated SQL answer the user's actual question?** Gold SQL is a reference implementation, not a mandatory output schema. A generated query can be semantically correct if it differs from gold SQL, includes extra harmless output columns/parameters, or omits support columns that only appear in the reference query, as long as the user can still get the answer they asked for. Conversely, a query is semantically incorrect when the core metric, filter, grouping, table, time/value logic, or aggregation prevents the user from answering their question.

Important traceability rule: judgment artifacts produced with `phase16_sql_business_logic_v0` must not be silently reinterpreted under v1. Rerun the judge when a paper table or final report needs v1 labels.

For paper reporting, Phase 16 now supports two explicit judge policies:

| Policy | CLI | Meaning |
|---|---|---|
| Semantic utility | `--judge-policy semantic` | The generated SQL is correct if the user can answer the question they asked, even if the query differs from gold or omits gold-only support columns. |
| Strict reference | `--judge-policy strict` | The generated SQL must satisfy the stricter reference/gold output contract, including reference-required filters, grouping, ordering, thresholds, and output shape. |

These should be reported as separate columns, for example `semantic_user_question_correct` and `strict_reference_correct`. Do not mix the two into one metric.

## 2. Methodology

The judge is an independent high-reasoning model that acts as a senior clinical/data analyst. The current preferred path uses OpenRouter-hosted open-model-ecosystem judges first (`qwen/qwen3.6-plus`, `deepseek/deepseek-v4-flash`) and reserves more expensive closed models for small disagreement/adjudication subsets only.

### Input to the Judge
- **Original Persian Question**: Raw user intent.
- **Normalized Context**: The system's understanding of the question.
- **Linked Schema**: Tables and columns used.
- **Generated SQL**: The candidate produced by the local agent.
- **Gold SQL**: The ground-truth reference implementation, not a mandatory exact output shape for semantic judging.
- **Execution Sample or Hash**: Redacted top rows, aggregate preview, or result hash.
- **Validation Trace**: SQL validation issues, repair attempts, and final action.
- **Generated Explanation**: Final answer/explanation shown by the system, if available.

### Judging Rubric (0-5 Scale)
| Score | Label | Description |
|---|---|---|
| 5 | Perfect | Logic is correct, efficient, and perfectly maps to the question. |
| 4 | Correct | Minor stylistic differences or slightly inefficient, but logic is sound. |
| 3 | Minor Logic Error | Result might be correct for this dataset, but the logic has a flaw (e.g., wrong join type). |
| 2 | Major Logic Error | The query uses the wrong columns or metrics but happens to execute. |
| 1 | Execution Failure / Hallucination | The query executes but is completely unrelated to the intent. |
| 0 | Catastrophic | Unsafe, toxic, or total gibberish. |

Required boolean labels:

```text
semantic_business_correct
metric_correct
filter_correct
join_logic_correct
aggregation_correct
answer_explanation_consistent
needs_human_review
```

## 3. Technical Implementation

### Module: `src/evaluation/llm_judge.py`
- [x] Provides a common provider protocol and deterministic `MockJudgeProvider` for tests/offline scaffolding.
- [x] `MockJudgeProvider` is intentionally conservative:
  - exact SQL match after normalization -> scaffold-correct;
  - missing/invalid SQL -> scaffold-incorrect;
  - valid SQL `RESULT_MISMATCH` -> `requires_semantic_review`, no invented semantic label.
- [x] Standalone artifact judgment entry point exists:
  `scripts/judge_benchmark_artifact.py`.
- [x] Uses environment variables for API keys when online providers are used.
- [x] Uses environment variables for OpenRouter API keys and model selection.
- [x] Must never hardcode API keys in code.
- [x] Add `OpenRouterJudgeProvider`.
- [ ] Add direct `OpenAIJudgeProvider`.
- [ ] Add `LocalJudgeProvider`.
- [ ] Implements batching where provider allows it.
- [x] Supports provider reasoning metadata beyond deterministic scaffold reasons; raw private reasoning is not stored as a correctness claim.
- [x] Stores token usage fields when provider usage is returned; dollar cost is not inferred unless billing data is added.

### Integration: `run_benchmark.py --use-judge`
- [x] Direct `run_benchmark.py --use-judge --judge-provider mock` integration exists for offline mock mode.
- [x] Direct `run_benchmark.py --use-judge --judge-provider openrouter` integration exists.
- [x] Live OpenRouter judgment pilots have run with user-supplied API key.
- [ ] Direct `run_benchmark.py --use-judge` integration for local providers is still pending.
- [x] Offline/standalone judgment from an existing benchmark artifact is available:

```powershell
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\manual_a4_after_generation_token_cap `
  --output-dir results\judgments\20260519_phase16_mock_a4_token_cap `
  --judge-provider mock
```

Current standalone scaffold generates:

- `judgments.jsonl`
- `judge_reasoning.md`
- `judge_summary.json`
- `judge_costs.json`
- `semantic_business_summary.csv`
- direct benchmark-run integration.

OpenRouter configuration:

```powershell
$env:OPENROUTER_API_KEY = "<your key>"
$env:VTD_OPENROUTER_JUDGE_MODEL = "qwen/qwen3.6-plus"
$env:OPENROUTER_HTTP_REFERER = "https://github.com/local/ADHD-VTD"
$env:OPENROUTER_APP_TITLE = "ADHD-VTD Phase16 Judge"
```

Live OpenRouter pilot command pattern:

```powershell
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\manual_a4_after_generation_token_cap `
  --output-dir results\judgments\<run_name> `
  --judge-provider openrouter `
  --judge-model qwen/qwen3.6-plus `
  --judge-reasoning `
  --judge-sample-size 2
```

Reasoning mode:

- `--judge-reasoning` sends `reasoning: {"enabled": true}` to OpenRouter when supported by the model.
- The project stores `reasoning_tokens` and whether `reasoning_details` were present.
- It does not store or display the full reasoning trace as a correctness claim.

Implementation notes from official OpenRouter docs:

- Chat completions endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Authentication: `Authorization: Bearer <OPENROUTER_API_KEY>`
- Optional app headers: `HTTP-Referer`, `X-Title` / `X-OpenRouter-Title`
- Request/response format is OpenAI-compatible chat completions.

Model policy for first live experiments, based on the user-provided pricing and the preference for open-model ecosystems:

| Role | Preferred model | Reason |
|---|---|---|
| Primary judge | `qwen/qwen3.6-plus` | Good cost/quality balance; large context; closer to open-model ecosystem than closed GPT/Gemini. |
| Cheap broad baseline judge | `deepseek/deepseek-v4-flash` | Very low cost; useful for judging larger batches and disagreement discovery. |
| High-confidence adjudicator subset | `openai/gpt-5.1` | More expensive; reserve for a small disputed sample if needed. |
| Alternative closed-model adjudicator | `google/gemini-3-flash-preview` | Use only for cross-provider disagreement checks, not as the primary open-model baseline. |

No live result should be reported until the generated `judgments.jsonl` and `judge_costs.json` come from a real API run.

Provider policy update: `deepseek/deepseek-v4-flash:free` artifacts are retained as historical pilot evidence only. The active DeepSeek baseline is paid `deepseek/deepseek-v4-flash`, because the free all-prediction run produced provider errors and left cases unjudged.

Current implemented CLI flags:

```text
--use-judge
--judge-provider mock|openrouter
--judge-model <name>
--judge-policy semantic|strict
--judge-sample-size N
--all-predictions
--case-ids VTD-001 VTD-002
--judge-reasoning / --no-judge-reasoning
```

Planned but not yet implemented: direct `openai` provider, direct `local` provider, batching, and cloud-result redaction switches beyond the current redacted SQL/question/hash payload.

Current cloud-judge redaction policy:

```text
redaction_applied: true
included: case/question/action/intent/category/difficulty/generated_sql/gold_sql/validity/execution flags/validation issues/result hashes
excluded: raw_database_rows, execution_result_preview, gold_result_preview, full_prompt, raw_model_response
raw_rows_sent: false
result_previews_sent: false
prompt_response_trace_sent: false
```

## 4. Artifact Schema

Each row in `judgments.jsonl` should include:

```json
{
  "case_id": "VTD-001",
  "judge_provider": "openai",
  "judge_model": "configured-model-name",
  "judge_prompt_version": "semantic_business_v1",
  "question": "...",
  "generated_sql": "SELECT ...",
  "gold_sql": "SELECT ...",
  "execution_correct": true,
  "semantic_business_score": 4,
  "semantic_business_correct": true,
  "reasoning_summary": "...",
  "metric_correct": true,
  "filter_correct": true,
  "join_logic_correct": true,
  "aggregation_correct": true,
  "answer_explanation_consistent": true,
  "redaction_applied": true,
  "input_tokens": 0,
  "output_tokens": 0,
  "estimated_cost_usd": 0.0
}
```

## 5. Static vs Judge-Based Tests

Static tests still matter and must remain offline:

- generated SQL parses
- generated SQL is SELECT-only
- referenced tables/columns exist
- result hash matches gold SQL
- expected action matches behavioral label

LLM-as-a-Judge handles semantic/business questions that static checks cannot reliably decide:

- wrong metric with same result on a small dataset
- correct execution but wrong clinical/business interpretation
- answer text contradicts generated SQL
- ambiguity that should have caused clarification

## 6. Paper Claims

By using this phase, we can report:
- **Human-Judge Correlation**: How well the local agent's self-critic matches a SOTA judge.
- **Logic vs. Execution Gap**: Percentage of queries that pass EX but fail Semantic Correctness.
- **Analyst Utility**: Qualitative analysis of why certain SQL patterns are hard for local models.
- **Judge Cost and Coverage**: How many cases were judged, how much it cost, and which cases still need human review.

## 7. Security & Privacy

> [!CAUTION]
> **NEVER** send raw database rows containing PII (Personally Identifiable Information) to cloud judges.
> Only send de-identified sample results or aggregated statistics.

Required privacy controls:

1. Default cloud judge mode sends schema, question, SQL and aggregate/hash preview only.
2. Raw row previews require explicit `--judge-redact-results false` and must still be blocked if PII fields are detected.
3. Every judgment row stores `redaction_applied`.
4. If privacy checks fail, benchmark must skip judge for that case and record `judge_skipped_reason`.

## 8. Definition of Done

Phase 16 is done when:

- `run_benchmark.py --use-judge --judge-provider mock` works in tests without network.
- Online judge provider is config-driven and optional.
- `judgments.jsonl`, `judge_reasoning.md`, `judge_costs.json` and `semantic_business_summary.csv` are produced.
- Reports show execution correctness and semantic/business correctness separately.
- Cases where EX passes but business correctness fails are explicitly listed.
- Privacy redaction status is recorded for every judged case.
- Multi-judge agreement is reported on both failure and success samples before any paper-level semantic accuracy claim.

## 9. Current Verified Scaffold

Implemented files:

- `src/evaluation/llm_judge.py`
- `scripts/judge_benchmark_artifact.py`
- `tests/tier1_unit/test_llm_judge.py`

Verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py tests\tier1_unit\test_artifact_analysis.py -vv --tb=short
7 passed

.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py -vv --tb=short
10 passed

.\.venv\Scripts\python.exe -m py_compile src\evaluation\llm_judge.py scripts\judge_benchmark_artifact.py
passed
```

First real artifact-backed mock judgment:

```text
source_artifact: results\benchmark\manual_a4_after_generation_token_cap
output_dir: results\judgments\20260519_phase16_mock_a4_token_cap
judgments: results\judgments\20260519_phase16_mock_a4_token_cap\judgments.jsonl
summary: results\judgments\20260519_phase16_mock_a4_token_cap\judge_summary.json
reasoning: results\judgments\20260519_phase16_mock_a4_token_cap\judge_reasoning.md
costs: results\judgments\20260519_phase16_mock_a4_token_cap\judge_costs.json
semantic_summary: results\judgments\20260519_phase16_mock_a4_token_cap\semantic_business_summary.csv
total_predictions: 8
total_judged: 5
verdict_counts: invalid_sql=3, requires_semantic_review=2
semantic_business_counts: incorrect=3, unjudged=2
mock_cost: input_tokens=0, output_tokens=0, estimated_cost_usd=0.0, cost_authoritative=false
authoritative: false
```

Interpretation:

- The scaffold proves the judgment artifact contract can be generated from real benchmark outputs.
- It does **not** claim semantic/business correctness for valid result mismatches.
- `VTD-141` and `VTD-300` remain `requires_semantic_review`.
- This is an anti-fake guard, not a replacement for a SOTA online/local judge or human review.

Integrated runner smoke:

```text
command: .\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset dev --sample 1 --bootstrap-iterations 20 --use-judge --judge-provider mock --no-judge-failures-only --ablation-id phase16_mock_integration_smoke_v2
artifact: results\benchmark\20260519_085308_gold_dev_qwen2-5-coder-7b_phase16_mock_integration_smoke_v2
benchmark: evaluated=1, failures=0, execution_accuracy=1.0, valid_sql_rate=1.0, reliability_score=1.0, unsafe_sql=0
judge_files: judgments.jsonl, judge_summary.json, judge_reasoning.md, judge_costs.json, semantic_business_summary.csv
judge_result: total_judged=1, exact_sql_match=1, semantic_correct=1, authoritative=false
artifact_locator_fix: final *_predictions.jsonl is preferred over *_partial_predictions.jsonl when both exist.
```

A0-A7 mock-judge sweep:

```text
source_manifest: results\ablation\20260517_phase11_a0_a7_execute\ablation_manifest.json
output_root: results\judgments\20260519_phase16_mock_a0_a7
jobs: 6
provider: mock
authoritative: false
summary:
  A0_direct_schema_only: judged=8, invalid_sql=5, requires_semantic_review=3
  A1_persian_nlu: judged=8, invalid_sql=5, requires_semantic_review=3
  A2_schema_linking: judged=8, invalid_sql=5, requires_semantic_review=3
  A3_value_linking: judged=8, invalid_sql=4, requires_semantic_review=4
  A4_cag_examples: judged=6, invalid_sql=4, requires_semantic_review=2
  A7_full_phase10_system: judged=6, invalid_sql=1, requires_semantic_review=5
```

OpenRouter no-key safety smoke:

```text
command: OPENROUTER_API_KEY unset; scripts\judge_benchmark_artifact.py results\benchmark\manual_a4_after_generation_token_cap --output-dir results\judgments\20260519_phase16_openrouter_no_key_a4_token_cap --judge-provider openrouter --judge-sample-size 2
result: provider=openrouter, model=qwen/qwen3.6-plus, total_judged=2, provider_not_configured=2, semantic_unjudged=2, authoritative=false
interpretation: OpenRouter provider wiring is present, but no network/live judgment is performed without an API key.
```

OpenRouter live pilot - Qwen:

```text
source_artifact: results\benchmark\manual_a4_after_generation_token_cap
output_dir: results\judgments\20260519_phase16_openrouter_qwen_a4_sample2_retry2
provider: openrouter
model: qwen/qwen3.6-plus
sample_size: 2
failures_only: true
authoritative: true
total_predictions: 8
total_judged: 2
verdict_counts: fail=1, incorrect=1
semantic_business_counts: incorrect=2
interpretation: both judged sampled failures are semantically/business incorrect. This is a small pilot, not a paper-grade semantic score.
```

OpenRouter live pilot - DeepSeek free:

```text
source_artifact: results\benchmark\manual_a4_after_generation_token_cap
output_dir: results\judgments\20260519_phase16_openrouter_deepseek_free_a4_sample2_no_reasoning
provider: openrouter
model: deepseek/deepseek-v4-flash:free
sample_size: 2
failures_only: true
judge_reasoning: false
authoritative: true
total_predictions: 8
total_judged: 2
verdict_counts: fail=2
semantic_business_counts: incorrect=2
reasoning_tokens: 0
reasoning_details_present: 0
interpretation: DeepSeek agreed with Qwen on the two sampled failures. Agreement on two cases is useful smoke evidence only.
```

OpenRouter live pilot - all A4 failures:

```text
source_artifact: results\benchmark\manual_a4_after_generation_token_cap
qwen_output_dir: results\judgments\20260519_phase16_openrouter_qwen_a4_failures_all
deepseek_output_dir: results\judgments\20260519_phase16_openrouter_deepseek_free_a4_failures_all
failures_only: true
total_predictions: 8
total_judged_each: 5
qwen_raw_verdict_counts: fail=3, incorrect=1, partial_match=1
qwen_raw_semantic_business_counts: incorrect=4, correct=1
deepseek_raw_verdict_counts: incorrect=2, invalid=1, disapproved=1, fail=1
deepseek_raw_semantic_business_counts: incorrect=4, unjudged=1
```

Interpretation:

- Both live judges agree that four sampled failures are semantically/business incorrect.
- `VTD-300` is not settled: Qwen marked it as partial/core-correct while DeepSeek marked it ambiguous. It must stay adjudication-required before any paper metric uses it as semantic-correct.
- These all-failure pilot artifacts were generated before canonical verdict hardening. Their raw rows are evidence, but canonical summaries should be regenerated before paper tables.

Provider robustness notes:

- Chunked HTTP failures such as `http.client.IncompleteRead` are retried and then recorded as `provider_error` if they persist.
- Empty or `None` provider content is recorded as `provider_parse_error` instead of crashing the run.
- `--judge-reasoning` sends OpenRouter `reasoning: {"enabled": true}` when requested, but artifacts store only token/presence metadata, not raw private reasoning.
- Free-form provider verdicts are canonicalized before summary metrics. In `phase16_sql_business_logic_v1`, partial labels defer to the provider's explicit semantic boolean: partial+true becomes `business_correct`, partial+false becomes `business_incorrect`, and partial+null remains `partial_business_match` with review required. Provider `invalid` labels are only reported as `invalid_sql` when the benchmark artifact itself says the SQL is invalid.

Canonical all-failure reruns and judge agreement:

```text
qwen_canonical: results\judgments\20260519_phase16_openrouter_qwen_a4_failures_all_canonical
qwen_counts: business_incorrect=4, partial_business_match=1; semantic incorrect=4, unjudged=1
deepseek_canonical: results\judgments\20260519_phase16_openrouter_deepseek_free_a4_failures_all_canonical
deepseek_counts: invalid_sql=3, business_incorrect=1, partial_business_match=1; semantic incorrect=4, unjudged=1
agreement_report: results\judgments\20260519_phase16_qwen_deepseek_a4_failure_agreement\judge_agreement.md
agreement_summary: common_cases=5, semantic_agreement=5, semantic_disagreement=0, verdict_agreement=2, verdict_disagreement=3
final_counts: agreed_incorrect=4, adjudication_required=1
tests: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_judge_agreement.py tests\tier1_unit\test_llm_judge.py -vv --tb=short -> 14 passed
```

Interpretation:

- Failure-only agreement is useful for error analysis, not for overall semantic accuracy.
- `VTD-300` remains `adjudication_required` because both judges now mark it as partial/unjudged after canonicalization.
- The next live review should include successful predictions as well; otherwise the judge layer can only characterize failures, not false-positive or over-rejection behavior.

All-prediction judge coverage:

```text
qwen_all_predictions: results\judgments\20260519_phase16_openrouter_qwen_a4_all_predictions
qwen_summary: total_judged=8, authoritative=8, semantic correct=3, incorrect=4, unjudged=1
deepseek_all_predictions: results\judgments\20260519_phase16_openrouter_deepseek_free_a4_all_predictions
deepseek_summary: total_judged=8, authoritative=6, provider_error=2, semantic correct=2, incorrect=1, unjudged=5
agreement_report: results\judgments\20260519_phase16_qwen_deepseek_a4_all_predictions_agreement\judge_agreement.md
agreement_summary: common_cases=8, semantic_agreement=4, semantic_disagreement=4, verdict_agreement=4, verdict_disagreement=4
final_counts: agreed_correct=2, agreed_incorrect=1, adjudication_required=5
```

Interpretation:

- `VTD-027` and `VTD-039` are confirmed success cases by both judges.
- `VTD-237` is agreed business-incorrect by both judges.
- In the historical DeepSeek-free all-prediction artifact, `VTD-078`, `VTD-141`, `VTD-300`, `VTD-343`, and `VTD-371` remained adjudication-required because of partial labels, provider errors, or Qwen/DeepSeek disagreement.
- That all-prediction artifact improved coverage, but the high adjudication count meant semantic accuracy could not be reported as a final model-quality metric.
- Next run policy: replace the DeepSeek free artifact with paid `deepseek/deepseek-v4-flash`, compare again against Qwen, then use `--case-ids` for any third-model adjudication so only unresolved cases are sent.

Paid DeepSeek replacement commands:

```powershell
$env:VTD_OPENROUTER_JUDGE_RETRIES = "3"

.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\manual_a4_after_generation_token_cap `
  --output-dir results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_all_predictions `
  --judge-provider openrouter `
  --judge-model deepseek/deepseek-v4-flash `
  --no-judge-reasoning `
  --all-predictions

.\.venv\Scripts\python.exe scripts\analyze_judge_agreement.py `
  results\judgments\20260519_phase16_openrouter_qwen_a4_all_predictions `
  results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_all_predictions `
  --output-dir results\judgments\20260520_phase16_qwen_deepseek_paid_a4_all_predictions_agreement
```

If the paid DeepSeek comparison still leaves unresolved cases, use the generated agreement report to choose only those case IDs for a third judge:

```powershell
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\manual_a4_after_generation_token_cap `
  --output-dir results\judgments\20260520_phase16_openrouter_gpt51_a4_unresolved_only `
  --judge-provider openrouter `
  --judge-model openai/gpt-5.1 `
  --no-judge-reasoning `
  --all-predictions `
  --case-ids VTD-078 VTD-141 VTD-300 VTD-343
```

After the third-judge artifact exists, build a conservative consensus report:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_judge_consensus.py `
  results\judgments\20260519_phase16_openrouter_qwen_a4_all_predictions `
  results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_all_predictions `
  results\judgments\20260520_phase16_openrouter_gpt51_a4_unresolved_only `
  --output-dir results\judgments\20260520_phase16_qwen_deepseek_paid_gpt51_a4_consensus
```

Consensus policy: a final correctness label requires at least two authoritative non-null semantic votes and no opposing authoritative semantic vote. Partial labels are reported as `consensus_partial_business_match` only when at least two authoritative partial votes exist and there are no non-null semantic votes. Provider errors, parse errors, and single-judge labels remain unresolved. Consensus summaries record `prompt_versions`, `same_prompt_version`, `judge_policies`, and `same_judge_policy`; mixed semantic/strict sets are evidence for review, not final metrics.

Paid DeepSeek replacement result:

```text
deepseek_paid_all_predictions: results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_all_predictions
deepseek_paid_summary: total_judged=8, authoritative=7, non_authoritative=1, provider_parse_error=1
deepseek_paid_semantic_counts: correct=3, incorrect=1, unjudged=4
paid_agreement_report: results\judgments\20260520_phase16_qwen_deepseek_paid_a4_all_predictions_agreement\judge_agreement.md
paid_agreement_summary: common_cases=8, semantic_agreement=5, semantic_disagreement=3, verdict_agreement=4, verdict_disagreement=4
paid_final_counts: agreed_correct=3, agreed_incorrect=1, adjudication_required=4
confirmed_correct: VTD-027, VTD-039, VTD-371
confirmed_incorrect: VTD-237
adjudication_required: VTD-078, VTD-141, VTD-300, VTD-343
```

Interpretation: paid DeepSeek improved the all-prediction agreement over the free artifact by confirming `VTD-371` as business-correct and reducing adjudication-required cases from `5/8` to `4/8`. It still produced one provider parse error and several partial/unjudged labels, so no final semantic accuracy claim should be made from this slice.

Consensus tooling verification:

```text
files: src/evaluation/judge_consensus.py, scripts/analyze_judge_consensus.py, tests/tier1_unit/test_judge_consensus.py
tests: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_judge_consensus.py tests\tier1_unit\test_judge_agreement.py tests\tier1_unit\test_llm_judge.py -vv --tb=short -> 17 passed
```

GPT-5.1 targeted adjudication and three-judge consensus:

```text
gpt51_unresolved_only: results\judgments\20260520_phase16_openrouter_gpt51_a4_unresolved_only
gpt51_summary: total_judged=4, authoritative=4, verdicts business_incorrect=2, invalid_sql=1, partial_business_match=1
gpt51_semantic_counts: incorrect=3, unjudged=1
consensus_report: results\judgments\20260520_phase16_qwen_deepseek_paid_gpt51_a4_consensus\judge_consensus.md
consensus_final_counts: consensus_correct=3, consensus_incorrect=4, consensus_partial_business_match=1
metric_policy_counts: semantic_correct=3, semantic_incorrect=4, partial_business_match=1, needs_human_review=0
consensus_correct: VTD-027, VTD-039, VTD-371
consensus_incorrect: VTD-078, VTD-141, VTD-237, VTD-343
consensus_partial_business_match: VTD-300
```

Interpretation: the three-judge consensus gives a defensible semantic correct/incorrect label for `7/8` A4 smoke cases under the older v0 strict policy and a separate partial-business-match label for `VTD-300`. Because the v1 policy now asks whether the SQL answers the user's actual question rather than whether it matches reference-only support columns, `VTD-300` should be rerun under `phase16_sql_business_logic_v1` before any final semantic claim is made. Do not edit or reinterpret the old v0 artifact.

Semantic v1 implementation update:

```text
prompt_version: phase16_sql_business_logic_v1
policy: judge against the user question, not exact gold shape
partial canonicalization: partial+semantic_true -> business_correct; partial+semantic_false -> business_incorrect; partial+semantic_null -> partial_business_match
dual policy: --judge-policy semantic and --judge-policy strict are supported and recorded in judge_policy
consensus traceability: prompt_versions, same_prompt_version, judge_policies and same_judge_policy are recorded
tests: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py tests\tier1_unit\test_judge_consensus.py tests\tier1_unit\test_judge_agreement.py -vv --tb=short -> 23 passed
compile: .\.venv\Scripts\python.exe -m py_compile src\evaluation\llm_judge.py src\evaluation\judge_consensus.py scripts\judge_benchmark_artifact.py scripts\analyze_judge_consensus.py -> passed
offline_contract_smoke: results\judgments\20260520_phase16_mock_v1_user_question_policy_smoke\judge_summary.json records prompt_version=phase16_sql_business_logic_v1, redaction_applied=true, total_judged=1; mock remains non-authoritative.
dual_policy_mock_smoke_semantic: results\judgments\20260520_phase16_mock_v1_semantic_vtd300_policy_smoke
dual_policy_mock_smoke_strict: results\judgments\20260520_phase16_mock_v1_strict_vtd300_policy_smoke
```

Recommended next live v1 rerun for the disputed rate case:

```powershell
$env:VTD_OPENROUTER_JUDGE_RETRIES = "3"

.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\manual_a4_after_generation_token_cap `
  --output-dir results\judgments\20260520_phase16_openrouter_qwen_a4_v1_semantic_vtd300 `
  --judge-provider openrouter `
  --judge-model qwen/qwen3.6-plus `
  --judge-policy semantic `
  --no-judge-reasoning `
  --all-predictions `
  --case-ids VTD-300

.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\manual_a4_after_generation_token_cap `
  --output-dir results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_v1_semantic_vtd300 `
  --judge-provider openrouter `
  --judge-model deepseek/deepseek-v4-flash `
  --judge-policy semantic `
  --no-judge-reasoning `
  --all-predictions `
  --case-ids VTD-300

.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\manual_a4_after_generation_token_cap `
  --output-dir results\judgments\20260520_phase16_openrouter_qwen_a4_v1_strict_vtd300 `
  --judge-provider openrouter `
  --judge-model qwen/qwen3.6-plus `
  --judge-policy strict `
  --no-judge-reasoning `
  --all-predictions `
  --case-ids VTD-300

.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  results\benchmark\manual_a4_after_generation_token_cap `
  --output-dir results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_v1_strict_vtd300 `
  --judge-provider openrouter `
  --judge-model deepseek/deepseek-v4-flash `
  --judge-policy strict `
  --no-judge-reasoning `
  --all-predictions `
  --case-ids VTD-300
```

If Qwen and paid DeepSeek disagree inside either policy, run GPT-5.1 only for `VTD-300` and only for the disputed policy.

Live v1 VTD-300 policy check:

```text
semantic_qwen: results\judgments\20260520_phase16_openrouter_qwen_a4_v1_semantic_vtd300
semantic_qwen_result: authoritative=true, verdict=business_correct, semantic_business_correct=true
semantic_deepseek_paid: results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_v1_semantic_vtd300
semantic_deepseek_paid_result: authoritative=true, verdict=business_correct, semantic_business_correct=true
semantic_agreement: results\judgments\20260520_phase16_qwen_deepseek_paid_a4_v1_semantic_vtd300_agreement
semantic_agreement_result: agreed_correct=1, semantic_agreement=1/1

strict_qwen: results\judgments\20260520_phase16_openrouter_qwen_a4_v1_strict_vtd300
strict_qwen_result: authoritative=true, verdict=business_incorrect, semantic_business_correct=false
strict_deepseek_paid: results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_v1_strict_vtd300
strict_deepseek_paid_result: authoritative=false, verdict=provider_parse_error, semantic_business_correct=null
strict_agreement: results\judgments\20260520_phase16_qwen_deepseek_paid_a4_v1_strict_vtd300_agreement
strict_agreement_result: adjudication_required=1
strict_gpt51: results\judgments\20260520_phase16_openrouter_gpt51_a4_v1_strict_vtd300
strict_gpt51_result: authoritative=true, verdict=business_incorrect, semantic_business_correct=false
strict_consensus: results\judgments\20260520_phase16_qwen_deepseek_paid_gpt51_a4_v1_strict_vtd300_consensus
strict_consensus_result: consensus_incorrect=1, same_prompt_version=true, same_judge_policy=true, incorrect_votes=2
```

Interpretation: `VTD-300` is now artifact-backed semantic-user-question correct under two live judges, and strict-reference incorrect under two authoritative strict votes (Qwen and GPT-5.1). For paper tables, report this as `semantic_user_question_correct=true` and `strict_reference_correct=false`. This is a useful qualitative example: the query answers the user's requested depression-rate question, but fails the stricter gold/reference output contract because reference support columns are missing.

Dual-policy report tooling:

```text
code: src\evaluation\dual_policy_report.py
cli: scripts\analyze_dual_policy_judgments.py
test: tests\tier1_unit\test_dual_policy_report.py
purpose: merge semantic-user-question and strict-reference agreement/consensus artifacts into one paper-facing table without calling a model or changing judgments.
verification: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_dual_policy_report.py tests\tier1_unit\test_judge_agreement.py tests\tier1_unit\test_judge_consensus.py -vv --tb=short -> 5 passed
broader_verification: dual-policy + agreement + consensus + llm_judge -> 24 passed
```

Current VTD-300 dual-policy report:

```text
artifact: results\judgments\20260520_phase16_a4_v1_vtd300_dual_policy_report
semantic_counts: correct=1
strict_counts: incorrect=1
combined_counts: semantic_correct_strict_incorrect=1
case: VTD-300 -> semantic correct, strict incorrect
```

Command pattern for future full-slice dual-policy reports:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_dual_policy_judgments.py `
  --semantic-dir results\judgments\<semantic_agreement_or_consensus_dir> `
  --strict-dir results\judgments\<strict_agreement_or_consensus_dir> `
  --output-dir results\judgments\<dual_policy_report_dir>
```

Full A4 v1 dual-policy report:

```text
semantic_agreement: results\judgments\20260520_phase16_qwen_deepseek_paid_a4_v1_semantic_all_agreement
semantic_result: common_cases=8, agreement=8/8, agreed_correct=4, agreed_incorrect=4
strict_agreement: results\judgments\20260520_phase16_qwen_deepseek_paid_a4_v1_strict_all_agreement
strict_result: common_cases=8, agreement=7/8, agreed_correct=3, agreed_incorrect=4, adjudication_required=1
strict_gpt51_vtd141: results\judgments\20260520_phase16_openrouter_gpt51_a4_v1_strict_vtd141
strict_gpt51_vtd141_result: authoritative=true, business_incorrect=1
strict_final_consensus: results\judgments\20260520_phase16_qwen_deepseek_paid_gpt51_a4_v1_strict_all_consensus
strict_final_result: consensus_correct=3, consensus_incorrect=5
dual_policy_final: results\judgments\20260520_phase16_a4_v1_all_dual_policy_final
dual_policy_final_counts: both_correct=3, both_incorrect=4, semantic_correct_strict_incorrect=1
both_correct: VTD-027, VTD-039, VTD-371
both_incorrect: VTD-078, VTD-141, VTD-237, VTD-343
semantic_correct_strict_incorrect: VTD-300
```

Interpretation: this is a completed 8-case A4 dual-policy evaluation slice. It is evidence for reporting evaluation gaps, not a license to tune prompts or validators to these IDs. Any future quality improvement must be general and validated on a fresh dev slice or larger run.

Redaction policy artifact:

```text
artifact: results\judgments\20260520_phase16_mock_redaction_policy_smoke\judge_summary.json
redaction_applied: true
raw_rows_sent: false
result_previews_sent: false
prompt_response_trace_sent: false
tests: .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py tests\tier1_unit\test_judge_consensus.py tests\tier1_unit\test_judge_agreement.py -vv --tb=short -> 18 passed
```
