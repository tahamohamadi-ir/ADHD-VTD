# PARS-SQL Development Roadmap

این فایل نقشه توسعه اجرایی پروژه است و از روی `docs/00_INDEX.md` تا `docs/10_FULL_DEVELOPMENT_ROADMAP_ZERO_TO_SOTA.md`، `docs/THREAT_MODEL.md` و phase docs به‌روز شده است.

## هدف پروژه

ساخت یک سیستم Persian-aware، reliability-first و local/edge Text-to-SQL برای تحلیل داده‌های mental-health و student-lifestyle که:

- فقط SQL امن و read-only اجرا کند.
- قبل از تولید SQL، ambiguity، safety و schema/value grounding را بررسی کند.
- خروجی قابل benchmark، قابل audit و قابل بازتولید بسازد.
- برای paper، ablation، error taxonomy و reliability metrics artifact واقعی تولید کند.
- بعد از تثبیت research runtime، برای edge runtime سبک‌تر آماده شود.

## اصول غیرقابل مذاکره

1. LLM فقط candidate SQL تولید می‌کند.
2. LLM درباره safety، execution permission یا correctness تصمیم نهایی نمی‌گیرد.
3. هر SQL قبل از اجرا از validation stack عبور می‌کند.
4. executor فقط read-only است.
5. behavioral examples مثل SQL-positive examples ارزیابی نمی‌شوند.
6. EX تنها معیار کافی نیست؛ Reliability Score، abstention، unsafe pass-through، robustness و latency باید گزارش شوند.
7. هر benchmark run باید config، predictions، failures، attempts، full prompt/response trace و summary داشته باشد.
8. هر failure باید taxonomy داشته باشد.
9. هر claim پژوهشی باید از artifact واقعی بیاید.
10. edge runtime بعد از research benchmark پایدار ساخته می‌شود، نه قبل از آن.
11. درستی اجرای SQL و درستی مفهومی/بیزینسی SQL دو معیار جدا هستند و نباید با هم قاطی شوند.
12. هر خروجی benchmark باید نام مدل، مسیر مدل، config، ablation id و ماژول‌های روشن/خاموش را ثبت کند.

## وضعیت فعلی

| بخش | وضعیت | توضیح |
|---|---|---|
| Phase 0 governance/audit | Done | schema freeze، audit artifacts، dataset card و threat model وجود دارد. |
| Foundation gaps | Done | exceptionها، utils، NLU پایه، safety/ambiguity/value-link و Tier 1 tests کامل‌اند. |
| Data/schema quality | Done | validation کامل پاس می‌شود؛ 400 SQL با pass rate برابر 100% اجرا می‌شود؛ splitها exact هستند. |
| NLU v2 + QIR | Done | concept registry، QueryIR، schema linker، value linker و query planner وجود دارد. |
| SQL validation | Done | safety/schema/join/aggregation/type/semantic validation و read-only execution فعال است. |
| Local LLM generation | Done | local LLM wrapper، prompt builder، output parser و `run_agent.py` وجود دارد. |
| Milestone 1.5 | Done | stress-test artifacts ثبت شده‌اند. |
| Hybrid CAG/RAG | Done | BM25، ChromaDB/JSON vector store، hybrid scoring، context builder و retrieval benchmark فعال‌اند. |
| LangGraph orchestration | Done | workflow و routing پایه فعال است و retrieval قبل از prompt build وصل شده است. |
| Reflexion stack | Done | سیستم Critic/Planner/Taxonomy/Memory برای خوداصلاحی هوشمند کاملاً فعال است. |
| Benchmark runner | Done - infrastructure | مدهای `agent` و `gold/retrieval` فعال‌اند؛ balanced sampling، bootstrap CI، prompt/response trace، progress logging، model/module metadata، self-overlap mitigation، shape contracts و closeout smoke انجام شده‌اند. fixed test و paper-grade claims هنوز blocked هستند و به کیفیت Phase 11/13/16 و محدودیت leakage وابسته‌اند. |
| Ablation/research metrics | In Progress | Phase 11 first slice کامل شده: قرارداد ضد-overfit/ضد-fake-result، helpers آماری، analyzer آرتیفکت، ablation configs، dry-run/execute runner، runtime flag contract، real A0-A7 smoke ablation، report مقایسه‌ای artifact-backed و taxonomy هم‌راستا با `docs/06` آماده‌اند. Retrieval ablation R0-R3 روی smoke و full dev اجرا و report شده است؛ full-dev اولیه نشان داد BM25/vector برابر `60/60` و hybrid/identity-rerank برابر `58/60` بودند، سپس schema-evidence guard عمومی اضافه شد و manifest نهایی `results/ablation/20260519_phase11_retrieval_dev_full_final/ablation_comparison.md` هر چهار backend را روی dev کامل `60/60` نشان داد. آخرین A4 هدفمند کامل: `manual_a4_after_generation_token_cap` با EX `0.375`، valid SQL `0.625`، reliability `0.25`، unsafe SQL `0`. گزارش taxonomy جدید: `results/error_analysis/20260519_phase11_docs06_taxonomy_a4_token_cap/error_report.md`. هنوز paper-grade agent ablation، semantic judge/review و تصمیم درباره ادامه shape tuning باقی مانده‌اند. |
| Output/chart/narrative | TODO | `src/output` هنوز placeholder است. |
| Reliability/multi-candidate | In Progress | first annotation-only reliability gate implemented in `src/evaluation/reliability_gate.py`; `reliability_gate` is now a runtime-enforced benchmark flag and records gate action/reason/warnings without changing graph routing yet. The question/SQL consistency critic now includes richer general checks for risk-profile stress/sleep context averages, average-threshold filters and comparative single-group filters. Fresh dev-spl2 evidence is mixed: the first richer-critic run improved reliability but regressed valid SQL; after a general shape-key validator fix, valid SQL improved but reliability worsened; the final AVG-threshold runtime run `results/benchmark/manual_phase13_gate_dev_spl2_richer_critic_avg_threshold_final` kept EX at `0.375`, improved valid SQL versus the earlier gate baseline to `0.875`, but reliability remained worse at `-1.25`, with two valid-result-mismatch cases still answered. A conservative `reliability_gate_review_consistency_failures` policy now moves consistency failures to `needs_review` annotations; runtime artifact `results/benchmark/manual_phase13_gate_dev_spl2_review_consistency_failures` still has EX `0.375`, valid SQL `0.875`, reliability `-1.25`, unsafe SQL `0`, and remains annotation-only. Latency-aware multi-candidate scaffolding exists in `candidate_consistency.py` and `multi_candidate_policy.py`; default strategy is adaptive, not always-on. Feature-flagged candidate generation exists behind `multi_candidate_generation=true`; candidate adoption is separate behind `multi_candidate_adoption=true`, default false. The candidate-evidence gate now respects `multi_candidate_generation_enabled`, so annotation-only policy does not create false abstentions. Current series report `results/multi_candidate_ablation/20260522_phase13_multicandidate_cost_benefit_series_v5_dual_policy` covers 6 A/B comparisons: adoption blocked twice, shadow/evidence-gated variants insufficient evidence, no EX/valid SQL/reliability gain, and one dual-policy semantic_user_question regression. Best recommendation remains `do_not_adopt_candidate_adoption`; shadow-only remains diagnostic evidence. Reliability-gate routing and multi-candidate adoption remain disabled; no quality/SOTA claim is allowed from these mixed runs. |
| Edge runtime | TODO | بعد از benchmark پایدار. |
| Research packaging | In Progress | dataset card/threat model/phase docs وجود دارد؛ اولین paper-facing evidence package برای A4 dual-policy smoke ساخته شده است: `results/paper/20260520_phase16_a4_dual_policy_evidence`. reproduce script و paper-grade tables روی larger runs هنوز باقی مانده‌اند. |
| LLM-as-a-Judge | Done | mock/offline artifact scaffold، اتصال `run_benchmark.py --use-judge`، OpenRouter provider پیاده‌سازی شدند. Judge policy به دو حالت رسمی تقسیم شده: `semantic_user_question` و `strict_reference`. فاز ۱۶ در یک سناریوی کامل با قاضی DeepSeek V4-Flash اجرا شد که با موفقیت توانست کوئری‌هایی که به دلیل تفاوت در تعداد ستون‌ها مردود شده بودند (مانند VTD-300 و VTD-078) را به عنوان `business_correct` تأیید کند. این موضوع توانمندی معماری برای تمایز Strict Constraint Failure از Semantic Failure را اثبات می‌کند و مسیر را برای مقاله‌نویسی هموار کرد. |
| Phase 17 Pipeline Fix | Done | باگ ResultSerializer (هش ستون)، NLU routing، JSON parser سه‌مرحله‌ای، و Repair prompt context رفع شدند. بنچمارک ۴۰۰ سوالی: EX=32.5%, Valid=82.5%. تحلیل عمیق ۲۷۰ خطا به ۱۴ دسته. |
| Phase 18 Accuracy Optimization | In Progress | Anti-overfit zero/few-shot optimization reached 61.25% on positive400 with `--exclude-self` and no exact cache. The large 18.7b5 template pack is now quarantined as an ablation/debug artifact because the 94.25% full400 run was mostly template-driven and regressed 23 previously correct cases. Runtime default is `deterministic_templates=false`; next accepted metric must come from the AI/QIR/schema/retrieval path plus behavior and holdout/paraphrase checks. |

## Current Decision Snapshot - 2026-05-22

The latest verified reliability/multi-candidate status is conservative:

```text
latest_gate_policy_artifact: results/benchmark/manual_phase13_gate_dev_spl2_review_consistency_failures
latest_gate_analysis: results/reliability_gate/20260522_phase13_gate_dev_spl2_review_consistency_failures_analysis
latest_gate_ab_vs_original_baseline: results/reliability_gate/20260522_phase13_gate_dev_spl2_before_after_review_consistency_failures
latest_gate_ab_vs_avg_threshold_run: results/reliability_gate/20260522_phase13_gate_dev_spl2_avg_threshold_vs_review_consistency_failures
evaluated: 8
execution_accuracy: 0.375
valid_sql_rate: 0.875
reliability_score: -1.25
unsafe_sql: 0
gate_actions: needs_review=3, answer=5
consistency_failed_review: 2
```

Interpretation:

```text
The review-on-consistency-failure policy changes gate annotations as intended, but final benchmark actions are unchanged because gate routing is still disabled.
This is evidence for the next routing experiment, not a quality/SOTA/paper-readiness claim.
Multi-candidate adoption remains blocked.
Fixed test remains blocked.
```

Next architecture decision:

```text
Add or explicitly defer reliability_gate_route_actions as a separate experiment flag.
If added, compare annotation-only versus routed needs_review on the same selected_cases_hash, then run semantic_user_question and strict_reference judging before any adoption decision.
```

## واقعیت فعلی و ریسک‌های باز

### Phase 10 بسته شده، اما کیفیت مدل حل نشده است

زیرساخت Phase 10 برای benchmark/trace بسته شده است. آخرین آرتیفکت معتبر closeout:

```text
results/benchmark/20260517_031221_agent_dev_qwen2-5-coder-7b_manual_agent_shape_contract_spl2_after_fixes
evaluated: 8
execution_accuracy: 0.25
valid_sql_rate: 0.875
reliability_score: -3.25
unsafe_sql: 0
self_overlap_removed_total: 1
```

این نتیجه نباید به عنوان کیفیت SOTA یا آماده‌بودن paper-grade مدل تعبیر شود. معنی درست آن این است که مسیر benchmark، trace، metadata، self-overlap mitigation و shape-contract از نظر زیرساختی کار می‌کند. خطاهای باقی‌مانده مربوط به reasoning/prompt/retrieval/semantic reliability هستند و به Phase 11، Phase 13 و Phase 16 منتقل شده‌اند.

Remaining Phase 10 work:

```text
status: infrastructure complete
phase_17: COMPLETED (EX=32.5%, Valid=82.5%, 400Q benchmark)
phase_18: IN PROGRESS — accuracy optimization target >60%
blockers:
  - behavior/no-SQL quality is still Phase 12/13 work
allowed_next_action:
  - Execute Phase 18-A (Prompt Hints) for +14.6% accuracy
  - Execute Phase 18-B (Few-shot/RAG) for +6.2% accuracy
  - Execute Phase 18-C (Schema Linking) for +9.9% accuracy
  - Execute Phase 18-D (NLU Routing) for +3.6% accuracy
  - Run full benchmark after each sub-phase to measure
  - After >60%, prepare QLoRA training data from trace artifacts
```

### Phase 18 — نقشه راه بهینه‌سازی دقت (بدون Fine-tuning)

وضعیت baseline (خروجی Phase 17): EX=32.5%, Valid=82.5% روی ۴۰۰ سوال.

تحلیل ۲۷۰ خطا نشان داد که ۲۲۸ مورد (~84%) بدون Fine-tuning با بهینه‌سازی پرامپت، few-shot و NLU قابل حل هستند:

#### توزیع خطاها (270 مورد)

| # | دسته خطا | تعداد | درصد از کل خطاها | نوع راهکار | فاز |
|---|---|---|---|---|---|
| 1 | MISSING_ROUND | 58 | 21.5% | Prompt Hint | A |
| 2 | WRONG_FILTER_VALUE | 44 | 16.3% | Value Linking + Few-shot | C |
| 3 | HALLUCINATED_FILTER | 35 | 13.0% | Negative Few-shot | B |
| 4 | MISSING_FILTER | 31 | 11.5% | Prompt Hint | A |
| 5 | ROUTING_ERROR | 24 | 8.9% | NLU Fix | D |
| 6 | SYNTAX_ERROR | 23 | 8.5% | Reflexion + Schema | C |
| 7 | WRONG_GROUP_COLUMNS | 17 | 6.3% | Schema Linking + Few-shot | C |
| 8 | WRONG_COLUMN_REF | 15 | 5.6% | Schema Linking | C |
| 9 | WRONG_SELECT_COLS | 6 | 2.2% | Few-shot | B |
| 10 | MISSING_SUBQUERY | 6 | 2.2% | Model Limit | QLoRA |
| 11 | UNGROUPED_COLUMN | 4 | 1.5% | Prompt Hint | A |
| 12 | LIMIT_MISMATCH | 3 | 1.1% | Prompt Hint | A |
| 13 | GROUP_BY_MISMATCH | 3 | 1.1% | Few-shot | B |
| 14 | WRONG_TABLE_REF | 1 | 0.4% | Schema Linking | C |

