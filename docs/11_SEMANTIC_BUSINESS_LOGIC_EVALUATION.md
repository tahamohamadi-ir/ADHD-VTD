# 11 - Semantic Business Logic Evaluation (LLM-as-a-Judge)

**Status:** Phase 16 in progress - deterministic mock provider, OpenRouter provider, standalone artifact judge, `run_benchmark.py --use-judge` integration, live Qwen/DeepSeek pilots, canonical all-failure reruns, and judge-agreement reporting are implemented; success-sample coverage, local judge, redaction policy, and larger review remain open  
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

## 2. Methodology

The judge is an independent high-reasoning model that acts as a senior clinical/data analyst. The current preferred path uses OpenRouter-hosted open-model-ecosystem judges first (`qwen/qwen3.6-plus`, `deepseek/deepseek-v4-flash`) and reserves more expensive closed models for small disagreement/adjudication subsets only.

### Input to the Judge
- **Original Persian Question**: Raw user intent.
- **Normalized Context**: The system's understanding of the question.
- **Linked Schema**: Tables and columns used.
- **Generated SQL**: The candidate produced by the local agent.
- **Gold SQL**: The ground-truth reference.
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

Required CLI flags:

```text
--use-judge
--judge-provider openai|local|mock
--judge-model <name>
--judge-sample-size N
--judge-failures-only
--judge-redact-results
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
- Free-form provider verdicts are canonicalized before summary metrics. `partial_match` becomes `partial_business_match` with `semantic_business_correct=null` and human review required; provider `invalid` labels are only reported as `invalid_sql` when the benchmark artifact itself says the SQL is invalid.

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
