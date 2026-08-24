# PARS-SQL / VTD-Edge — تحلیل کامل پیاده‌سازی و چک‌لیست فازبندی‌شده

> **مبنای اسناد:** docs/00_INDEX.md تا docs/10_FULL_DEVELOPMENT_ROADMAP_ZERO_TO_SOTA.md  
> **تاریخ تحلیل:** 2026-05-11  
> **وضعیت کلی پروژه:** Phase 0 تکمیل‌شده — در آستانه Phase 1 / Milestone 1

---

## بخش اول — ممیزی کامل فایل‌ها (File Audit)

### وضعیت‌ها:
- ✅ **پیاده‌سازی شده** — کد واقعی دارد
- 🟡 **اسکفولد** — فایل وجود دارد اما محتوا خالی است (فقط یک `\r\n`)
- ❌ **وجود ندارد** — باید ساخته شود
- 📄 **داده** — فایل داده‌ای است، نه کد

---

## ۱. `src/config/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `paths.py` | ✅ | تمام مسیرها تعریف‌شده، `find_project_root()` پیاده |
| `settings.py` | ✅ | کانفیگ اصلی |
| `features.py` | ✅ | feature flags — CAG/LangGraph/Reflexion همه `False` |
| `__init__.py` | ✅ | |

---

## ۲. `src/core/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `types.py` | ✅ | BenchmarkCase, VTDState-like models, ReliabilityResult... |
| `enums.py` | ✅ | IntentLabel, SafetyLabel, ErrorType, AbstentionReason... |
| `contracts.py` | ✅ | Protocol interfaces برای LLM، Executor، Linker |
| `exceptions.py` | 🟡 | فایل خالی — هیچ exception تعریف نشده |
| `__init__.py` | ✅ | |

**نقص:** `exceptions.py` خالی است. VTDException، SchemaNotFoundError، UnsafeSQLError و... باید تعریف شوند.

---

## ۳. `src/nlu/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `persian_normalizer.py` | ✅ | NFKC، Arabic→Persian، ZWNJ، typo fix، colloquial |
| `number_normalizer.py` | ✅ | digit conversion، word-to-num، extract |
| `date_normalizer.py` | ✅ | Jalali month→Gregorian range، vague→clarification |
| `colloquial_mapper.py` | ✅ | Finglish، colloquial Persian، regex patterns |
| `intent_classifier.py` | ✅ | rule-based، safety+ambiguity check اول |
| `safety_intent_detector.py` | ✅ | forbidden SQL، Persian dangerous phrases، injection |
| `ambiguity_detector.py` | ✅ | generic patterns، ranking without metric |
| `term_extractor.py` | 🟡 | **فایل خالی** — باید پیاده شود |
| `__init__.py` | ✅ | |

**نقص‌های مهم:**
1. `term_extractor.py` خالی — token extraction برای schema linking هنوز نشده
2. `intent_classifier.py` فاقد `comparison_query`، `definition_query`، `raw_retrieval_query` 
3. `ambiguity_detector.py` فاقد بررسی "بهترین/بدترین بدون metric"، chart بدون measure/dimension
4. هیچ unit test در `tests/tier1_unit/` برای NLU وجود ندارد

---

## ۴. `src/schema/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `schema_loader.py` | ✅ | JSON loader |
| `schema_registry.py` | ✅ | has_table، has_column، ddl_context |
| `schema_graph.py` | ✅ | GraphEdge، find_direct_join |
| `schema_linker.py` | ✅ | alias→column، glossary، metric، direct mention، context builder |
| `value_linker.py` | ✅ | gender/flag/risk/disorder manual aliases، value dict fuzzy match |
| `join_path_finder.py` | ✅ | فایل وجود دارد |
| `business_rules.py` | ✅ | فایل وجود دارد |
| `__init__.py` | ✅ | |