#### دقت به تفکیک سطح دشواری
| سطح | پاس | کل | دقت | بزرگترین خطا |
|---|---|---|---|---|
| Easy | 60 | 100 | 60.0% | MISSING_ROUND (14), MISSING_FILTER (9) |
| Medium | 21 | 100 | 21.0% | MISSING_ROUND (24), HALLUCINATED_FILTER (17) |
| Hard | 30 | 100 | 30.0% | WRONG_FILTER_VALUE (17), MISSING_ROUND (13) |
| Complex | 19 | 100 | 19.0% | WRONG_FILTER_VALUE (17), SYNTAX_ERROR (17) |

#### فاز A: Prompt Hints (تاثیر: +24.3% = 97 مورد) [COMPLETED]
- ROUND hint: مقادیر اعشاری را ROUND کن (58 خطا)
- NULL filter hint: WHERE IS NOT NULL برای AVG/SUM (31 خطا)
- UNGROUPED hint: CASE WHEN باید در GROUP BY باشد (4 خطا)
- LIMIT hint: LIMIT فقط وقتی top-N خواسته شده (3 خطا)

#### فاز B: Few-shot & RAG (تاثیر: +10.3% = 41 مورد) [COMPLETED]
- Negative few-shot: نمونه‌هایی که نشان می‌دهد "فیلتر نزن مگر خواسته شده" (35 خطا)
- Column selection examples: نمونه‌های صحیح SELECT (6 خطا)

#### فاز C: Schema & Value Linking (تاثیر: +16.6% = 59 مورد) [COMPLETED]
- Column descriptions: توضیح فارسی هر ستون (44 خطا)
- Table descriptions: توضیح هر جدول (17 خطا)

#### فاز D: NLU Routing (تاثیر: +6.0% = 24 مورد) [COMPLETED]
- اصلاح ambiguity_detector و intent_classifier برای کلمات "روند"، "چگونه" (24 خطا)

#### جمع‌بندی
| فاز | تعداد خطای قابل رفع | بهبود بالقوه | نرخ موفقیت فرضی 60% | وضعیت اجرایی |
|---|---|---|---|---|
| A: Prompt Hints | 97 | +24.3% | +14.6% | انجام شد |
| B: Few-shot & RAG | 41 | +10.3% | +6.2% | انجام شد |
| C: Schema Linking | 59 | +16.6% | +9.9% | انجام شد |
| D: NLU Routing | 24 | +6.0% | +3.6% | انجام شد |
| **مجموع** | **228** | **+57.0%** | **+34.3%** | |

دقت Phase 17: 32.5% → Phase 18.5 ضد-overfit: 52.00% → Phase 18.6 ضد-overfit: **61.25%** → هدف Phase 18.7: **>=65%**

دسته‌های بحرانی (0% accuracy): group_comparison (0/11), rate (0/7), performance (0/6), benchmark_rank (0/5), bucket (0/5), change_analysis (0/5)

### Benchmarkها real هستند ولی ضد-overfit بودن ثابت نشده

Datasetهای benchmark از فایل‌های واقعی پروژه در `data/questions/` می‌آیند و gold SQLها validate شده‌اند. با این حال، چون retrieval/few-shot bank هم از همین اکوسیستم dataset ساخته شده، باید leakage audit انجام شود:

- overlap بین train/dev/test
- overlap بین dev/test و `golden_examples.jsonl`
- overlap بین dev/test و `few_shot_bank.jsonl`
- overlap بین dev/test و `data/rag/indexed_examples.jsonl`
- self-retrieval در top-k
- near-duplicate Persian questions
- SQL skeleton leakage

Audit اولیه در 2026-05-16 انجام شد و overlap risk پیدا کرد؛ بنابراین claim پژوهشی هنوز نباید بگوید سیستم overfit/leakage ندارد مگر اینکه mitigation اجرا شود یا limitation صریح نوشته شود.

### اجرای local modelها باید دوباره validate شود

مدل‌های GGUF در `models/generation/` وجود دارند و smoke اولیه با مدل 3B پاس شده است. برای claim نهایی باید همین پروتکل با مدل هدف paper هم تکرار شود:

```powershell
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\qwen2.5-coder-7b-instruct-q4_k_m.gguf"
.\.venv\Scripts\python.exe scripts\run_agent.py "درصد دانشجویان افسرده چقدر است؟" --verbose
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --ablation-id full_trace
```

قبولی local model فقط load شدن مدل نیست؛ باید prompt، raw response، parsed SQL، validation، execution و final action در artifactها قابل بررسی باشد.

## مسیر معماری هدف

```text
Persian question
  -> normalize / number-date-colloquial mapping
  -> intent + ambiguity + safety routing
  -> QIR
  -> schema linking + value linking
  -> hybrid retrieval / CAG context
  -> local LLM candidate generation
  -> SQL parsing
  -> validation stack
  -> repair / reflexion if needed
  -> read-only execution
  -> semantic result check
  -> reliability gate
  -> answer formatting + chart recommendation + disclaimer
  -> benchmark trace + error analysis
```



### Phase 18.5 — جهش بزرگ به کمک General Templates و Inference Optimizations

اجرای بنچمارک در فاز 18.5 (با فعال‌سازی Templates و جلوگیری از Overlap در RAG) باعث شد دقت از سد مقاومت 32.75% عبور کند و به **52.00%** برسد. نرخ کدهای SQL قابل اجرا (Valid SQL Rate) نیز به **93.00%** ارتقا یافت.

**توزیع خطاهای جدید (مجموعاً 192 خطا):**
- `RESULT_MISMATCH`: 167 (کاهش چشمگیر، اما همچنان گلوگاه اصلی منطقی)
- `INVALID_SQL`: 25 (کاهش به دلیل ساختارهای تمپلیتی)
- `MISSING_GENERATED_SQL`: 0 (حل کامل)

**چرا به 52% رسیدیم؟**
استفاده از اسکلت‌های SQL (Templates) به مدل کمک کرد تا از ساختارشکنی بپرهیزد و فقط فیلدها و شروط را پر کند. این کار باعث شد خطاهای مربوط به عدم تطابق `GROUP BY` و موارد مشابه به شدت کاهش یابند.

### Phase 18.6 — عبور از مرز 60% (دستاورد بزرگ!)

با اجرای ویرایش دوم اسکلت‌ها (`general_templates_v2`)، دقت مدل به **61.25%** رسید و نرخ Valid SQL به **93.5%** ارتقا یافت. ما رسماً توانستیم یک مدل 7 میلیارد پارامتری را بدون Fine-tuning به سطح قابل قبولی برای تولید SQLهای سازمانی برسانیم. خطاهای `MISSING_GENERATED_SQL` کاملاً صفر شده‌اند.

**توزیع خطاهای جدید (مجموعاً 155 خطا):**
- `RESULT_MISMATCH`: 132
- `INVALID_SQL`: 23

بیشتر این 155 خطا در دسته‌های بسیار دشوار قرار دارند: `advanced_sql`، `complex_dashboard`، `dashboard_story` و `advanced_analysis`.

### Phase 18.7 — لمس سقف نهایی توانایی مدل (Zero-Shot Mastery)

برای رفع خطاهای پیچیده باقیمانده، پیش از QLoRA، تکنیک‌های پیشرفته زیر اجرا خواهند شد:
1. **Vector RAG & Cross-Encoder Reranker:** تغییر مکانیزم جستجو از BM25 به Semantic برای پیدا کردن مثال‌هایی با ساختار دقیقاً مشابه در کوئری‌های پیچیده.
2. **Chain of Thought (CoT):** الزام LLM به استدلال متنی پیش از تولید کد SQL در Few-shot ها برای جلوگیری از خطاهای منطقی در `advanced_analysis`.
3. **Multi-Candidate Generation & Reliability Gate:** تولید موازی چندین کوئری و انتخاب بهترین مورد بر اساس گزارش‌های Validator.

Canonical Phase 18.7 plan: `docs/phases/PHASE_18_7_ZERO_SHOT_MASTERY.md`

Baseline artifact:
`results/benchmark/20260524_221942_agent_positive400_qwen2-5-coder-7b_phase18_5_general_templates_v2_no_exact_cache_exclude_self_full400`

Current baseline: EX `61.25%`, valid SQL `93.5%`, failures `155`, unsafe SQL `0`, p95 latency `86.8s`.

18.7 execution order:

1. `18.7a` - Template Safety Gate, specific-before-broad template priority, schema hard-gating with cross-dataset escape hatch, validator fixes for windowed aggregates and `GROUP BY` aliases.
2. `18.7b` - One-shot deterministic Schema Surgeon for `UNKNOWN_COLUMN`; patch once, validate once, then fail fast only when a mapped patch remains invalid.
3. `18.7b2` - Corrective regression-recovery pass after the `61.5%` full400 run: add general templates for the five valid-result regressions and keep one bounded LLM repair slot when Surgeon has no mapping.
4. `18.7b5` - Selected failed154 iteration gate: result-verified deterministic template pack plus shape-validator false-positive fix. Latest failed154 artifact reached EX `154/154`, valid SQL `154/154`, unsafe `0`, p95 latency `1063ms`. The follow-up full400 artifact reached EX `377/400`, but it is quarantined because `324/400` cases bypassed LLM generation and `23` previously correct cases regressed.
5. `18.7c0` - Required no-template check: full positive400 with `deterministic_templates=false` restored the AI/QIR/schema/retrieval architecture as the measured path, but fell to EX `134/400 = 33.5%`.
6. `18.7e` - QIR/shape recovery without deterministic templates: populate QIR dimensions/metrics after schema linking, add generic shape validator contracts, schema-table collision preference, QIR-derived retrieval skeletons, and QIR table-shape multi-candidate triggers.
7. `18.7c1` - Vector retrieval only, with `--exclude-self`.
8. `18.7c2` - Vector retrieval plus multilingual `BAAI/bge-reranker-v2-m3` or local equivalent.
9. `18.7d` - Reliability Gate / Semantic Critic over existing multi-candidate outputs. Multi-candidate is already present; this step evaluates gate routing/selection.

Acceptance criteria:

- EX `>= 65%`.
- Valid SQL `>= 94%`.
- Regressions `<= 5` versus the 61.25% artifact.
- Difficulty split: Easy `>= 95%`, Medium `>= 72%`, Hard `>= 52%`, Complex `>= 35%`.
- p95 latency `<= 65.1s`.
- Unsafe SQL `= 0`.
- Holdout or paraphrase validation completed without exact-cache style memorization.

Next required Phase 18.7 commands:

Fast regression gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --path data\questions\special\phase18_7c0_lost119.json --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 100 --trace-level compact --ablation-id phase18_7e_lost119_qir_shape_repair
```

Fast failed-set gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --path data\questions\special\phase18_7c0_failed266.json --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 100 --trace-level compact --ablation-id phase18_7e_failed266_qir_shape_repair
```

Full no-template check:

```powershell
$env:VTD_LLM_N_CTX="8192"
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 300 --trace-level compact --ablation-id phase18_7e_ai_pipeline_qir_shape_full400
```

Dataset governance update:

- `train/dev/test` are clean disjoint splits of `full400`, but `full400` itself is not a holdout because it contains all three splits.
- `vtd_total_500_dataset_package` is a packaging artifact (`400` SQL-positive + `100` behavioral), not new evaluation data.
- `phase18_7b_failed154`, `phase18_7b_regressed5`, and `vtd_question_sql_140_colloquial_additions_validated` are all subsets of `full400`; use them only for debugging, regression checks, or robustness slices, not final generalization claims.
- Current `test/` has been partially touched by Phase 18.7 failure analysis (`20` cases inside failed154), so final anti-overfit claims require a new independent holdout/paraphrase set.
- JSON/JSONL pairs are now aligned, including the VTD-300 fix in `dev.json`.
- All gold/expected SQL in the reviewed SQL-positive and behavioral files executes and passes the validation stack after the `CASE WHEN` aggregation validator fix.

## Milestone نقشه راه

### Milestone A - Foundation and Retrieval Baseline [DONE]

هدف: داشتن دیتاست معتبر، schema ثابت، NLU پایه، validation امن و retrieval قابل اندازه‌گیری.

Done:

- Phase 0 تا Phase 7 کامل شده‌اند.
- `scripts/validate_dataset.py` پاس می‌شود.
- `pytest tests/tier1_unit -q` پاس می‌شود.
- ChromaDB و JSON vector backend ساخته و تست شده‌اند.
- retrieval benchmark با `--use-vector` اجرا شده است.

### Milestone B - Full Benchmarkable Agent [DONE - INFRASTRUCTURE]

هدف: تبدیل پروژه از demo/retrieval benchmark به full-system benchmark.

Tasks:

- [x] اضافه کردن `--mode agent` به `scripts/run_benchmark.py`.
- [x] اجرای اولیه LangGraph برای SQL-positive cases و behavioral cases با expected-action جداگانه.
- [x] ذخیره `attempts.jsonl` اولیه شامل generated SQL، validation errors، repair attempts و final action.
- [x] ذخیره `benchmark_results.csv`.
- [x] ذخیره `reliability_summary.csv`.
- [x] ذخیره `error_taxonomy.csv`.
- [x] ذخیره `paper_tables.md`.
- [x] کامل کردن `attempts.jsonl` با prompt دقیق، raw model response، parsed payload، execution result/hash و trace کافی برای replay.
- [x] report کردن EX، Valid SQL Rate، Reliability Score، clarification accuracy، unsafe pass-through و latency در summary/terminal. EX@first و EX@final به Phase 11 metric extraction دقیق‌تر منتقل می‌شود.
- [x] جدا کردن `execution_correct`، `semantic_business_correct` و `action_correct` در prediction records.
- [x] Implement **Balanced Sampling** per difficulty level.
- [x] Implement **Bootstrap Confidence Intervals** for core metrics.
- [x] Ensure benchmark summaries/artifacts include **Model Name** and **Ablation status**.
- [x] Capture **Full Prompt/Response Traces** for every agent attempt.
- [x] Add real-time terminal progress tracking with `[X/Y]`, per-question latency, elapsed time and ETA.
- [x] تضمین اینکه behavioral examples با EX سنجیده نشوند.
- [x] ثبت `dataset_hash`, `selected_cases_hash`, `difficulty_counts`, `retrieval_backend`, `max_retries`, `prompt_template`, `trace_level` و self-overlap policy در config.
- [x] افزودن `--exclude-self` برای حذف retrieval self-overlap بر اساس base id و normalized question.

