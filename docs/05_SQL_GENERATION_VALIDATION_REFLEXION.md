# 05 - SQL Generation, Validation, Reflexion, and Safe Execution

**Status:** Updated with v2.3 multi-candidate consistency, abstention, and error disclosure  
**Version:** v2.3 Execution-Ready alignment  
**Updated focus:** implementation-first, reliability-first, edge-aware, benchmark-auditable.


## 1. Core Principle

The LLM only generates **candidate SQL**. It does not decide correctness, safety, or executability.

Treat every generated SQL query as untrusted input.

---

## 2. SQL Generation Contract

The LLM should return strict JSON:

```json
{
  "sql": "SELECT ...",
  "confidence": 0.0,
  "assumptions": [],
  "used_tables": [],
  "used_columns": [],
  "result_shape": "single_value | table | time_series | ranking",
  "needs_clarification": false,
  "clarification_question": null
}
```

Never rely only on code blocks.

---

## 3. Recommended Generation Parameters

For local Text-to-SQL generation:

```text
temperature: 0.0 - 0.2
top_p: 0.8 - 0.95
max_tokens: 512 - 1024
repeat_penalty: low/moderate
stop sequences: optional, depends on model template
```

For repair prompts, use even lower randomness.

---

## 4. Prompt Rules

The system prompt must include:

1. SQLite dialect only.
2. Only `SELECT` queries.
3. Use only linked schema.
4. Do not invent columns.
5. Do not use markdown unless explicitly requested.
6. Return strict JSON.
7. If query is ambiguous, set `needs_clarification=true`.
8. If concept is outside schema, do not generate SQL.
9. Use joins only through known join paths.
10. For raw retrieval, include `LIMIT`.

---

## 5. Static Validation Stack

Validation order:

```text
1. Output JSON parse
2. SQL extraction
3. Single statement check
4. Forbidden keyword check
5. sqlglot parse
6. SELECT-only check
7. Table existence check
8. Column existence check
9. Join path validation
10. Aggregation and GROUP BY validation
11. Type compatibility validation
12. LIMIT validation for raw retrieval
13. QIR alignment check
```

---

## 6. Forbidden SQL

Reject immediately if SQL contains:

```text
INSERT
UPDATE
DELETE
DROP
ALTER
CREATE
TRUNCATE
REPLACE
MERGE
ATTACH
DETACH
PRAGMA
VACUUM
REINDEX
EXEC
CALL
```

Also reject:

- Multiple statements separated by semicolon.
- Comments that try prompt injection.
- Access to SQLite internal tables unless explicitly allowed.
- `SELECT *` for raw sensitive data unless allowed by config.

---

## 7. Validation Error Taxonomy

Use stable error categories for research.

| Error Type | Meaning | Example |
|---|---|---|
| `OUTPUT_FORMAT_ERROR` | invalid JSON or no SQL field | model returned prose |
| `SYNTAX_ERROR` | SQL cannot be parsed | missing FROM |
| `SAFETY_ERROR` | unsafe operation | DELETE |
| `SCHEMA_TABLE_ERROR` | unknown table | patients table invented |
| `SCHEMA_COLUMN_ERROR` | unknown column | gpa instead of cgpa |
| `JOIN_ERROR` | missing/wrong join | no user_id join |
| `AGGREGATION_ERROR` | invalid group/aggregate | dimension without GROUP BY |
| `TYPE_ERROR` | aggregation on text column | AVG(depression_diagnosis) |
| `SEMANTIC_ERROR` | SQL runs but answers wrong intent | SUM instead of AVG |
| `EMPTY_RESULT_WARNING` | result empty unexpectedly | wrong filter |
| `TIMEOUT_ERROR` | query too expensive | cross join |
| `AMBIGUITY_ERROR` | should have asked clarification | “best” without metric |

---

## 8. SQL Surgeon

The SQL Surgeon performs deterministic repair when safe.

Allowed repairs:

| Error | Repair |
|---|---|
| Missing LIMIT in raw retrieval | append `LIMIT 100` |
| `gpa` used but only `cgpa` exists | replace with `cgpa` if schema context confirms |
| Missing GROUP BY dimension | add GROUP BY if unambiguous |
| Wrong alias reference | fix alias if table is known |
| Extra markdown fences | strip fences |
| Trailing semicolon | remove if single statement |

Not allowed repairs:

1. Guessing unknown metric.
2. Creating join path not in schema graph.
3. Replacing a medical concept with another concept.
4. Changing aggregation semantics without QIR evidence.

---

## 9. Reflexion Loop

Algorithm:

```python
def reflexion_loop(state):
    while state.retry_count <= state.max_retries:
        validation = validate_sql(state.generated_sql, state.qir, state.linked_schema)

        if validation.ok:
            execution = execute_readonly(state.generated_sql)
            if execution.ok:
                semantic = semantic_check(execution.result, state.qir, state.generated_sql)
                if semantic.ok:
                    return success
                else:
                    error = semantic.error
            else:
                error = execution.error
        else:
            error = validation.error

        if is_infinite_loop(state.attempts, state.generated_sql, error):
            return fail("LOOP_DETECTED")

        if surgeon_can_fix(error):
            state.generated_sql = surgeon_fix(state.generated_sql, error)
        else:
            state.critic_feedback = build_targeted_feedback(error, state)
            state.generated_sql = llm_regenerate(state.critic_feedback)

        state.retry_count += 1

    return fail("MAX_RETRIES")
```