**نقص‌های مهم:**
1. `schema_linker.py` — فاقد **RapidFuzz** fuzzy matching (فقط substring match)
2. `schema_linker.py` — فاقد embedding fallback برای unresolved terms
3. `schema_linker.py` — `unresolved_terms` همیشه `[]` برمی‌گرداند (پیاده نشده)
4. `concept_registry.py` — **وجود ندارد** (doc مشخص کرده باید باشد)
5. `query_planner.py` — **وجود ندارد** (QIR builder باید اینجا باشد)
6. هیچ unit test برای schema linking در tier1 نیست

---

## ۵. `src/db/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `sqlite_connection.py` | ✅ | read-only URI، context manager |
| `schema_inspector.py` | ✅ | table/column/FK extractor از DB |
| `read_only_executor.py` | ✅ | safety check، execute، row limit، hash |
| `result_serializer.py` | ✅ | serialize rows + hash |
| `__init__.py` | ✅ | |

**نقص‌های مهم:**
1. `read_only_executor.py` — timeout تنظیم‌شده اما فاقد `LIMIT` auto-injection برای raw retrieval
2. فاقد `join_validator` integration با executor
3. فاقد dry-run execution (execution برای validation)

---

## ۶. `src/sql_validation/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `syntax_validator.py` | ✅ | sqlglot parse، single statement |
| `safety_validator.py` | ✅ | forbidden keywords، SELECT-only، COUNT(*) allowed، CTE safe |
| `schema_validator.py` | ✅ | table/column existence، old-table detection |
| `semantic_validator.py` | ✅ | lightweight — expected_tables/columns check |
| `sql_rewriter.py` | ✅ | فایل وجود دارد |
| `validation_result.py` | ✅ | ValidationIssue، ValidationResult |
| `__init__.py` | ✅ | |

**نقص‌های مهم:**
1. `semantic_validator.py` — خیلی سطحی: فقط string-match بدون AST
2. `sql_rewriter.py` — بررسی نشده، احتمالاً stub
3. فاقد `join_validator.py` (مستقل)
4. فاقد `aggregation_validator.py` (مستقل)
5. فاقد `reliability_gate.py` (doc مشخص کرده)
6. فاقد `type_validator.py`
7. `QIR alignment check` — پیاده نشده
8. هیچ unit test برای validators در tier1 نیست

---

## ۷. `src/generation/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `llm_engine.py` | 🟡 | **خالی** |
| `local_llm.py` | 🟡 | **خالی** |
| `prompt_builder.py` | 🟡 | **خالی** |
| `output_parser.py` | 🟡 | **خالی** |
| `prompts/sql_generation.j2` | ✅ | template پایه وجود دارد |
| `prompts/sql_repair.j2` | ✅ | template پایه |
| `prompts/clarification.j2` | ✅ | template پایه |
| `prompts/answer_generation.j2` | ✅ | template پایه |
| `__init__.py` | ✅ | |

**نقص:** کل لایه generation پیاده نشده — مهم‌ترین نقص فعلی.

---

## ۸. `src/retrieval/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `embedding_model.py` | 🟡 | **خالی** |
| `chroma_store.py` | 🟡 | **خالی** |
| `bm25_index.py` | 🟡 | **خالی** |
| `hybrid_retriever.py` | 🟡 | **خالی** |
| `reranker.py` | 🟡 | **خالی** |
| `context_builder.py` | 🟡 | **خالی** |
| `retrieval_scorer.py` | 🟡 | **خالی** |
| `__init__.py` | ✅ | |

**نقص:** کل لایه retrieval/CAG پیاده نشده. (طبق roadmap این درست است — بعد از LLM baseline)

---

## ۹. `src/reflexion/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `critic.py` | 🟡 | **خالی** |
| `repair_planner.py` | 🟡 | **خالی** |
| `transition_memory.py` | 🟡 | **خالی** |
| `error_taxonomy.py` | 🟡 | **خالی** |
| `retry_policy.py` | 🟡 | **خالی** |
| `__init__.py` | ✅ | |

**نقص:** کل لایه reflexion پیاده نشده. (طبق roadmap این درست است — Phase 9)

---