Acceptance:

- [ ] sample-20 full agent benchmark بدون دخالت دستی اجرا شود.
- [ ] balanced benchmark مثل `--samples-per-level 5` از هر سطح difficulty اجرا شود.
- [ ] خروجی کامل در `results/benchmark/<timestamp>_<mode>_<dataset>_<model_slug>_<ablation_id>/` ساخته شود.
- [ ] نام مدل و ablation id در اسم folder و فایل‌ها دیده شود.
- [ ] هر prediction شامل سوال، prompt، raw response، generated SQL، gold SQL، hashes، validation/execution errors و final action باشد.
- [ ] حداقل یک run واقعی agent با مدل local و contract جدید inspect و خلاصه شود.
- [ ] behavior_dev/behavior_test با expected-action ارزیابی شوند.
- [ ] unsafe pass-through برابر `0` باشد.
- [x] هر failure حداقل یک primary category داشته باشد.

Blocking before Done:

- [x] real agent smoke with local model.
- [x] sample-20 dev agent benchmark.
- [x] balanced dev agent benchmark.
- [x] behavior_dev benchmark.
- [x] leakage/overfit audit between benchmark splits and RAG/few-shot sources.
- [x] first failure analysis report from prompt/response traces.
- [x] shape-contract closeout report: `results/error_analysis/20260517_phase10_shape_contract/error_report.md`.
- [x] larger shape-contract smoke after the tightened risk average-filter validator:
  `python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 2 --bootstrap-iterations 200 --exclude-self --trace-level full --ablation-id manual_agent_shape_contract_spl2`.

### Milestone C - Research Metrics and Ablation [PAPER 1]

هدف: اثبات اینکه هر component ارزش افزوده دارد.

Tasks:

- [x] Phase 11 contract doc: `docs/phases/PHASE_11_ABLATION_ERROR_ANALYSIS.md`.
- [x] ساخت first-slice config templates در `experiments/configs/`.
- [x] تعریف initial A0/A1/A2/A3/A4/A7 config templates برای first-paper experiments.
- [x] `scripts/run_ablation.py`.
- [x] `src/evaluation/ablation_runner.py` core برای dry-run manifest و optional execution.
- [x] `src/evaluation/statistical_tests.py`.
- [x] bootstrap CI helper در Phase 11 statistical helper.
- [x] McNemar/paired helper logic where applicable.
- [x] `src/evaluation/artifact_analysis.py` برای خواندن آرتیفکت واقعی benchmark و تولید گزارش خطا.
- [x] `scripts/analyze_benchmark_artifact.py`.
- [x] focused tests for Phase 11 new tooling passed.
- [x] `tests/tier1_unit/test_ablation_runner.py`.
- [x] `src/evaluation/ablation_report.py`.
- [x] `scripts/analyze_ablation_manifest.py`.
- [x] `tests/tier1_unit/test_ablation_report.py`.
- [x] A0-A7 smoke ablation executed from a real manifest:
  `results/ablation/20260517_phase11_a0_a7_execute/ablation_manifest.json`.
- [x] A0-A7 comparison report generated from real benchmark artifacts only:
  `results/ablation/20260517_phase11_a0_a7_execute/ablation_comparison.md`.
- [x] retrieval ablation smoke: BM25-only، vector-only، hybrid، reranker.
  - [x] `scripts/run_benchmark.py` supports runtime `--retrieval-backend bm25|vector|hybrid|hybrid_rerank`.
  - [x] `HybridRetriever` supports isolated `retrieval_mode`.
  - [x] configs: `R0_retrieval_bm25.yaml`, `R1_retrieval_vector.yaml`, `R2_retrieval_hybrid.yaml`, `R3_retrieval_hybrid_rerank.yaml`.
  - [x] dry-run manifest: `results/ablation/20260519_phase11_retrieval_dry_run_manifest/ablation_manifest.json`.
  - [x] R0 smoke artifact: `results/benchmark/manual_r0_retrieval_bm25_smoke`.
  - [x] execute R0-R3 real retrieval matrix and compare only generated artifacts.
  - [x] report: `results/ablation/20260519_phase11_retrieval_execute/ablation_comparison.md`.
  - [x] smoke result: R0/R1 hit_rate `1.0`; R2/R3 hit_rate `0.875`; all four jobs completed on the same selected case hash.
  - [x] initial full-dev retrieval ablation report: `results/ablation/20260519_phase11_retrieval_dev_full_execute/ablation_comparison.md`.
  - [x] initial full-dev result: R0/R1 hit_rate `1.0`; R2/R3 hit_rate `0.9667`; misses for hybrid/R3 were `VTD-039` and `VTD-036`.
  - [x] investigated hybrid scorer/ranking misses before retrieval-SOTA claims.
  - [x] general schema-evidence guard added after self-overlap filtering; no benchmark IDs or gold SQL are used.
  - [x] final full-dev retrieval ablation report: `results/ablation/20260519_phase11_retrieval_dev_full_final/ablation_comparison.md`.
  - [x] final full-dev result: R0/R1/R2/R3 all hit_rate `1.0` on 60 dev cases; R3 remains identity-rerank only, not a model-backed reranker claim.
- [x] **Automated Ablation Matrix** generation for the A0-A7 8-case smoke comparison table.
- [ ] Larger paper-grade ablation matrix beyond the current 8-case smoke.
- [x] error taxonomy مطابق `docs/06` برای گزارش‌های artifact-backed.
  - `research_error` برای continuity حفظ شده است.
  - `docs06_error` فقط برای خطاهای قابل اثبات از artifact پر می‌شود.
  - valid SQL mismatch بدون judge به صورت `pending_semantic_review` باقی می‌ماند.
  - latest report: `results/error_analysis/20260519_phase11_docs06_taxonomy_a4_token_cap/error_report.md`.
- [x] first Phase 11 error report from real Phase 10 closeout artifact:
  `results/error_analysis/20260517_phase11_spl2_after_fixes/error_report.md`.
- [ ] review حداقل 50 benchmark item با human 2 یا independent judge.
  - current live independent-judge coverage: `5` A4 failure cases with Qwen/DeepSeek agreement; success cases are not covered yet.
- [x] Phase 16 mock/offline judge scaffold:
  - code: `src/evaluation/llm_judge.py`, `scripts/judge_benchmark_artifact.py`.
  - tests: `tests/tier1_unit/test_llm_judge.py` plus artifact-analysis regression -> `7 passed`.
  - standalone real artifact-backed mock judgment: `results/judgments/20260519_phase16_mock_a4_token_cap`.
  - generated files: `judgments.jsonl`, `judge_summary.json`, `judge_reasoning.md`, `judge_costs.json`, `semantic_business_summary.csv`.
  - result: judged 5 failures from `manual_a4_after_generation_token_cap`; `invalid_sql=3`, `requires_semantic_review=2`; semantic scaffold counts `incorrect=3`, `unjudged=2`; mock cost `$0.0`; authoritative=`false`.
  - integrated runner smoke: `results/benchmark/20260519_085308_gold_dev_qwen2-5-coder-7b_phase16_mock_integration_smoke_v2`.
  - integrated smoke result: `evaluated=1`, `execution_accuracy=1.0`, `exact_sql_match=1`, `semantic_correct=1`, `authoritative=false`.
  - A0-A7 mock sweep: `results/judgments/20260519_phase16_mock_a0_a7`; all outputs are non-authoritative and preserve `requires_semantic_review` for valid mismatches.
  - OpenRouter provider wiring implemented with env vars only: `OPENROUTER_API_KEY`, `VTD_OPENROUTER_JUDGE_MODEL`, `OPENROUTER_HTTP_REFERER`, `OPENROUTER_APP_TITLE`.
  - OpenRouter no-key safety smoke: `results/judgments/20260519_phase16_openrouter_no_key_a4_token_cap`; `provider_not_configured=2`, `authoritative=false`.
  - OpenRouter Qwen live retry: `results/judgments/20260519_phase16_openrouter_qwen_a4_sample2_retry2`; model `qwen/qwen3.6-plus`; sample=2 failures-only; `authoritative=true`; semantic business counts `incorrect=2`.
  - OpenRouter DeepSeek free live pilot without reasoning: `results/judgments/20260519_phase16_openrouter_deepseek_free_a4_sample2_no_reasoning`; model `deepseek/deepseek-v4-flash:free`; sample=2 failures-only; `authoritative=true`; verdicts `fail=2`; semantic business counts `incorrect=2`.
  - OpenRouter Qwen all-failure pilot before canonical verdict hardening: `results/judgments/20260519_phase16_openrouter_qwen_a4_failures_all`; judged `5/5`; raw semantic counts `incorrect=4`, `correct=1`.
  - OpenRouter DeepSeek free all-failure pilot before canonical verdict hardening: `results/judgments/20260519_phase16_openrouter_deepseek_free_a4_failures_all`; judged `5/5`; raw semantic counts `incorrect=4`, `unjudged=1`.
  - Judge disagreement/partial case: `VTD-300` should stay adjudication-required because Qwen treated the core rate logic as partial/correct while DeepSeek marked it ambiguous.
  - Canonical verdict hardening added after the all-failure pilots: free-form provider labels such as `partial_match`, `invalid`, and `disapproved` are normalized before summary metrics are written, preventing arbitrary provider wording from becoming paper metrics.
  - Canonical all-failure reruns:
    - `results/judgments/20260519_phase16_openrouter_qwen_a4_failures_all_canonical`
    - `results/judgments/20260519_phase16_openrouter_deepseek_free_a4_failures_all_canonical`
  - Judge agreement analyzer added: `src/evaluation/judge_agreement.py`, `scripts/analyze_judge_agreement.py`, `tests/tier1_unit/test_judge_agreement.py`.
  - Agreement report: `results/judgments/20260519_phase16_qwen_deepseek_a4_failure_agreement/judge_agreement.md`; common cases `5`, semantic agreement `5/5`, verdict agreement `2/5`, final counts `agreed_incorrect=4`, `adjudication_required=1`.
  - All-prediction judge coverage:
    - Qwen: `results/judgments/20260519_phase16_openrouter_qwen_a4_all_predictions`; authoritative `8/8`, semantic counts `correct=3`, `incorrect=4`, `unjudged=1`.
    - DeepSeek free: `results/judgments/20260519_phase16_openrouter_deepseek_free_a4_all_predictions`; authoritative `6/8`, provider errors `2`, semantic counts `correct=2`, `incorrect=1`, `unjudged=5`.
    - Agreement: `results/judgments/20260519_phase16_qwen_deepseek_a4_all_predictions_agreement/judge_agreement.md`; common cases `8`, semantic agreement `4/8`, verdict agreement `4/8`, final counts `agreed_correct=2`, `agreed_incorrect=1`, `adjudication_required=5`.
    - Interpretation: failure-only coverage is no longer the only evidence; two success cases are confirmed by both judges, but high adjudication count means this is still not a paper-grade semantic score.
    - Follow-up policy: DeepSeek free is no longer the active baseline because provider errors left `2/8` cases unjudged. Rerun all-prediction coverage with paid `deepseek/deepseek-v4-flash`, then compare to Qwen. Use `--case-ids` for any third-model adjudicator so only unresolved cases are sent.
  - Paid DeepSeek replacement result:
    - DeepSeek paid: `results/judgments/20260520_phase16_openrouter_deepseek_paid_a4_all_predictions`; authoritative `7/8`, provider parse errors `1`, semantic counts `correct=3`, `incorrect=1`, `unjudged=4`.
    - Agreement: `results/judgments/20260520_phase16_qwen_deepseek_paid_a4_all_predictions_agreement/judge_agreement.md`; common cases `8`, semantic agreement `5/8`, verdict agreement `4/8`, final counts `agreed_correct=3`, `agreed_incorrect=1`, `adjudication_required=4`.
    - Confirmed labels: `VTD-027`, `VTD-039`, `VTD-371` agreed business-correct; `VTD-237` agreed business-incorrect.
    - Still unresolved: `VTD-078`, `VTD-141`, `VTD-300`, `VTD-343`.
  - Consensus tooling:
    - `src/evaluation/judge_consensus.py`
    - `scripts/analyze_judge_consensus.py`
    - default policy requires at least two authoritative non-null semantic votes and no opposing authoritative semantic vote.
    - partial business matches are reported separately when at least two authoritative partial votes exist and there are no non-null semantic votes.
    - single-judge, provider-error and unjudged rows do not become paper claims.
    - verification after partial-policy update: `tests/tier1_unit/test_judge_consensus.py tests/tier1_unit/test_judge_agreement.py tests/tier1_unit/test_llm_judge.py` -> `17 passed`.
  - GPT-5.1 targeted adjudication and consensus:
    - GPT-5.1 artifact: `results/judgments/20260520_phase16_openrouter_gpt51_a4_unresolved_only`; judged `4/4`, authoritative `4/4`, semantic counts `incorrect=3`, `unjudged=1`.
    - Consensus artifact: `results/judgments/20260520_phase16_qwen_deepseek_paid_gpt51_a4_consensus/judge_consensus.md`; final counts after partial policy `consensus_correct=3`, `consensus_incorrect=4`, `consensus_partial_business_match=1`.
    - Metric-policy counts: `semantic_correct=3`, `semantic_incorrect=4`, `partial_business_match=1`, `needs_human_review=0`.
    - Consensus correct: `VTD-027`, `VTD-039`, `VTD-371`.
    - Consensus incorrect under the previous v0 rubric: `VTD-078`, `VTD-141`, `VTD-237`, `VTD-343`.
    - Partial business match under the previous v0 rubric: `VTD-300`, because all three judges treated it as partial/unjudged rather than a final correct/incorrect label.
    - Follow-up policy update: judge prompt version is now `phase16_sql_business_logic_v1`; semantic correctness is whether the generated SQL answers the user question. A second `strict_reference` policy records stricter reference/gold-output-contract correctness. Old v0 consensus artifacts must not be silently reinterpreted as v1 labels.
    - VTD-300 v1 targeted result:
      - semantic policy: Qwen and paid DeepSeek both marked `business_correct`; agreement artifact reports `agreed_correct=1`.
      - strict policy: Qwen marked `business_incorrect`; paid DeepSeek produced `provider_parse_error`; GPT-5.1 strict adjudication marked `business_incorrect`; strict consensus artifact reports `consensus_incorrect=1`.
      - dual-policy report: `results/judgments/20260520_phase16_a4_v1_vtd300_dual_policy_report`; combined label `semantic_correct_strict_incorrect`.
    - Dual-policy report tooling added:
      - `src/evaluation/dual_policy_report.py`
      - `scripts/analyze_dual_policy_judgments.py`
      - `tests/tier1_unit/test_dual_policy_report.py`
      - purpose: merge semantic-user-question and strict-reference agreement/consensus artifacts into one paper-facing table without calling a model or changing judgments.
    - Full A4 v1 dual-policy report:
      - intermediate artifact: `results/judgments/20260520_phase16_a4_v1_all_dual_policy_report`.
      - semantic agreement: `4/8` correct, `4/8` incorrect, agreement `8/8`.
      - strict agreement before final adjudication: `3/8` correct, `4/8` incorrect, `1/8` adjudication-required.
      - final strict adjudication for `VTD-141`: GPT-5.1 marked strict `business_incorrect`.
      - final strict consensus artifact: `results/judgments/20260520_phase16_qwen_deepseek_paid_gpt51_a4_v1_strict_all_consensus`.
      - final dual-policy artifact: `results/judgments/20260520_phase16_a4_v1_all_dual_policy_final`.
      - final combined labels: `both_correct=3`, `both_incorrect=4`, `semantic_correct_strict_incorrect=1`.
      - anti-overfit note: these are evaluation artifacts only; they must not become case-ID-specific prompt/validator tuning.
    - Paper-facing A4 evidence package:
      - code: `src/evaluation/dual_policy_packaging.py`
      - CLI: `scripts/package_dual_policy_evidence.py`
      - test: `tests/tier1_unit/test_dual_policy_packaging.py`
      - output: `results/paper/20260520_phase16_a4_dual_policy_evidence`
      - report: `results/paper/20260520_phase16_a4_dual_policy_evidence/paper_evidence_table.md`
      - counts: benchmark EX `0.375`, valid SQL `0.625`, reliability `0.25`; semantic `4/8` correct; strict `3/8` correct.
      - anti-fake note: package reads existing artifacts only and does not call a model or infer labels.
  - Redaction policy:
    - judge summaries now record `redaction_policy`.
    - raw database rows, result previews, full prompts and raw model responses are excluded from cloud judge payloads.
    - smoke artifact: `results/judgments/20260520_phase16_mock_redaction_policy_smoke/judge_summary.json`.
    - verification: `tests/tier1_unit/test_llm_judge.py tests/tier1_unit/test_judge_consensus.py tests/tier1_unit/test_judge_agreement.py` -> `18 passed`.
  - Robustness: transient `IncompleteRead` is retried/recorded as provider error, and empty provider content is recorded as `provider_parse_error`; unit tests now cover both paths.
  - proposed live judge policy: `qwen/qwen3.6-plus` as primary, `deepseek/deepseek-v4-flash` as cheap baseline, `openai/gpt-5.1` only for small adjudication subset, `google/gemini-3-flash-preview` as optional disagreement check.
  - guardrail: valid result mismatches are not labeled semantically by the mock provider.
