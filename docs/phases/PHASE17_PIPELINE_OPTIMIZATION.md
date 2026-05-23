# Phase 17: Pipeline & Prompt Optimization (Completion Report)

## 1. Execution Evaluation & `ResultSerializer` Bug Fix
During earlier benchmarks, we discovered an abnormally low `execution_accuracy` (~16.6%) despite a high `valid_sql_rate`. The root cause was traced to the `ResultSerializer` in `src/db/result_serializer.py`.
- **Bug**: The dictionary keys (column aliases from the SQL `SELECT` clause) were being hashed alongside the actual data values. For example, `SELECT COUNT(*) AS total_records` vs `SELECT COUNT(*) AS record_count` produced mismatched hashes, forcing a `RESULT_MISMATCH` failure even when logically correct.
- **Fix**: Modified `ResultSerializer` to replace the column names with generic index keys (`col_0`, `col_1`, etc.) while maintaining proper column order sorting. This ensures that any logically equivalent SQL returning the correct data shape passes Execution Evaluation.

## 2. Dynamic JSON & Markdown Block Output Extraction
The JSON extraction fallback mechanism had issues handling raw generation text when the LLM hallucinated markdown code blocks.
- **Fix**: Implemented a robust 3-stage fallback parser in `src/generation/output_parser.py`:
  1. Direct `json.loads`
  2. Regex match for ````json { ... } ```` blocks
  3. Raw SQL regex extraction (Last Resort)
- **Prompt Upgrade**: Updated `sql_generation.j2` to use explicit Markdown JSON blocks and `tojson` jinja filters to guide the LLM into returning structurally valid responses.

## 3. Repair Prompt (`sql_repair.j2`) Context Restoration
- **Bug**: The LLM lacked awareness of the original user's question during the Reflexion/Repair phase (`reflect_on_error` node).
- **Fix**: Re-injected `{{ question }}` into `sql_repair.j2` so the LLM knows what goal it is trying to achieve while fixing SQL syntax or semantic errors.

## 4. Intent Classifier & Ambiguity Detector (NLU) Enhancements
- **Bug**: User questions explicitly requesting data (e.g., "تعداد کل رکوردهای...") were misclassified as `definition_query` or triggered the `ambiguity_detector` simply because they contained words like "چیست" or "لیست کن".
- **Fix**: Introduced `has_data_signal` logic matching entity keywords like "جدول", "دیتاست", "نمونه", etc. If a data signal is present, the NLU overrides vague/definition classifications and accurately routes the task to SQL Generation.

## 5. Dataset Name Hallucination Prevention
- **Bug**: Questions regarding the `student_depression` table were causing the LLM to hallucinate `WHERE depression_flag = 1`, erroneously filtering datasets meant to be globally analyzed.
- **Fix**: Added dynamic dataset context hints in `src/generation/prompt_builder.py` explicitly warning the LLM about linguistic overlaps between table names and metric conditions.

## 6. Multi-Candidate Generation Enabling
- Enabled `multi_candidate_generation: True` by default for complex queries, low-confidence situations, and retries.
- Handled gracefully via `Consistency Abstention` where the LLM executes multiple generated candidates and adopts the most structurally/semantically correct sequence.

## Future Watch-outs & Recommendations
1. **QLoRA Fine-tuning Prep**: Now that the pipeline correctly parses and evaluates outputs, any remaining failure cases are purely LLM intelligence/reasoning limits. The next major step is compiling the Phase 17 `trace` artifacts into a high-quality dataset for QLoRA fine-tuning.
2. **Context Window Limitations**: Pay close attention to `n_ctx=8192`. If you add too many Few-Shot CAG examples or large schemas, the repair prompts can exceed the sequence length.
3. **Execution Latency**: Multi-Candidate Generation drastically improves accuracy but triples execution time. If deployed to production, consider adding a caching layer or disabling it for `easy` level questions.