## ۱۰. `src/graph/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `state.py` | 🟡 | **خالی** |
| `workflow.py` | 🟡 | **خالی** |
| `routes.py` | 🟡 | **خالی** |
| `checkpoints.py` | 🟡 | **خالی** |
| `nodes/*.py` (11 فایل) | 🟡 | **همه خالی** |
| `__init__.py` | ✅ | |

**نقص:** کل لایه LangGraph پیاده نشده. (طبق roadmap این درست است — Phase 8)

---

## ۱۱. `src/output/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `answer_formatter.py` | 🟡 | **خالی** |
| `chart_recommender.py` | 🟡 | **خالی** |
| `narrative_generator.py` | 🟡 | **خالی** |
| `explanation_builder.py` | 🟡 | **خالی** |
| `__init__.py` | ✅ | |

**نقص:** کل لایه output پیاده نشده.

---

## ۱۲. `src/evaluation/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `metrics.py` | ✅ | EX، valid_sql_rate، schema_linking، safety، abstention، robustness |
| `benchmark_runner.py` | ✅ | run_benchmark، phase0_identity_benchmark |
| `reliability_metrics.py` | ✅ | ReliabilityScore |
| `dataset_loader.py` | ✅ | load 400/500/special datasets |
| `error_analyzer.py` | ✅ | error categorization |
| `gold_sql_runner.py` | ✅ | gold SQL executor |
| `ablation_runner.py` | ✅ | ablation runner |
| `report_generator.py` | ✅ | report generation |
| `human_agreement.py` | ✅ | Cohen's Kappa stub |
| `phase0_audit.py` | ✅ | Phase 0 audit |
| `__init__.py` | ✅ | |

**نقص‌های مهم:**
1. `robustness_runner.py` — **وجود ندارد** (doc آن را ذکر کرده)
2. `schema_linking_metrics.py` — **وجود ندارد** (برای retrieval eval)
3. `statistical_tests.py` — **وجود ندارد** (Phase 11)
4. هیچ benchmark config واقعی در `benchmark/configs/` نیست

---

## ۱۳. `src/utils/`

| فایل | وضعیت | توضیح |
|---|---|---|
| `hashing.py` | 🟡 | **خالی** |
| `jsonl.py` | 🟡 | **خالی** |
| `logging.py` | 🟡 | **خالی** |
| `timing.py` | 🟡 | **خالی** |
| `__init__.py` | ✅ | |

**نقص:** کل utils خالی. در عوض result_serializer از db module hashing انجام می‌دهد.

---

## ۱۴. `data/` — آرتیفکت‌های داده

| فایل | وضعیت | توضیح |
|---|---|---|
| `data/db/vtd_health_research_v1.db` | ✅ | ~10MB، باز شده |
| `data/db/vtd_health_research_schema.sql` | ✅ | |
| `data/schema/schema_snapshot.json` | ✅ | |
| `data/schema/schema_snapshot.generated.json` | ✅ | |
| `data/schema/schema_graph.json` | ✅ | |
| `data/schema/column_aliases.fa.json` | ✅ | |
| `data/schema/business_glossary.fa.json` | ✅ | |
| `data/schema/metric_definitions.json` | ✅ | |
| `data/schema/value_dictionary.generated.json` | ✅ | ~71KB |
| `data/questions/full/vtd_total_500_dataset_package.json` | ✅ | |
| `data/questions/full/vtd_question_sql_400_merged_validated.json` | ✅ | |
| `data/questions/full/vtd_question_sql_140_colloquial_additions_validated.json` | ✅ | |
| `data/questions/special/vtd_evaluation_special_100.json` | ✅ | |
| `data/golden_sql/golden_examples.jsonl` | ✅ | ~2KB (کم!) |
| `data/golden_sql/few_shot_bank.jsonl` | ✅ | ~2KB (کم!) |
| `data/rag/indexed_examples.jsonl` | ✅ | ~2KB (کم!) |
| `data/rag/bm25/` | ❌ | BM25 index ساخته نشده |
| `data/rag/chroma/` | ❌ | Chroma index ساخته نشده |
| `data/questions/audit/phase0_50q_audit_cases.json` | ❌ | باید ساخته شود |
| `data/questions/train/` `dev/` `test/` | ❌ | split انجام نشده |
| `data/audit/phase0_50q_audit.csv` | ❌ | باید ساخته شود |