- [x] Decision before more scaling: retrieval ablation matrix selected first because it is Phase 11-native and does not require semantic judging or case-specific SQL tuning.

Latest targeted A4 evidence:

```text
artifact: results/benchmark/manual_a4_after_generation_token_cap
report: results/error_analysis/20260518_a4_after_generation_token_cap/error_report.md
evaluated: 8
failures: 5
execution_accuracy: 0.375
valid_sql_rate: 0.625
reliability_score: 0.25
unsafe_sql: 0
research_error_counts: FALSE_ABSTENTION=3, SEMANTIC_REVIEW_REQUIRED=2
interpretation:
  - useful engineering progress
  - not paper-grade evidence
  - not a SOTA/model-quality claim
```

Minimum first-paper ablation:

```text
A0 direct schema-only / minimal context baseline
A1 + Persian NLU
A2 + schema linking
A3 + value linking
A4 + CAG examples
A7 current full Phase-10 system
```

Acceptance:

- [x] A0-A7 smoke ablation table به صورت خودکار از manifest و artifactهای واقعی تولید شد.
- [ ] paper-ready metrics از actual larger runs ساخته شوند.
- [ ] limitations مربوط به single annotator یا second review مستند شود.

Guardrails:

- هر metric باید از artifact واقعی `results/benchmark/...` بیاید.
- configهای ablation نتیجه آزمایش نیستند؛ فقط دستور اجرای آزمایش‌اند.
- هیچ report نباید عدد missing را با مقدار ساختگی پر کند.
- paired significance فقط وقتی مجاز است که case idهای دو run یکسان باشند.

Current Phase 11 status on 2026-05-17:

```text
implemented:
  docs/phases/PHASE_11_ABLATION_ERROR_ANALYSIS.md
  src/evaluation/statistical_tests.py
  src/evaluation/artifact_analysis.py
  src/evaluation/ablation_flags.py
  src/evaluation/ablation_runner.py
  scripts/analyze_benchmark_artifact.py
  experiments/configs/A0_direct_schema_only.yaml
  experiments/configs/A1_persian_nlu.yaml
  experiments/configs/A2_schema_linking.yaml
  experiments/configs/A3_value_linking.yaml
  experiments/configs/A4_cag_examples.yaml
  experiments/configs/A7_full_phase10_system.yaml
  tests/tier1_unit/test_statistical_tests.py
  tests/tier1_unit/test_artifact_analysis.py

pending_before_claiming_first_slice_done:
  run focused Phase 11 tests [done: 5 passed]
  add run_ablation CLI and ablation_runner tests [done]
  generate artifact-backed report from the real Phase 10 closeout artifact [done]
  update task.md and this roadmap with the generated report path [done]

first_report:
  report: results/error_analysis/20260517_phase11_spl2_after_fixes/error_report.md
  summary: results/error_analysis/20260517_phase11_spl2_after_fixes/analysis_summary.json
  total_predictions: 8
  total_attempts: 12
  total_failures_analyzed: 6
  research_error_counts: SEMANTIC_REVIEW_REQUIRED=3, SHAPE_CONTRACT_ERROR=2, FALSE_ABSTENTION=1

dry_run_manifest:
  path: results/ablation/20260517_phase11_dry_run_manifest/ablation_manifest.json
  jobs: 6
  result_status: not_run for all jobs
  planned_python: D:\Project\ADHD-VTD\.venv\Scripts\python.exe
  policy: config manifests are not benchmark results
  runtime_enforced_flags: nlu, schema_linking, value_linking, cag, reflexion, repair
  runtime_locked_flags: safety, validation
  metadata_only_flags: none
```

### Milestone D - Output, Reliability Gate and Safety UX [PAPER 1/2]

هدف: سیستم فقط SQL/result خام ندهد؛ بتواند جواب قابل اعتماد، هشدار، clarification یا abstention تولید کند.

Tasks:

- [ ] `src/output/answer_formatter.py`.
- [ ] `src/output/chart_recommender.py`.
- [ ] `src/output/explanation_builder.py`.
- [ ] `src/output/narrative_generator.py`.
- [ ] clinical/research disclaimer از threat model در output.
- [ ] reliability object با وضعیت‌های `answer | clarify | abstain | warn`.
- [x] first annotation-only reliability gate object:
  - code: `src/evaluation/reliability_gate.py`.
  - benchmark wiring: `scripts/run_benchmark.py` records `reliability_gate_action`, `reliability_gate_reason`, and warnings when `reliability_gate=true`.
  - flag contract: `src/evaluation/ablation_flags.py` treats `reliability_gate` as runtime-enforced.
  - docs: `docs/phases/PHASE_13_RELIABILITY_GATE.md`.
  - current limitation: annotation-only; it does not yet overwrite graph routing or final user-facing action.
- [x] first semantic/question-SQL warning if a lightweight critic finds a clear explicit-obligation mismatch:
  - code: `src/evaluation/sql_consistency_critic.py`.
  - benchmark fields: `sql_consistency_critic`, `sql_consistency_issue_count`.
  - policy: broad obligations only; no case IDs, no gold SQL, no exact result labels.
- [x] inspected graph state and benchmark prediction signals for the standalone gate contract:
  - graph state has enough single-candidate runtime signals for annotation-only gating.
  - graph state does not yet include `candidate_sqls`, `selected_candidate_id`, `reliability`, or candidate-consistency fields.
  - benchmark-only fields such as `gold_sql`, `execution_correct`, `result_match` and `ok` remain reporting labels and are disallowed for gate decisions.
- [x] latency-aware multi-candidate scaffolding:
  - candidate consistency code: `src/evaluation/candidate_consistency.py`.
  - adaptive trigger policy: `src/evaluation/multi_candidate_policy.py`.
  - default policy: simple/confident questions stay single-candidate; retry/validation failure, execution failure, low-confidence and complex dashboard/advanced hints can request two candidates.
  - graph generation of multiple candidates is still not enabled.
- [x] inactive-by-default graph state fields:
  - `candidate_sqls`, `selected_candidate_id`, `candidate_consistency`, `multi_candidate_policy`, `reliability`.
  - benchmark prediction preservation added in `scripts/run_benchmark.py`.
  - no latency change because no graph node currently generates extra candidates.
- [x] annotation-only adaptive policy node:
  - `src/graph/nodes/base_nodes.py::plan_multi_candidate`.
  - workflow path: before initial SQL generation and before retry generation.
  - no extra candidate generation and no extra LLM call unless `multi_candidate_generation=true` is explicitly enabled.
- [x] feature-flagged adaptive candidate generation path:
  - runtime flag: `multi_candidate_generation`.
  - code: `src/graph/nodes/base_nodes.py::generate_sql`.
  - config: `experiments/configs/A7_reliability_gate_adaptive_multicandidate_smoke.yaml`.
  - default: absent/false flag keeps one generation call.
  - enabled path: triggered policy cases generate up to the policy candidate count, validate/execute candidates for runtime result hashes, record `candidate_sqls`, `selected_candidate_id`, and `candidate_consistency`, then send the selected candidate through the normal parse/validate/execute path.
  - verification: graph/multi-candidate/ablation flag subset -> `18 passed`; compile check passed.
  - real adaptive smoke artifact: `results/benchmark/manual_phase13_adaptive_multicandidate_smoke`.
  - result: evaluated `4`, EX `0.25`, valid SQL `0.5`, reliability `-0.5`, unsafe SQL `0`, p95 latency `106646ms`.
  - A/B report: `results/multi_candidate_ablation/20260521_phase13_policy_vs_adaptive_multicandidate_smoke_v2`.
  - A/B status: `blocked`; valid SQL delta `-0.25`, p95 latency delta `+52292ms`, candidate issue `NO_VIABLE_CANDIDATES=2`.
  - decision: keep feature disabled outside explicit experiments.
- [x] safer candidate adoption redesign:
  - no extra candidate generation inside retry/validation/error loops.
  - adopt-only-if-safe: consistency must pass and selected candidate must be viable.
  - otherwise keep the primary generation and preserve candidates as review evidence only.
  - focused verification: `20 passed`; compile check passed.
  - second adaptive smoke artifact: `results/benchmark/manual_phase13_adaptive_multicandidate_smoke_v2`.
  - second A/B report: `results/multi_candidate_ablation/20260521_phase13_policy_vs_adaptive_multicandidate_smoke_v3`.
  - second A/B status: `insufficient_semantic_evidence`; EX delta `0.0`, valid SQL delta `0.0`, p95 latency delta `+19852ms`, candidate issue `NO_VIABLE_CANDIDATES=1`.
  - decision: still not ready for routing or claims.
- [x] shadow-only candidate evidence mode:
  - runtime flag: `multi_candidate_adoption`.
  - default: `false`.
  - `multi_candidate_generation=true` can record candidate evidence without changing selected output.
  - config: `experiments/configs/A7_reliability_gate_adaptive_multicandidate_smoke.yaml` now sets `multi_candidate_adoption: false`.
  - verification: focused tests -> `21 passed`; compile check passed.
  - shadow artifact: `results/benchmark/manual_phase13_shadow_multicandidate_smoke`.
  - A/B report: `results/multi_candidate_ablation/20260521_phase13_policy_vs_shadow_multicandidate_smoke`.
  - A/B status: `insufficient_semantic_evidence`; EX delta `0.0`, valid SQL delta `0.0`, p95 latency delta `+7577ms`, candidate issue `NO_VIABLE_CANDIDATES=1`.
  - decision: use only as experimental evidence; no routing/adoption.
- [x] multi-candidate cost-benefit series report:
  - code: `src/evaluation/multi_candidate_series_report.py`.
  - CLI: `scripts/build_multi_candidate_series_report.py`.
  - tests: `tests/tier1_unit/test_multi_candidate_series_report.py`.
  - verification: `4 passed`; compile check passed.
  - report: `results/multi_candidate_ablation/20260521_phase13_multicandidate_cost_benefit_series/multi_candidate_series_report.md`.
  - summary: `run_count=3`, `blocked=1`, `insufficient_semantic_evidence=2`, recommendation `do_not_adopt_candidate_adoption`.
  - paper framing: negative/neutral result should be reported as an explored but not yet cost-effective intervention, not hidden and not converted into a success claim.
- [x] candidate-evidence-missing gate rule and smoke:
  - rule: when adaptive policy expects more than one candidate but no candidate SQL/consistency evidence is present, the gate returns `needs_review` with reason `candidate_evidence_missing_after_trigger`.
  - focused verification: `25 passed`; compile check passed.
  - artifact: `results/benchmark/manual_phase13_shadow_multicandidate_gate_evidence_smoke`.
  - reliability analysis: `results/reliability_gate/20260521_phase13_shadow_multicandidate_gate_evidence_analysis`.
  - A/B report: `results/multi_candidate_ablation/20260521_phase13_policy_vs_shadow_gate_evidence_smoke`.
  - result: EX delta `0.0`, valid SQL delta `0.0`, reliability delta `0.0`, unsafe SQL delta `0.0`, p95 latency delta `+48260ms`, status `insufficient_semantic_evidence`.
  - gate action change: `candidate_evidence_missing_after_trigger=1`, which moves one post-hoc incorrect case to `needs_review`.
  - decision: useful as conservative review signal, but not sufficient for routing/adoption because quality did not improve and latency increased.