---

## 10. Anti-Loop Detection

Stop retry if:

```text
same SQL generated twice
same error type appears 3 times
SQL similarity > 0.92 compared to previous attempt and error unchanged
LLM returns invalid JSON twice
repair makes SQL worse
schema confidence is too low
```

SQL similarity can use normalized SQL string + RapidFuzz ratio.

---

## 11. Semantic Critic

Static SQL validity is not enough. Semantic validation checks whether the SQL matches the QIR.

Checks:

| QIR field | SQL requirement |
|---|---|
| `aggregation = COUNT` | SQL must contain COUNT |
| `metric = depression_score` | SQL must use phq9_score or approved depression rule |
| `dimension = gender` | SQL must SELECT/GROUP BY gender |
| `task_type = ranking_query` | SQL must ORDER BY and LIMIT |
| `expected_result_shape = single_value` | result should be one row/one column |
| `chart_intent = true` | result must have chartable dimensions |

---

## 12. Safe Execution

Use read-only SQLite:

```python
import sqlite3

class ReadOnlySQLiteExecutor:
    def __init__(self, db_path: str, timeout: float = 5.0):
        self.db_path = db_path
        self.timeout = timeout

    def execute(self, sql: str):
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=self.timeout)
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            return {
                "success": True,
                "columns": columns,
                "rows": [dict(zip(columns, row)) for row in rows]
            }
        except sqlite3.Error as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
```

---

## 13. Prompt Template: Initial Generation

```text
You are a precise SQLite Text-to-SQL generator.

You must generate SQL only from the linked schema.
Do not invent tables or columns.
Only SELECT statements are allowed.
Return strict JSON only.

### LINKED SCHEMA
{schema_context}

### BUSINESS RULES
{business_rules}

### QUERY INTERMEDIATE REPRESENTATION
{qir_json}

### GOLDEN EXAMPLES
{golden_examples}

### USER QUESTION
Raw: {raw_question}
Normalized: {normalized_question}

### OUTPUT JSON SCHEMA
{
  "sql": "...",
  "confidence": 0.0,
  "assumptions": [],
  "used_tables": [],
  "used_columns": [],
  "result_shape": "...",
  "needs_clarification": false,
  "clarification_question": null
}
```

---

## 14. Prompt Template: Repair

```text
The previous SQL candidate failed validation.

### ORIGINAL USER QUESTION
{raw_question}

### NORMALIZED QUESTION
{normalized_question}

### QUERY PLAN
{qir_json}

### LINKED SCHEMA
{schema_context}

### PREVIOUS SQL
{failed_sql}

### VALIDATION ERROR
Type: {error_type}
Message: {error_message}
Repair hint: {repair_hint}

Regenerate a corrected SQLite SELECT query.
Return strict JSON only.
Do not repeat the same SQL.
```

---

## 15. LLM-Friendly Implementation Prompt

```text
Implement SQL generation, validation, SQL Surgeon, Reflexion loop, and read-only execution from 05_SQL_GENERATION_VALIDATION_REFLEXION.md. Keep validation deterministic. The LLM only generates candidates and repairs. Add tests for every error category. Store every attempt in state for benchmark error analysis.
```


---

## 16. v2.3 Additions: Multi-Candidate Consistency and Error Disclosure

### 16.1 Multi-Candidate Generation Contract

When enabled, the generator returns multiple candidates:

```json
{
  "candidates": [
    {
      "candidate_id": "c1",
      "sql": "SELECT ...",
      "confidence": 0.74,
      "used_tables": [],
      "used_columns": [],
      "assumptions": []
    }
  ],
  "needs_clarification": false,
  "clarification_question": null
}
```

### 16.2 Consistency-Based Abstention

If candidates disagree on important structure, the system should abstain or ask clarification.

Disagreement signals:

1. different metric columns,
2. different base tables,
3. different join paths,
4. different aggregation type,
5. different result shape,
6. materially different execution results.

### 16.3 Error Disclosure Rule

If SQL executes but semantic critic fails, do not silently return the result.

Return a warning:

```text
این نتیجه با موفقیت اجرا شد، اما بررسی معنایی سیستم نشان می‌دهد ممکن است با نیت سؤال منطبق نباشد. لطفاً معیار یا فیلتر موردنظر را دقیق‌تر مشخص کنید.
```

This is different from silent abstention and is important in mental-health analytics where a wrong aggregate can still be harmful.

### 16.4 Reliability-Aware Final Output

Final output must include an internal reliability object:

```json
{
  "status": "answer | clarify | abstain | warn",
  "reliability_score": 0.0,
  "abstention_reason": null,
  "warning_message_fa": null,
  "sql": null,
  "answer_fa": null
}
```

### 16.5 Safety Is Stronger Than SQL Correctness

A syntactically valid SQL query must still be rejected if it violates:

- read-only policy,
- raw sensitive data policy,
- schema scope,
- low-confidence value linking,
- semantic critic constraints.