---

## ۱۵. `scripts/`

| فایل | وضعیت |
|---|---|
| `_bootstrap_path.py` | ✅ |
| `smoke_test_environment.py` | ✅ |
| `phase0_freeze_schema.py` | ✅ |
| `phase0_validate_gold_sql.py` | ✅ |
| `phase0_run_50q_manual_audit.py` | ✅ |
| `phase0_select_50q_audit_cases.py` | ✅ |
| `phase0_validate_semantic_metadata.py` | ✅ |
| `phase0_build_value_dictionary.py` | ✅ |
| `phase0_generate_audit_report.py` | ✅ |
| `patch_schema_linker_v2.py` | ✅ |
| `bootstrap_foundation.py` | ✅ |
| `milestone_1_run_baseline.py` | ✅ |
| `milestone_1_5_run_stress_test.py` | ✅ |
| `run_query.py` | ❌ | **وجود ندارد** — Phase 6 |
| `run_benchmark.py` | ❌ | **وجود ندارد** — Phase 10 |
| `build_rag_index.py` | ❌ | **وجود ندارد** — Phase 7 |
| `run_ablation.py` | ❌ | **وجود ندارد** — Phase 11 |
| `validate_dataset.py` | ❌ | **وجود ندارد** |
| `convert_dataset_to_jsonl.py` | ❌ | **وجود ندارد** |
| `compare_schema_snapshots.py` | ❌ | **وجود ندارد** |
| `export_schema_markdown.py` | ❌ | **وجود ندارد** |
| `export_graph_diagram.py` | ❌ | **وجود ندارد** |

---

## ۱۶. Root-level و مستندات

| فایل | وضعیت | توضیح |
|---|---|---|
| `README.md` | ✅ | Feature Decision Table دارد |
| `DATASET_CARD.md` | ❌ | **وجود ندارد** (فقط draft در docs/) |
| `.env.example` | ✅ | |
| `requirements.txt` | ✅ | |
| `pyproject.toml` | ✅ | |
| `main.py` | 🟡 | PyCharm default — هیچ کد واقعی ندارد |
| `docs/adr/` | ❌ | **وجود ندارد** |
| `docs/generated/` | ❌ | **وجود ندارد** |
| `benchmark/configs/` | ❌ | خالی (فقط .gitkeep) |
| `benchmark/protocols/` | ❌ | خالی |
| `experiments/configs/` | ✅ | 5 فایل YAML وجود دارد |
| `tests/tier1_unit/` | ❌ | فقط .gitkeep — هیچ unit test نیست |
| `tests/tier2_integration/` | ❌ | خالی |
| `tests/tier3_benchmark/` | ❌ | خالی |

---

## خلاصه وضعیت فعلی

| لایه | وضعیت |
|---|---|
| config | ✅ کامل |
| core (types/enums/contracts) | ✅ کامل — exceptions خالی |
| NLU (normalizer/intent/safety/ambiguity) | ✅ ~85% — term_extractor خالی |
| schema (linker/registry/graph/value_linker) | ✅ ~80% — fuzzy/embedding ندارد، concept_registry/query_planner نیست |
| sql_validation (syntax/safety/schema) | ✅ ~70% — join/agg/type validator مستقل ندارد |
| db (executor/inspector) | ✅ ~90% |
| evaluation (metrics/runner/reports) | ✅ ~75% — robustness_runner/stats test نیست |
| generation | 🟡 0% — همه خالی |
| retrieval | 🟡 0% — همه خالی |
| reflexion | 🟡 0% — همه خالی |
| graph (LangGraph) | 🟡 0% — همه خالی |
| output | 🟡 0% — همه خالی |
| utils | 🟡 0% — همه خالی |
| data artifacts | ✅ ~85% — BM25/Chroma index و splits نیست |
| tests | ❌ ~5% — عملاً هیچ unit test نیست |