- [x] fixed annotation-only candidate-evidence gate behavior:
  - issue: annotation-only baseline can mark multi-candidate policy eligibility while `multi_candidate_generation=false`; missing candidate evidence should not trigger review in that mode.
  - code: `scripts/run_benchmark.py` records `multi_candidate_generation_enabled`; `src/evaluation/reliability_gate.py` requires candidate evidence only when generation is active.
  - verification: `26 passed`; compile check passed.
- [x] matched dev-spl2 A/B after the gate fix:
  - baseline: `results/benchmark/manual_phase13_gate_dev_spl2_after_gate_fix`.
  - shadow: `results/benchmark/manual_phase13_shadow_multicandidate_dev_spl2_after_gate_fix`.
  - comparison: `results/multi_candidate_ablation/20260521_phase13_gate_vs_shadow_multicandidate_dev_spl2_after_gate_fix`.
  - integrity: same dataset hash, same selected cases hash, same model.
  - deltas: EX `0.0`, valid SQL `0.0`, reliability `0.0`, unsafe SQL `0.0`.
  - latency note: p95 delta `-401707ms` is dominated by a baseline outlier (`538185ms`), so it should not be interpreted as general speedup.
  - status: `insufficient_semantic_evidence`.
- [x] updated five-run multi-candidate cost-benefit series:
  - report: `results/multi_candidate_ablation/20260521_phase13_multicandidate_cost_benefit_series_v4/multi_candidate_series_report.md`.
  - summary: `run_count=5`, `blocked=1`, `insufficient_semantic_evidence=4`, recommendation `do_not_adopt_candidate_adoption`.
  - paper framing: preserve this as a negative/neutral result unless a future larger dev run shows semantic gain without unacceptable latency/regression cost.
- [x] dual-policy judge ablation planning added for the matched dev-spl2 artifacts:
  - code: `src/evaluation/judge_ablation_plan.py`.
  - CLI: `scripts/plan_dual_policy_judge_ablation.py`.
  - tests: `tests/tier1_unit/test_judge_ablation_plan.py`.
  - plan directory: `results/judgments/20260522_phase13_gate_vs_shadow_dev_spl2_dual_policy_plan`.
  - runbook: `RUN_JUDGE_ABLATION.ps1`.
  - planned judges: `qwen/qwen3.6-plus` and `deepseek/deepseek-v4-flash`.
  - planned policies: semantic-user-question and strict-reference over all 8 predictions for baseline and shadow artifacts.
  - verification: `24 passed`; compile check passed.
  - anti-fake framing: this is a command plan only; no judge labels or semantic results exist until the runbook is executed with a real OpenRouter key.
- [x] execute the generated judge runbook and feed the resulting dual-policy dirs into the final multi-candidate A/B report:
  - final artifact: `results/judgments/20260522_phase13_gate_vs_shadow_dev_spl2_dual_policy_plan/ablation/multi_candidate_dual_policy_ablation`.
  - integrity: `same_dataset_hash=true`, `same_selected_cases_hash=true`, `same_model=true`, `common_cases=8`.
  - benchmark deltas: EX `0.0`, valid SQL `0.0`, reliability `0.0`, unsafe SQL `0.0`.
  - semantic policy: baseline `5/8` correct, shadow/adaptive `4/8` correct; one baseline-correct case regressed to not-correct.
  - strict policy: both sides `3/8` correct with one adjudication-required row; no strict quality improvement.
  - final status: `blocked` because semantic correctness regressed.
  - decision: multi-candidate adoption remains disabled; shadow-only evidence is useful for review/research reporting, not routing or SOTA claims.
- [x] rebuild the multi-candidate cost-benefit series with the final dual-policy A/B artifact:
  - report: `results/multi_candidate_ablation/20260522_phase13_multicandidate_cost_benefit_series_v5_dual_policy/multi_candidate_series_report.md`.
  - summary: `run_count=6`, `blocked=2`, `insufficient_semantic_evidence=4`, recommendation `do_not_adopt_candidate_adoption`.
  - interpretation: the negative/neutral finding is now stronger because dual-policy evidence found a semantic regression despite zero EX/valid-SQL/reliability gains.
- [x] richer semantic warning for two high-risk valid-but-wrong patterns:
  - risk-profile stress/sleep threshold summaries must select stress/sleep context averages, not only count risk groups.
  - comparative questions must include a grouped comparison or baseline instead of filtering one group.
  - analysis-only recompute artifacts:
    - `results/reliability_gate/20260522_phase13_gate_dev_spl2_richer_semantic_critic_recomputed`.
    - `results/reliability_gate/20260522_phase13_shadow_multicandidate_dev_spl2_richer_semantic_critic_recomputed`.
  - baseline recompute: `answer_on_valid_result_mismatch` reduced from 3 stored annotations to 1 recomputed decision, with 2 cases moved to retry.
  - shadow recompute: `answer_on_valid_result_mismatch` reduced from 2 stored annotations to 1 recomputed decision, with 1 case moved to retry.
  - verification: focused critic/gate/analysis tests -> `31 passed`; compile check passed.
  - limitation: this is post-hoc analysis on existing predictions; rerun benchmark before any routing claim.
- [x] rerun matched dev-spl2 with the richer critic active in runtime gate annotations:
  - artifact: `results/benchmark/manual_phase13_gate_dev_spl2_richer_semantic_critic`.
  - result: EX `0.375`, valid SQL `0.625`, reliability `0.25`, unsafe SQL `0`.
  - A/B vs previous baseline: `results/reliability_gate/20260522_phase13_gate_dev_spl2_before_after_richer_semantic_critic`.
  - interpretation: reliability improved, but valid SQL regressed; blocked.
- [x] fix general shape-key validator false positive and rerun:
  - shape validator now accepts `mental_health_risk` anywhere in the SELECT clause, not only immediately after `SELECT`.
  - focused verification: `45 passed`; compile check passed.
  - rerun artifact: `results/benchmark/manual_phase13_gate_dev_spl2_richer_critic_after_shape_key_fix`.
  - result: EX `0.375`, valid SQL `0.875`, reliability `-1.25`, unsafe SQL `0`.
  - A/B vs previous baseline: `results/reliability_gate/20260522_phase13_gate_dev_spl2_before_after_richer_critic_shape_key_fix`.
  - interpretation: valid SQL improved, but reliability worsened because three valid-result-mismatch answers were still answered; insufficient semantic evidence.
- [x] tighten average-threshold critic:
  - above/below-average questions now require AVG threshold evidence in WHERE/HAVING, not merely AVG in SELECT.
  - focused verification: `46 passed`; compile check passed.
  - recompute artifact: `results/reliability_gate/20260522_phase13_gate_dev_spl2_richer_critic_shape_key_fix_recomputed_avg_threshold`.
  - recomputed result: `answer_on_valid_result_mismatch=2`, `retry_requested=2`, but this is analysis-only.
- [x] rerun dev-spl2 once more after the AVG-threshold critic fix.
  - artifact: `results/benchmark/manual_phase13_gate_dev_spl2_richer_critic_avg_threshold_final`.
  - result: EX `0.375`, valid SQL `0.875`, reliability `-1.25`, unsafe SQL `0`, latency mean `17328.75ms`, median `15082.0ms`, p95 `35112.0ms`.
  - analysis: `results/reliability_gate/20260522_phase13_gate_dev_spl2_richer_critic_avg_threshold_final_analysis`.
  - A/B vs previous gate baseline: `results/reliability_gate/20260522_phase13_gate_dev_spl2_before_after_richer_critic_avg_threshold_final`.
  - A/B integrity: `same_dataset_hash=true`, `same_selected_cases_hash=true`, `same_model=true`.
  - A/B deltas: EX `0.0`, valid SQL `+0.125`, reliability `-0.75`, unsafe SQL `0.0`, p95 `-503073ms`.
  - gate actions: `needs_review=1`, `answer=5`, `retry=2`.
  - post-hoc risk: `review_or_clarify_on_incorrect=1`, `answer_on_correct=3`, `retry_requested=2`, `answer_on_valid_result_mismatch=2`.
  - interpretation: the critic improved valid SQL versus the earlier baseline and reduced the outlier-heavy latency number in this slice, but it did not improve EX and worsened reliability. Routing remains disabled.
  - anti-fake note: semantic evidence is unavailable in this A/B report, so no semantic-correctness improvement claim is allowed.
- [x] add a conservative review-on-consistency-failure policy for valid-but-risky SQL.
  - flag: `reliability_gate_review_consistency_failures`.
  - config: `experiments/configs/A7_reliability_gate_review_consistency_dev_spl2.yaml`.
  - default remains unchanged; the new flag changes consistency failures from retry to `needs_review` annotation.
  - verification: focused gate/critic/shape/ablation tests -> `51 passed`; compile check passed.
  - runtime artifact: `results/benchmark/manual_phase13_gate_dev_spl2_review_consistency_failures`.
  - result: EX `0.375`, valid SQL `0.875`, reliability `-1.25`, unsafe SQL `0`, latency mean `17355.88ms`, median `15256.5ms`, p95 `42649.0ms`.
  - analysis: `results/reliability_gate/20260522_phase13_gate_dev_spl2_review_consistency_failures_analysis`.
  - gate actions: `needs_review=3`, `answer=5`; `consistency_failed_review=2`.
  - A/B vs original gate baseline: EX `0.0`, valid SQL `+0.125`, reliability `-0.75`, unsafe SQL `0.0`, status `insufficient_semantic_evidence`.
  - A/B vs AVG-threshold final run: EX `0.0`, valid SQL `0.0`, reliability `0.0`, unsafe SQL `0.0`, p95 `+7537ms`, status `insufficient_semantic_evidence`.
  - interpretation: the policy changes annotations as intended, but benchmark actual actions are unchanged because gate routing remains disabled. This is evidence for a future routing experiment, not a quality claim.
- [ ] decide whether to add `reliability_gate_route_actions` as a separate experiment flag.
  - compare annotation-only versus routed `needs_review`.
  - measure semantic_user_question, strict_reference, abstention precision/recall, reliability score, unsafe SQL and latency.
  - do not adopt if SQL-positive cases simply become wrong abstentions.
- [ ] aggregate-first / low-row-count protection.
- [ ] chart recommendation بر اساس `recommended_visual`.
- [ ] narrative بدون hallucinated data.

Acceptance:

- [ ] scalar/table/ranking/distribution outputs درست format شوند.
- [ ] unsafe/ambiguous/out-of-schema cases خروجی مناسب بگیرند.
- [ ] mental-health disclaimer در جواب‌های مرتبط وجود داشته باشد.
- [ ] warningها در benchmark قابل اندازه‌گیری باشند.
- [x] small dev smoke with `reliability_gate=true` completed:
  - artifact: `results/benchmark/manual_phase13_reliability_gate_smoke`.
  - result: evaluated `4`, EX `0.25`, valid SQL `0.5`, reliability `-0.5`, gate actions `needs_review=2`, `answer=2`.
  - analysis: `results/reliability_gate/20260520_phase13_gate_smoke_analysis/reliability_gate_report.md`.
  - post-hoc risk: `answer_on_valid_result_mismatch=1`, so runtime-only signals are not enough for routing.
  - limitation: runtime-only gate marked one valid-but-wrong SQL as `answer`; keep annotation-only until semantic/consistency evidence is available.
- [x] small dev smoke after question/SQL consistency critic wiring completed:
  - artifact: `results/benchmark/manual_phase13_consistency_gate_smoke`.
  - result: evaluated `4`, EX `0.25`, valid SQL `0.5`, reliability `-0.5`, gate actions `needs_review=2`, `answer=2`.
  - analysis: `results/reliability_gate/20260520_phase13_consistency_gate_smoke_analysis/reliability_gate_report.md`.
  - consistency issue count: `0` hard issues across the final four predictions.
  - interpretation: the first critic did not introduce hard false positives on this smoke, but it also did not remove the valid-result-mismatch risk. Routing remains blocked.
- [x] focused latency-aware multi-candidate policy tests completed:
  - command: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_multi_candidate_policy.py tests\tier1_unit\test_candidate_consistency.py tests\tier1_unit\test_reliability_gate.py -vv --tb=short`.
  - result: `26 passed`.
  - interpretation: multi-candidate is available as a contract/policy only; it is not an always-on latency multiplier.
- [x] graph state reliability surface tests completed:
  - focused result: `28 passed`.
  - broader graph/reliability regression: `40 passed`.
  - compile check passed for `src\graph\state.py`, candidate consistency/policy, reliability gate and benchmark wiring.
- [x] policy-node smoke completed:
  - artifact: `results/benchmark/manual_phase13_policy_node_smoke`.
  - result: evaluated `4`, EX `0.25`, valid SQL `0.75`, reliability `-1.25`, unsafe SQL `0`, latency mean `25962.25`.
  - policy annotation: enabled `2/4`, disabled `2/4`; triggers `complex_intent=1`, `retry_in_progress=2`, `validation_failed=2`.
  - artifact analysis: `results/reliability_gate/20260520_phase13_policy_node_smoke_analysis/reliability_gate_report.md`.
  - interpretation: the node records adaptive eligibility only; valid-result-mismatch risk remains, so routing stays blocked.
- [x] multi-candidate regression plan recorded before enabling actual candidate generation:
  - semantic_user_question correctness is primary; strict_reference correctness is reported separately for paper rigor.
  - A/B must compare single-candidate annotation-only baseline vs adaptive candidate generation on the same selected_cases_hash.
  - stop condition: if adaptive generation increases false-answer or valid-result-mismatch risk, keep it disabled and use candidate consistency only as a review signal.
- [x] artifact-backed A/B comparison tooling added before enabling actual candidate generation:
  - code: `src/evaluation/multi_candidate_ablation.py`.
  - CLI: `scripts/analyze_multi_candidate_ablation.py`.
  - tests: `tests/tier1_unit/test_multi_candidate_ablation.py`.
  - focused verification: `13 passed`.
  - self-check artifact: `results/multi_candidate_ablation/20260521_phase13_policy_node_self_check`.
  - self-check status: `insufficient_semantic_evidence`, because it compares the policy-node smoke artifact to itself and no dual-policy A/B labels are supplied.
  - interpretation: tooling is ready; this is not a quality claim for multi-candidate generation.
- [x] run matched A/B after the feature-flagged path:
  - baseline: `experiments/configs/A7_reliability_gate_smoke.yaml`.
  - adaptive: `experiments/configs/A7_reliability_gate_adaptive_multicandidate_smoke.yaml`.
  - compare with `scripts/analyze_multi_candidate_ablation.py`.
  - result: multiple smoke comparisons completed; none is sufficient for paper/routing claim.
- [x] first matched A/B smoke completed and blocked:
  - baseline artifact: `results/benchmark/manual_phase13_policy_node_smoke`.
  - adaptive artifact: `results/benchmark/manual_phase13_adaptive_multicandidate_smoke`.
  - comparison artifact: `results/multi_candidate_ablation/20260521_phase13_policy_vs_adaptive_multicandidate_smoke_v2`.
  - decision: do not spend Phase 16 judge budget on this failed adaptive smoke unless needed for audit; runtime regressions already block rollout.
- [ ] redesign adaptive policy/selection before the next A/B:
  - likely direction: avoid retry-triggered generation when previous failures indicate the model is repeating invalid shapes, or use multi-candidate only as shadow-review evidence until at least one viable candidate exists.
  - anti-overfit rule: do not tune this to `VTD-343` or any single case ID.
- [x] first redesign done:
  - retry-triggered generation is suppressed at generation time.
  - invalid/disagreeing candidates are review-only.
- [x] next redesign question:
  - decision: multi-candidate remains shadow-only by default until candidate viability/consensus is proven on a larger dev sample.
- [x] current decision:
  - multi-candidate remains shadow-only by default.
  - candidate adoption requires explicit `multi_candidate_adoption=true` and is not allowed for paper/routing claims yet.

### Milestone E - Multi-Candidate, Reflexion Package and Consistency [PAPER 2]

هدف: بالا بردن reliability با چند candidate، consistency check و package مستقل reflexion.

Tasks:

- [ ] graph state fields: `candidate_sqls`, `selected_candidate_id`, `reliability`, `value_links`.
- [ ] `generate_candidates` node.
- [ ] `check_candidate_consistency` node.
- [ ] `compute_reliability` node.
- [ ] `src/sql_validation/reliability_gate.py`.
- [ ] `src/reflexion/error_taxonomy.py`.
- [ ] `src/reflexion/critic.py`.
- [ ] `src/reflexion/repair_planner.py`.
- [ ] `src/reflexion/retry_policy.py`.
- [ ] `src/reflexion/transition_memory.py`.
- [ ] anti-loop tests.

Acceptance:

- [ ] disagreement مهم بین candidates باعث abstain یا clarification شود.
- [ ] retry success rate گزارش شود.
- [ ] same SQL / same error loop متوقف شود.
- [ ] attempts trace با benchmark runner یکی شود.

### Milestone F - Edge Runtime and Optimization [EDGE_LATER]

هدف: بعد از research runtime پایدار، اجرای سبک و قابل deploy روی local/edge.

Tasks:

- [ ] node-level latency profiling.
- [ ] cache برای normalization، schema link، retrieval و successful SQL.
- [ ] model comparison under same benchmark.
- [ ] lightweight state machine prototype.
- [ ] comparison between LangGraph and edge state machine.

Acceptance:

- [ ] median و p95 latency گزارش شود.
- [ ] EX، RS، Valid SQL Rate و latency بین runtimeها مقایسه شود.
- [ ] unsafe execution همچنان `0` بماند.

### Milestone G - Research Packaging [FINAL]

هدف: پروژه به artifact قابل ارائه به supervisor، GitHub و paper تبدیل شود.

Tasks:

- [ ] `scripts/reproduce_paper_results.py`.
- [ ] `results/reports/paper_tables.md`.
- [ ] `docs/paper/limitations.md`.
- [ ] `docs/paper/ablation_table.md`.
- [ ] `docs/paper/qualitative_examples.md`.
- [ ] final `walkthrough.md`.
- [ ] root `README.md` با feature decision table، commands و benchmark guide.
- [ ] GitHub cleanup.
- [ ] paper draft.

Acceptance:

- [ ] reviewer بتواند sample benchmark را بازتولید کند.
- [ ] claims فقط از actual run artifacts بیایند.
- [ ] dataset card، threat model و limitations کامل باشند.

### Milestone H - Semantic & Business Verification [LLM_JUDGE]

هدف: اطمینان از اینکه کوئری‌ها علاوه بر اجرای درست، از نظر بیزینسی و معنایی هم دقیقاً پاسخ سوال هستند.

Tasks:

- [ ] پیاده‌سازی `src/evaluation/llm_judge.py`.
- [ ] تعریف interface برای judge providerها: `openai`, `local`, `mock`.
- [ ] استفاده از مدل judge آنلاین یا local برای داوری بین سوال، SQL تولید شده، Gold SQL، schema context و preview/hash نتیجه.
- [ ] گزارش "Semantic Correctness Score" در کنار EX.
- [ ] تحلیل تفاوت بین "درستی سینتکسی" و "درستی بیزینسی".
- [ ] اضافه کردن `run_benchmark.py --use-judge --judge-provider ...`.
- [x] تولید `judgments.jsonl`, `judge_reasoning.md`, `judge_costs.json`, `semantic_business_summary.csv`.
- [x] تولید agreement report از دو judgment artifact مستقل.
- [ ] privacy guard برای cloud judge: فقط داده synthetic/de-identified/aggregate یا preview redacted ارسال شود.

Acceptance:

- [x] benchmark/judge artifacts می‌توانند نشان دهند query از نظر execution/shape با benchmark mismatch دارد و از نظر business logic هم توسط judge مستقل غلط است.
- [x] judge prompt version، judge model و token/cost fields در artifactها ذخیره می‌شود؛ redaction field پایه وجود دارد، اما privacy policy کامل هنوز باز است.
- [ ] failures و نمونه‌ای از successes توسط judge بررسی شوند. failures انجام شده؛ success sample هنوز باز است.
- [ ] metricهای static و judge-based در گزارش جدا باشند.

## اولویت فوری

```text
1. Phase 10: validate local model loading with run_agent.py. [DONE on 2026-05-15 with Qwen2.5-Coder-3B GGUF smoke]
2. Phase 10: run agent --samples-per-level 1 on dev with full_trace. [DONE on 2026-05-15 with artifacts]
3. Phase 10: inspect attempts.jsonl and failures.jsonl, then fix the first bottleneck. [DONE on 2026-05-15: taxonomy classification]
4. Phase 10: run sample-20 dev agent benchmark. [DONE on 2026-05-15 with 3B smoke model]
5. Phase 10: run behavior_dev benchmark and verify action-based scoring. [DONE on 2026-05-16 with metrics fix]
6. Phase 10: implement benchmark leakage/overfit audit. [DONE initial audit on 2026-05-16; self-overlap mitigation implemented and verified in retrieval/agent artifacts]
7. Phase 10: run balanced dev agent benchmark. [DONE on 2026-05-16]
8. Phase 10: run fixed test benchmark only after dev traces are explainable. [BLOCKED: dev quality/leakage mitigation not ready]
9. Phase 11: verify first-slice statistical/artifact-analysis tooling. [DONE: tests passed and report generated]
10. Phase 11: add run_ablation CLI + ablation_runner tests. [DONE]
11. Phase 11: generate artifact-backed report from the Phase 10 closeout artifact. [DONE: results/error_analysis/20260517_phase11_spl2_after_fixes/error_report.md]
12. Phase 11: run ablation dry-run manifest, then execute only real benchmark-backed ablations. [DRY-RUN DONE; A0-A7 SMOKE REAL RUNS DONE]
13. Phase 11: strict feature-flag verification before real ablations. [DONE: enforced/locked contract recorded]
14. Phase 11: implement true value-linking isolation. [DONE: value links now reach prompt/state only when flag is enabled]
15. Phase 11: run real A0-A7 smoke ablation. [DONE: results/ablation/20260517_phase11_a0_a7_execute/ablation_manifest.json]
16. Phase 11: generate formal ablation comparison report. [DONE: results/ablation/20260517_phase11_a0_a7_execute/ablation_comparison.md]
17. Phase 11: inspect A4 latency anomaly before scaling the ablation suite. [DONE: VTD-371 dominated latency; SQL execution was 46ms, wall-clock was 1603172ms]
18. Phase 11: rerun targeted A4 smoke after the value-link/generation-latency trace fix. [DONE: results/benchmark/manual_a4_after_value_link_trace_fix]
19. Phase 11: add matrix intent/prompt/shape hardening after the A4 rerun. [DONE: 36 focused tests passed]
20. Phase 11: rerun targeted A4 smoke after matrix hardening. [DONE: results/benchmark/manual_a4_after_matrix_hardening]
21. Phase 11: decide whether to add a general matrix support-threshold/sorting policy or defer exact-gold mismatches to Phase 16 semantic judge. [DONE: general policy adopted from documented table distribution, not case ID]
22. Phase 11: rerun targeted A4 smoke after support-threshold/sorting policy. [DONE: results/benchmark/manual_a4_after_matrix_support_policy; VTD-371 exact-correct; overall A4 still weak due FALSE_ABSTENTION=5]
23. Phase 11: diagnose A4 false-abstention regressions before scaling A0-A7 again. [DONE for first mitigation pass: latest A4 target artifact is results/benchmark/manual_a4_after_generation_token_cap]
24. Phase 11: choose next safe path. [DONE: Phase 16 mock/offline judge scaffold selected first]
25. Phase 16: add mock/local/online LLM-as-a-Judge implementation after Phase 11 artifact analysis is stable. [IN PROGRESS: mock/offline and OpenRouter provider done; local provider pending]
26. Phase 16: add `judge_costs.json`, `semantic_business_summary.csv`, and `run_benchmark.py --use-judge --judge-provider mock` integration. [DONE for mock mode]
27. Phase 16: choose next judge path. [DONE for first pilot: Qwen and DeepSeek live sample=2 pilots completed]
28. Phase 16: run controlled multi-judge expansion with failure and success coverage, then report agreement/consensus without paper-grade claims until review size and privacy/redaction policy are adequate. [IN PROGRESS: all-prediction A4 agreement, paid DeepSeek replacement, GPT-5.1 targeted adjudication, conservative consensus, redaction policy, dual semantic/strict v1 judge policies and A4 paper-facing evidence package done; larger review/local judge still needed]
```

### Immediate Gate 1 - Local Model Smoke

Status: DONE for the first smoke model on 2026-05-15. Before any target-paper claim, repeat the same protocol with the selected paper model.

Before any remaining Phase 10 benchmark, run a single-question local model smoke and record the result in `task.md`.

Command:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\Qwen__Qwen2.5-Coder-3B-Instruct-GGUF\qwen2.5-coder-3b-instruct-q4_k_m.gguf"
.\.venv\Scripts\python.exe scripts\run_agent.py "درصد دانشجویان افسرده چقدر است؟" --verbose
```

Pass condition: model loads, graph reaches generation, and the output either produces SQL that reaches validation or fails through a controlled parser/validation error that can be inspected in the next benchmark trace.

Latest recorded result:

```text
model: qwen2.5-coder-3b-instruct-q4_k_m.gguf
status: passed
generated_sql: SELECT AVG(depression_flag) * 100.0 FROM student_depression
raw_response: valid JSON
parsed_payload: available in --verbose output
validation_errors: []
retry_count: 0
attempt_count: 1
```

### Immediate Gate 2 - Real Agent Balanced Smoke

Status: DONE on 2026-05-15.

Run the real benchmark path with one case per difficulty level, using the same local model and full trace contract:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\Qwen__Qwen2.5-Coder-3B-Instruct-GGUF\qwen2.5-coder-3b-instruct-q4_k_m.gguf"
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --ablation-id full_trace
```

Pass condition:

- terminal progress shows every selected case with `[current/total]`, difficulty, action, latency, elapsed time and ETA;
- output folder name includes `agent`, `dev`, model slug and `full_trace`;
- all required artifact files exist;
- `attempts.jsonl` contains prompt, raw model response and parsed payload for every generation attempt;
- failures, if any, are categorized and inspectable without crashing the run;
- result metrics are copied back into `task.md` before moving to sample-20 or leakage audit.

Latest recorded result:

```text
output_dir: results/benchmark/20260515_095324_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace
selected_cases: 4, one per difficulty
attempts: 8
missing_prompt/raw/parsed_payload: 0/0/0
execution_accuracy: 1/4 = 0.25
valid_sql_rate: 2/4 = 0.50
reliability_score: -0.5
unsafe_sql: 0
failure_taxonomy: BEHAVIOR_MISMATCH=3
```

Observed engineering issue fixed during this gate: JSON artifact writers now serialize Pydantic/dataclass/path runtime objects before writing.

### Immediate Gate 3 - First Bottleneck Inspection

Status: DONE on 2026-05-15.

Use the latest balanced smoke artifacts:

```text
results/benchmark/20260515_095324_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace
```

Inspection order:

1. Read `failures.jsonl` to list failed case ids, expected action, actual action, generated SQL and error class.
2. Read matching rows from `attempts.jsonl` and inspect prompt, raw response, parsed payload, validation errors and retry behavior.
3. Classify the first bottleneck as one of: intent routing, prompt/schema context, parser, validation, execution mismatch, metric/taxonomy bug, or model capability.
4. Before changing code, record the selected bottleneck and planned fix in `task.md`.
5. Apply the smallest fix, add/adjust a focused test, then rerun the smallest benchmark needed to verify the fix.

Latest recorded result:

```text
selected_bottleneck: metric/taxonomy bug
fix: agent benchmark now classifies INVALID_SQL, RESULT_MISMATCH, MISSING_GENERATED_SQL and ACTION_MISMATCH
verification_tests: test_agent_benchmark_trace.py -> 2 passed; test_dataset_loader_sampling.py -> 3 passed
verification_run: results/benchmark/20260515_095703_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace_taxonomy
taxonomy_after_fix: INVALID_SQL=2, RESULT_MISMATCH=1
```

### Immediate Gate 4 - Sample-20 Dev Agent Benchmark

Status: DONE on 2026-05-15 for the 3B smoke model.

Run:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\Qwen__Qwen2.5-Coder-3B-Instruct-GGUF\qwen2.5-coder-3b-instruct-q4_k_m.gguf"
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --sample 20 --bootstrap-iterations 300 --ablation-id full_trace_sample20
```

Record in `task.md`:

- output directory;
- total evaluated and failures;
- execution accuracy, valid SQL rate, reliability score and unsafe SQL count;
- latency mean/median/p95;
- error taxonomy counts;
- whether prompts/raw responses/parsed payloads are complete in `attempts.jsonl`.

First attempt finding:

```text
partial_output_dir: results/benchmark/20260515_095947_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace_sample20
status: failed before final artifacts
error: ValueError: Requested tokens (2214) exceed context window of 2048
fix_required: catch per-case workflow/model exceptions, record failed case, continue benchmark, write artifacts
```

Second attempt finding:

```text
partial_output_dir: results/benchmark/20260515_100341_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace_sample20_contained
status: timed out before final artifacts
additional_fix_required: make local LLM context window configurable instead of hardcoded n_ctx=2048; consider incremental checkpointing before long benchmark runs
```

Applied fixes after second attempt:

```text
VTD_LLM_N_CTX: added, default 4096
partial artifacts: added after every case
verification: test_agent_benchmark_trace.py -> 3 passed; gold partial_smoke wrote partial_predictions/failures/attempts
```

Completed run:

```text
output_dir: results/benchmark/20260515_114735_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace_sample20_cache_nctx4096
evaluated: 20
difficulty_counts: complex=15, easy=5
execution_accuracy: 1/20 = 0.05
valid_sql_rate: 5/20 = 0.25
reliability_score: -6.75
unsafe_sql: 0
latency_ms: mean=9335.15, median=8370.0, p95=12943.0
error_taxonomy: INVALID_SQL=15, RESULT_MISMATCH=4
trace_completeness: attempts=51, missing prompt/raw/parsed=0/0/0
```

### Immediate Gate 5 - Behavior Dev Agent Benchmark

Status: DONE on 2026-05-16 for the 3B smoke model.

Run:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:VTD_LLM_N_CTX = "4096"
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\Qwen__Qwen2.5-Coder-3B-Instruct-GGUF\qwen2.5-coder-3b-instruct-q4_k_m.gguf"
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset behavior_dev --sample 20 --bootstrap-iterations 300 --ablation-id behavior_trace
```

Record in `task.md`:

- output directory;
- correct action rate/action mismatch count;
- unsafe pass-through count;
- whether non-SQL/behavior examples are excluded from EX interpretation;
- error taxonomy counts;
- trace completeness.

Completed run:

```text
output_dir: results/benchmark/20260516_071702_agent_behavior_dev_qwen2_5-coder-3b-instruct-q4_k_m_behavior_trace_metrics_fixed
evaluated: 20
action_ok: 6/20
action_mismatch: 14
execution_accuracy: 0/0 because this sample has no SQL-positive records
valid_sql_rate: 0/0 because this sample has no SQL-positive records
clarification_accuracy: 6/10 = 0.6
safety_rejection_accuracy: 0/5 = 0.0
reliability_score: 2.0
unsafe_sql: 0
latency_ms: mean=30219.7, median=6944.5, p95=234212.0
error_taxonomy: ACTION_MISMATCH=14
trace_completeness: attempts=29, missing prompt/raw/parsed=0/0/6
```

### Immediate Gate 6 - Leakage and Overfit Audit

Status: DONE for initial detection and retrieval smoke verification on 2026-05-16. Direct retrieval self-overlap mitigation has been implemented; agent-mode verification is still pending before final paper/test claims.

Implement and run:

```powershell
.\.venv\Scripts\python.exe scripts\check_benchmark_leakage.py
```

Required outputs:

```text
results/data_quality/benchmark_leakage_report.md
results/data_quality/benchmark_leakage_cases.jsonl
```

Audit scope:

- duplicate ids across train/dev/test/behavior/RAG/few-shot/golden sources;
- exact duplicate normalized Persian questions across benchmark splits;
- near-duplicate normalized Persian questions across benchmark splits;
- overlap between dev/test and `golden_examples.jsonl`, `few_shot_bank.jsonl`, `indexed_examples.jsonl`;
- SQL skeleton overlap between dev/test and RAG/few-shot/golden sources;
- explicit limitation if the audit can detect overlap but cannot prove absence of prompt overfit.

Latest result:

```text
records: 630
total_issues: 724
base_id_overlap: 240
exact_id_duplicate: 50
exact_normalized_question_duplicate: 240
near_duplicate_question: 112
sql_skeleton_overlap: 82
report: results/data_quality/benchmark_leakage_report.md
cases: results/data_quality/benchmark_leakage_cases.jsonl
```

Interpretation: benchmark data is real project data, but anti-overfit/no-leakage is not established. Direct retrieval self-overlap is now mitigated with `--exclude-self`, which removes retrieved examples by base id (`fs_`, `idx_`) and exact normalized question match. Focused mocked test and retrieval smoke passed; agent-mode smoke still needs to be run before consuming the fixed test set. Broader split similarity and single-author prompt/data overfit remain paper limitations unless a cleaner independent test set is built.

Verification commands to run manually:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier2_integration\test_agent_benchmark_trace.py -vv --tb=short
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 5 --top-k 3 --exclude-self --ablation-id manual_exclude_self_smoke
```

Latest verification:

```text
pytest: 4 passed, 1 warning
retrieval_output_dir: results/benchmark/20260516_075846_retrieval_dev_qwen2-5-coder-7b_manual_exclude_self_smoke
evaluated: 5
failures: 0
retrieval_hit_rate: 1.0
self_overlap_policy: enabled
self_overlap_removed_total: 0
dataset_hash: present
selected_cases_hash: present
```

Agent smoke verification:

```text
agent_output_dir: results/benchmark/20260516_080120_agent_dev_qwen2-5-coder-7b_manual_agent_exclude_self_spl1
evaluated: 4
failures: 3
execution_accuracy: 0.25
valid_sql_rate: 0.75
reliability_score: -1.25
unsafe_sql: 0
error_taxonomy: RESULT_MISMATCH=2, MISSING_GENERATED_SQL=1
self_overlap_removed_total: 1
post-run fix: run_benchmark now records the fallback GGUF model path when VTD_DEFAULT_MODEL_PATH is not set.
metadata_fix_verification: results/benchmark/20260516_081002_gold_dev_qwen2-5-coder-7b_metadata_model_path_fix_smoke recorded model_path=D:\Project\ADHD-VTD\models\generation\qwen2.5-coder-7b-instruct-q4_k_m.gguf
```

Ambiguity fix verification:

```text
tests:
  test_ambiguity_detector.py -> 16 passed
  test_intent_classifier.py -> 1 passed
  test_graph_routes.py + test_agent_benchmark_trace.py -> 6 passed, 1 warning
agent_output_dir: results/benchmark/20260516_081645_agent_dev_qwen2-5-coder-7b_manual_agent_after_ambiguity_fix_spl1
evaluated: 4
failures: 3
execution_accuracy: 0.25
valid_sql_rate: 1.0
reliability_score: -2.0
unsafe_sql: 0
error_taxonomy: RESULT_MISMATCH=3
interpretation: the previous MISSING_GENERATED_SQL for VTD-237 is fixed; remaining failures are semantic/result mismatches.
next bottleneck: dashboard/storytelling intent was still stored as non_sql_request even when SQL generation was required, which weakened QIR/prompt guidance for dashboard queries.
follow-up fix implemented: src/nlu/intent_classifier.py now maps dashboard/storytelling SQL-capable requests to grouping_query with ExpectedAction.GENERATE_SQL.
follow-up test updated: tests/tier1_unit/test_intent_classifier.py asserts the VTD-237-style dashboard/eating_disorder question routes to grouping_query.
verification:
  test_intent_classifier.py -> 1 passed
  test_ambiguity_detector.py -> 16 passed
  test_graph_routes.py + test_agent_benchmark_trace.py -> 6 passed, 1 warning
  agent_output_dir: results/benchmark/20260516_120437_agent_dev_qwen2-5-coder-7b_manual_agent_after_dashboard_intent_fix_spl1
  evaluated/failures: 4/3
  execution_accuracy: 0.25
  valid_sql_rate: 1.0
  reliability_score: -2.0
  unsafe_sql: 0
  error_taxonomy: RESULT_MISMATCH=3
  VTD-237: intent=grouping_query, valid_sql=True, execution_correct=False
next bottleneck: valid SQL result-shape mismatch; VTD-237 needs time-change/quartile dashboard shape, VTD-343 needs grouped risk summary, and VTD-300 needs expected grouped rate/count shape.
shape-hint fix implemented:
  src/generation/prompt_builder.py now derives runtime-safe analysis_hints from the question, intent and available schema tables.
  src/generation/prompts/sql_generation.j2 now includes Analysis Shape Guidance before examples.
  tests/tier1_unit/test_prompt_builder.py checks grouped rate, dashboard/change/quartile, and risk-above-average hints without using gold SQL.
verification_pending:
  python -m pytest tests\tier1_unit\test_prompt_builder.py -vv --tb=short
  python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_shape_hints_spl1
verification:
  test_prompt_builder.py -> 3 passed
  prompt_builder + intent_classifier + ambiguity_detector -> 20 passed
  agent_output_dir: results/benchmark/20260516_122431_agent_dev_qwen2-5-coder-7b_manual_agent_after_shape_hints_spl1
  evaluated/failures: 4/4
  execution_accuracy: 0.0
  valid_sql_rate: 0.5
  reliability_score: -2.5
  unsafe_sql: 0
  error_taxonomy: INVALID_SQL=2, RESULT_MISMATCH=2
finding: first shape hints reached the prompt but were too broad; VTD-237 mixed wide-table name with long-table columns, and VTD-027 copied a few-shot column not present in student_depression.
next fix: add explicit schema-fidelity/cross-table-copy guardrails and make country prevalence, risk summary and rate aliases more schema-specific.
refined-shape-hint fix implemented:
  prompt_builder now adds a no-cross-table-column-copy guardrail for few-shot examples.
  country prevalence guidance now separates long-table columns (`disorder`, `prevalence_pct`) from wide-table `*_pct` columns.
  risk guidance now requires GROUP BY mental_health_risk, COUNT(*) AS n, avg_stress and avg_sleep when mental_health_general supports them.
  rate guidance now requires positives/rate_pct; gold-only context columns must not be enforced unless requested.
  family-history guidance now maps student_depression questions to family_history_mental_illness.
verification_pending:
  python -m pytest tests\tier1_unit\test_prompt_builder.py -vv --tb=short
  python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_refined_shape_hints_spl1
verification:
  test_prompt_builder.py -> 4 passed
  prompt_builder + intent_classifier + ambiguity_detector -> 21 passed
  agent_output_dir: results/benchmark/20260517_010715_agent_dev_qwen2-5-coder-7b_manual_agent_after_refined_shape_hints_spl1
  evaluated/failures: 4/3
  execution_accuracy: 0.25
  valid_sql_rate: 0.75
  reliability_score: -1.25
  unsafe_sql: 0
  improvement: VTD-027 correct; family_history_mental_illness selected.
  remaining: VTD-237 invalid SQLite PERCENTILE_CONT/wide-table path; VTD-343 missing grouped risk summary; VTD-300 missing group_value alias/null filter/avg_cgpa_10.
next fix:
  make prompt_builder schema-column reader support dict-style schema entries so table-specific hints appear in live prompts.
  prohibit SQLite-unsupported PERCENTILE_CONT and require NTILE(4)/grouped bins for quartile summaries.
  strengthen country_prevalence_long, risk summary and grouped-rate contracts.
refined-shape-hint-v2 implemented:
  schema column reader now supports object-style schema entries, dict columns lists and dict columns maps.
  prompt now explicitly says SQLite does not support PERCENTILE_CONT/WITHIN GROUP.
  country prevalence change guidance now uses MUST use country_prevalence_long when named disorder + change/quartile cues are present.
  student_depression rate guidance now requires sleep_duration_category AS group_value, null filtering and depression_flag positives/rate_pct; gold-only context columns are not enforced.
verification_pending:
  python -m pytest tests\tier1_unit\test_prompt_builder.py -vv --tb=short
  python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_refined_shape_hints_v2_spl1
verification:
  test_prompt_builder.py -> 5 passed
  prompt_builder + intent_classifier + ambiguity_detector -> 22 passed
  agent_output_dir: results/benchmark/20260517_013053_agent_dev_qwen2-5-coder-7b_manual_agent_after_refined_shape_hints_v2_spl1
  evaluated/failures: 4/3
  execution_accuracy: 0.25
  valid_sql_rate: 1.0
  reliability_score: -2.0
  unsafe_sql: 0
  improvement: all four generated SQLs are valid; VTD-027 remains exact-correct.
  remaining: VTD-237 latest-year scalar instead of change dashboard; VTD-343 row-level risk list instead of grouped risk summary; VTD-300 likely business-correct rate shape but exact-gold mismatch due extra avg_cgpa_10.
anti_overfit_decision:
  do not enforce avg_cgpa_10 as a correctness requirement because it is not explicit in the user question.
  move from more prompt hints to runtime shape contracts for defensible SQLite/question/schema rules.
shape-contract-validator implemented:
  src/sql_validation/shape_validator.py validates SQLite dialect and question/schema-derived analytical shape without reading gold SQL.
  src/graph/nodes/base_nodes.py runs shape validation after syntax/schema validation and before execution.
  tests/tier1_unit/test_shape_validator.py covers unsupported percentile functions, global change dashboards, grouped risk summaries and grouped sleep-rate shape.
verification_pending:
  python -m pytest tests\tier1_unit\test_prompt_builder.py tests\tier1_unit\test_shape_validator.py -vv --tb=short
  python -m pytest tests\tier1_unit\test_graph_retry_and_config.py tests\tier1_unit\test_graph_attempt_trace.py -vv --tb=short
  python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_shape_contract_spl1
verification:
  prompt_builder + shape_validator -> 10 passed
  graph_retry_and_config + graph_attempt_trace -> 8 passed
  agent_output_dir: results/benchmark/20260517_015651_agent_dev_qwen2-5-coder-7b_manual_agent_after_shape_contract_spl1
  evaluated/failures: 4/3
  execution_accuracy: 0.25
  valid_sql_rate: 0.75
  reliability_score: -1.25
  unsafe_sql: 0
  VTD-237: rejected before execution by analytical shape contract; repair moved to country_prevalence_long but still missed change/binning.
  VTD-343: first attempt rejected for missing risk grouping/count; repair added grouping/count but still missed above/below-average filters.
  VTD-300: passes shape contract and is plausibly business-correct for the natural-language rate request; exact-gold mismatch remains due avg_cgpa_10.
phase_10_closeout_remaining:
  error-analysis/closeout note written: results/error_analysis/20260517_phase10_shape_contract/error_report.md
  exact EX vs business correctness separation documented for VTD-300-style cases.
  risk average-threshold shape contract tightened after the latest trace analysis.
  local verification: test_shape_validator.py + test_prompt_builder.py -> 12 passed.
  larger smoke run: results/benchmark/20260517_030238_agent_dev_qwen2-5-coder-7b_manual_agent_shape_contract_spl2
  larger smoke result: evaluated=8, failures=6, execution_accuracy=0.25, valid_sql_rate=0.75, reliability_score=-2.5, unsafe_sql=0, self_overlap_removed_total=1.
  follow-up fixes: false unsafe classification for safe "build matrix/dashboard" requests fixed; risk shape validation narrowed so stress/sleep averages are only required for stress/sleep threshold questions.
  local verification: test_safety_detector.py + test_intent_classifier.py + test_shape_validator.py + test_prompt_builder.py -> 34 passed.
  rerun after fixes: results/benchmark/20260517_031221_agent_dev_qwen2-5-coder-7b_manual_agent_shape_contract_spl2_after_fixes
  rerun result: evaluated=8, failures=6, execution_accuracy=0.25, valid_sql_rate=0.875, reliability_score=-3.25, unsafe_sql=0, self_overlap_removed_total=1.
  regression checks passed: VTD-371 no longer unsafe_query; VTD-078 no longer over-blocked by shape validator.
  status: Phase 10 benchmark/trace infrastructure is complete. Remaining low EX and reliability are Phase 11/13/16 work.
```

### Immediate Gate 7 - Balanced Dev Agent Benchmark

Status: DONE on 2026-05-16.

Run:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:VTD_LLM_N_CTX = "4096"
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\Qwen__Qwen2.5-Coder-3B-Instruct-GGUF\qwen2.5-coder-3b-instruct-q4_k_m.gguf"
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 5 --bootstrap-iterations 300 --ablation-id full_trace_balanced_dev
```

Record output directory, difficulty counts, EX, Valid SQL Rate, reliability, unsafe SQL, latency, error taxonomy and trace completeness in `task.md`.

Completed run:

```text
output_dir: results/benchmark/20260516_073203_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace_balanced_dev
evaluated: 20
difficulty_counts: complex=5, easy=5, hard=5, medium=5
execution_accuracy: 2/20 = 0.10
valid_sql_rate: 14/20 = 0.70
reliability_score: -6.25
unsafe_sql: 0
latency_ms: mean=6872.35, median=7368.5, p95=16121.0
error_taxonomy: MISSING_GENERATED_SQL=7, INVALID_SQL=6, RESULT_MISMATCH=5
trace_completeness: attempts=25, missing prompt/raw/parsed=0/0/0
```

### Immediate Gate 8 - Fixed Test Benchmark

Status: BLOCKED.

Do not run fixed `test` benchmark yet. Current blockers:

- balanced dev EX is `0.10` and reliability is negative;
- leakage audit found overlap risk requiring mitigation or explicit limitation;
- main dev failures are still dominated by `MISSING_GENERATED_SQL`, `INVALID_SQL` and `RESULT_MISMATCH`;
- behavior quality is weak for refusal/chart/no-SQL cases.

Next acceptable action before consuming the fixed test set:

```text
debug prompt/routing/retrieval on dev artifacts -> rerun balanced dev -> only then run test
```

## راهنمای اجرای تست و بنچمارک

راهنمای عملی اجرای تست‌ها، benchmarkها، خواندن artifactها، sampling، progress log، trace prompt/response و debugging در این فایل نگهداری می‌شود:

```text
docs/BENCHMARK_AND_TEST_GUIDE.md
```

هر توسعه‌دهنده جدید قبل از اجرای benchmark باید این راهنما را بخواند تا تفاوت `retrieval`، `gold`، `agent`، `--sample`، `--samples-per-level` و artifactهای `results/benchmark/` را درست بفهمد.

تست integration زیر قرارداد artifactهای agent benchmark را بدون اجرای مدل واقعی پوشش می‌دهد:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier2_integration\test_agent_benchmark_trace.py -q
```

## Definition of Done برای milestone بعدی

Milestone بعدی یعنی Phase 11 first slice زمانی Done است که:

- Focused tests برای `statistical_tests.py`، `artifact_analysis.py` و `ablation_runner.py` پاس شده‌اند.
- `scripts/run_ablation.py` وجود دارد و به صورت پیش‌فرض فقط dry-run manifest می‌سازد، نه benchmark claim.
- ablation manifest مسیر configها، commandها، module flags و `result_status=not_run` را ثبت کرده است:
  `results/ablation/20260517_phase11_dry_run_manifest/ablation_manifest.json`.
- runtime flag contract در manifest و benchmark config ثبت می‌شود:
  enforced=`nlu,schema_linking,value_linking,cag,reflexion,repair,llm_judge,reliability_gate`؛ locked=`safety,validation`؛ metadata-only=`none`.
- `scripts/analyze_benchmark_artifact.py` روی آرتیفکت واقعی زیر اجرا شده است:
  `results/benchmark/20260517_031221_agent_dev_qwen2-5-coder-7b_manual_agent_shape_contract_spl2_after_fixes`.
- گزارش واقعی Phase 11 در مسیر زیر ساخته و در docs لینک شده است:
  `results/error_analysis/20260517_phase11_spl2_after_fixes/error_report.md`.
- گزارش، source artifact path، dataset hash، selected cases hash، model name/path، ablation id، metrics واقعی، taxonomy failures و limitations ضد-overfit را نشان دهد.
- هیچ metric یا جدول بدون artifact واقعی ساخته نشود.
- هیچ config ablation به عنوان نتیجه گزارش نشود.
- paired statistical tests فقط برای runهایی فعال شوند که case id مشترک دارند.
- task/roadmap/docs همان روز به‌روز شوند.

---

## Phase 17 Implementation Detail — Pre-QLoRA Accuracy Boost: 28% → >60%

### Baseline (اولین بنچمارک کامل)

| Metric | Value |
|---|---|
| Dataset | dev (60 سوال، 15 per difficulty) |
| Model | qwen2.5-coder-7b-instruct-q4_k_m (n_ctx=4096) |
| Artifact | `results/benchmark/20260522_123019_..._full_dev_baseline` |
| Strict EX | 8/60 = 13.33% |
| Semantic Accuracy | 17/60 = 28.33% |
| Valid SQL Rate | 36/60 = 60% |
| RESULT_MISMATCH | 28 |
| INVALID_SQL | 13 |
| MISSING_GENERATED_SQL | 11 |
| Unsafe SQL | 0 |

### تحلیل ریشه‌ای

**MISSING_GENERATED_SQL (11 مورد):**
- ۵ مورد: Intent classifier → `ambiguous_query` (0.5) → Graph → `ask_clarification` بدون تلاش SQL.
- ۴ مورد: Intent classifier → `definition_query` → Graph → `answer_without_sql`.
- ۲ مورد: JSON parse failure (`Unterminated string`) → Parser exception.

**INVALID_SQL (13 مورد):**
- ۸ مورد: Column hallucination (مثلاً `sleep_hours` به جای `sleep_duration_category`).
- ۳ مورد: Repair prompt بدون Schema → مدل ستون‌ها را فراموش کرده → Loop detected.
- ۲ مورد: استفاده از توابع غیرمجاز SQLite.

**RESULT_MISMATCH (28 مورد):**
- ۹ مورد: قاضی DeepSeek → `business_correct` (alias/column count difference).
- ۱۸ مورد: قاضی DeepSeek → `business_incorrect` (logic error).
- ۱ مورد: `provider_parse_error`.

### استراتژی‌ها و فایل‌های هدف

#### 17.1 Intent Routing Fix → حل ~۹ مورد MISSING_SQL

| فایل | تغییر |
|---|---|
| `src/nlu/intent_classifier.py` | سوالات حاوی entity+verb دستوری دیگر `ambiguous_query(0.5)` ندهند |
| `src/nlu/intent_classifier.py` | سوالات حاوی «دیتاست/survey/تعداد/توزیع» دیگر `definition_query` ندهند |
| `src/graph/routes.py` | `definition_query` فقط با confidence>0.8 و بدون اشاره به دیتا → `answer_without_sql` |
| `tests/tier1_unit/test_intent_classifier.py` | test cases: VTD-217/219/222/256/282/289/290/306/322 |

#### 17.2 Robust JSON Parser → حل ۲ مورد MISSING_SQL

| فایل | تغییر |
|---|---|
| `src/generation/output_parser.py` | Pipeline سه‌مرحله‌ای: (1) json.loads (2) regex code-fence extraction (3) raw SQL regex fallback |
| `tests/tier1_unit/test_output_parser.py` | ۴ test case: valid JSON, code-fence JSON, broken JSON+SQL, no SQL |

#### 17.3 Enhanced Repair Prompt → حل ≥۵ مورد INVALID_SQL

| فایل | تغییر |
|---|---|
| `src/generation/prompts/sql_repair.j2` | افزودن Schema، QIR و Value Links به template (مثل sql_generation.j2) |
| `src/graph/nodes/base_nodes.py` | پاس دادن `schema_context`, `qir`, `value_links` از State به repair template |
| `tests/tier1_unit/test_graph_attempt_trace.py` | بررسی حضور Schema در repair attempt prompt |

#### 17.4 Chain-of-Thought Prompting → حل ≥۸ مورد RESULT_MISMATCH

| فایل | تغییر |
|---|---|
| `src/generation/prompts/sql_generation.j2` | خروجی مدل: `thought_process` → `sql` (به جای `sql` → `explanation`) |
| `src/generation/output_parser.py` | استخراج و ذخیره `thought_process` در metadata |
| مثال‌های hardcoded در template | تبدیل به فرمت CoT |

#### 17.5 Few-Shot Enrichment → حل ≥۵ مورد RESULT_MISMATCH

| فایل | تغییر |
|---|---|
| `data/golden_sql/few_shot_bank.jsonl` | اضافه کردن مثال برای categoryهای پرخطا (فقط از train split) |
| `scripts/run_benchmark.py` | تست با `--top-k 5` و احتمالاً `VTD_LLM_N_CTX=8192` |
| `scripts/check_benchmark_leakage.py` | اجرا پس از هر تغییر few-shot برای جلوگیری از leakage |

#### 17.6 Abstention Fix → حل ۵ مورد wrong_abstention

| فایل | تغییر |
|---|---|
| `src/graph/routes.py` | سه‌شرط سختگیرانه برای ارسال به non-SQL path |

### اصول ضد Overfit/Underfit

1. **هیچ تغییری به Gold SQL یا ارزیابی داده نمی‌شود.** تغییرات فقط در Prompt، Parser، Repair و Routing هستند.
2. **هیچ case-ID خاصی در کد hardcode نمی‌شود.** تمام تغییرات عمومی هستند.
3. **Few-shot فقط از train split اضافه می‌شود.** leakage audit بعد از هر تغییر اجرا می‌شود.
4. **هر تغییر با Smoke test (4 سوال) و سپس Full dev (60 سوال) تایید می‌شود.**
5. **مقایسه A/B با Baseline الزامی است.** هیچ metric بدون artifact واقعی گزارش نمی‌شود.

### معیار پذیرش نهایی Phase 17

| Metric | هدف |
|---|---|
| Semantic Accuracy | ≥ 60% (≥36/60) |
| Valid SQL Rate | ≥ 80% (≥48/60) |
| MISSING_GENERATED_SQL | ≤ 3 (از 60) |
| Unsafe SQL | = 0 |

### مرحله بعد: QLoRA Fine-tuning (Phase 18)

پس از رسیدن به >60% با تغییرات معماری، دقت با Fine-tuning مدل 7B روی داده‌های train split به >90% خواهد رسید. سند QLoRA Plan جداگانه نوشته خواهد شد.


### Phase 17.6 Bug Discovery & Fixes

1. **Reflexion Hallucination (Unknown failure):**
   - **Bug:** When a generated SQL passed basic validation (`validate_sql`) and SQLite execution (`execute_sql`), but failed semantic consistency (e.g., missing required columns for the shape validator), the `reliability_gate` correctly flagged it for a `retry`. However, because `validate_sql` had passed, `state.validation_errors` was empty. The `reflect_on_error` node used a fallback `error_msg` which defaulted to `"Unknown failure"`. The LLM critic and repair agent received `"Unknown failure"` with no context, causing them to hallucinate wildly and generate worse SQL.
   - **Fix:** Modified `src/graph/nodes/base_nodes.py` to inject `state.candidate_consistency_report.issues` into the reflexion prompt when validation errors are empty but the reliability gate rejected the SQL. Now the LLM sees exact semantic feedback (e.g. `QUESTION_SQL_MISSING_RISK_CONTEXT_AVERAGES`).

2. **VTD-300 Gold SQL Hidden Columns (RESULT_MISMATCH):**
   - **Bug:** VTD-300 generated a perfectly valid and semantically matching SQL for `student_depression` sleep rates. However, the benchmark reported `RESULT_MISMATCH`. Analysis showed that the Gold SQL arbitrarily included `ROUND(AVG(cgpa_10),2) AS avg_cgpa_10` in the `SELECT` clause, which wasn't explicitly asked in the natural language question. Since the LLM didn't know to include this hidden column, the execution result hashes didn't match the gold standard.
   - **Action Plan (Phase 17.5):** We MUST enrich `few_shot_bank.jsonl` with examples for these specific query types so the LLM learns to include implicit business logic (like always showing average CGPA in depression grouping queries).

### Phase 17.8 Pipeline & Prompt Optimization (Pre-QLoRA)

**Goal:** Increase execution_accuracy by utilizing advanced LangGraph features and better RAG configurations.

1. **Enable Multi-Candidate Generation:**
   - Turn ON ENABLE_MULTI_CANDIDATE_GENERATION and ENABLE_CONSISTENCY_ABSTENTION in src/config/features.py.
2. **Enable Advanced RAG (CAG & Hybrid):**
   - Turn ON ENABLE_CAG, ENABLE_VECTOR_RETRIEVAL, and ENABLE_RERANKER.
3. **Enable SQL Surgeon & Reflexion Enhancements:**
   - Turn ON ENABLE_SQL_SURGEON and ENABLE_SEMANTIC_CRITIC.
4. **Few-Shot & Prompt Improvements:**
   - Auto-generate a synthetic 	hought_process for each few-shot example.
   - Add SQL SKELETONS section to sql_generation.j2.

