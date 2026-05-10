# 02 - LangGraph Workflow Specification

**Status:** Updated research-runtime workflow aligned with v2.3 reliability/abstention rules  
**Version:** v2.3 Execution-Ready alignment  
**Updated focus:** implementation-first, reliability-first, edge-aware, benchmark-auditable.


## 1. Why LangGraph

This project has loops, conditional routing, validation, retry, and persistent state. A linear LangChain chain is not ideal. LangGraph is better because the pipeline behaves like a state machine:

```text
normalize → classify → route → link schema → retrieve context → generate SQL → validate → repair/retry → execute → format
```

Each node should be deterministic when possible and LLM-based only when necessary.

---

## 2. Global State Contract

Use a Pydantic state object. Every node reads from and writes to this state.

```python
from pydantic import BaseModel, Field
from typing import Any, Literal

class SQLAttempt(BaseModel):
    iteration: int
    prompt_id: str | None = None
    sql: str | None = None
    parsed: bool = False
    validation_passed: bool = False
    execution_passed: bool = False
    error_type: str | None = None
    error_message: str | None = None
    repair_action: str | None = None
    latency_ms: int | None = None

class LinkedSchema(BaseModel):
    tables: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    join_paths: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    unresolved_terms: list[str] = Field(default_factory=list)

class QueryIR(BaseModel):
    task_type: str | None = None
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    filters: list[dict[str, Any]] = Field(default_factory=list)
    aggregation: str | None = None
    time_range: dict[str, str] | None = None
    expected_result_shape: str | None = None
    chart_intent: bool = False
    should_generate_sql: bool = True

class VTDState(BaseModel):
    trace_id: str
    raw_question: str
    normalized_question: str | None = None
    language: Literal["fa", "en", "mixed"] = "fa"

    intent: str | None = None
    intent_confidence: float = 0.0
    safety_label: str = "safe"
    ambiguity_score: float = 0.0
    needs_clarification: bool = False
    clarification_question: str | None = None

    qir: QueryIR | None = None
    linked_schema: LinkedSchema | None = None
    schema_context: str | None = None

    retrieved_examples: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_skeletons: list[dict[str, Any]] = Field(default_factory=list)
    prompt: str | None = None

    generated_sql: str | None = None
    attempts: list[SQLAttempt] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    critic_feedback: str | None = None
    deterministic_repair_applied: bool = False

    execution_result: list[dict[str, Any]] | None = None
    execution_error: str | None = None
    semantic_passed: bool = False

    final_answer: str | None = None
    chart_recommendation: dict[str, Any] | None = None
    benchmark_record: dict[str, Any] | None = None
```

---

## 3. Node List

| Node | Type | Uses LLM? | Responsibility |
|---|---:|---:|---|
| `initialize_trace` | deterministic | No | create trace ID and config metadata |
| `normalize_input` | deterministic | No | Persian cleanup, number/date normalization |
| `classify_intent` | hybrid | Optional | intent, ambiguity, safety route |
| `build_qir` | hybrid | Optional | create structured query plan |
| `route_pre_generation` | deterministic | No | reject, clarify, or continue |
| `link_schema` | deterministic/hybrid | No by default | map terms to tables, columns, joins |
| `retrieve_context` | deterministic retrieval | No | schema context + examples + skeletons |
| `build_prompt` | deterministic | No | create strict prompt |
| `generate_sql` | LLM | Yes | generate SQL candidate |
| `parse_llm_output` | deterministic | No | extract JSON/SQL safely |
| `validate_sql` | deterministic | No | sqlglot + schema + safety checks |
| `try_sql_surgeon` | deterministic | No | repair common SQL issues |
| `build_critic_feedback` | deterministic | No | make targeted repair prompt |
| `execute_sql` | deterministic | No | read-only execution |
| `semantic_result_check` | deterministic/hybrid | Optional | validate result matches QIR |
| `format_answer` | deterministic/LLM | Optional | Persian response, no hallucination |
| `recommend_chart` | deterministic | No | chart type and storytelling hint |
| `log_benchmark_record` | deterministic | No | store complete trace |

---

## 4. Routing Logic

### 4.1 Pre-Generation Route

```python
def route_pre_generation(state: VTDState) -> str:
    if state.safety_label == "unsafe":
        return "reject_safely"
    if state.needs_clarification:
        return "ask_clarification"
    if state.qir and not state.qir.should_generate_sql:
        return "explain_no_sql"
    if state.linked_schema and state.linked_schema.confidence < 0.45:
        return "ask_clarification"
    return "link_schema"
```

### 4.2 Validation Route

```python
def route_after_validation(state: VTDState) -> str:
    if not state.validation_errors:
        return "execute_sql"

    if state.retry_count >= state.max_retries:
        return "fail_gracefully"

    if can_surgeon_repair(state.validation_errors):
        return "try_sql_surgeon"

    return "build_critic_feedback"
```

### 4.3 Semantic Route

```python
def route_after_semantic_check(state: VTDState) -> str:
    if state.semantic_passed:
        return "format_answer"

    if state.retry_count >= state.max_retries:
        return "fail_gracefully"

    return "build_critic_feedback"
```

---

## 5. Graph Definition Skeleton

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(VTDState)

workflow.add_node("initialize_trace", initialize_trace)
workflow.add_node("normalize_input", normalize_input)
workflow.add_node("classify_intent", classify_intent)
workflow.add_node("build_qir", build_qir)
workflow.add_node("reject_safely", reject_safely)
workflow.add_node("ask_clarification", ask_clarification)
workflow.add_node("explain_no_sql", explain_no_sql)
workflow.add_node("link_schema", link_schema)
workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("build_prompt", build_prompt)
workflow.add_node("generate_sql", generate_sql)
workflow.add_node("parse_llm_output", parse_llm_output)
workflow.add_node("validate_sql", validate_sql)
workflow.add_node("try_sql_surgeon", try_sql_surgeon)
workflow.add_node("build_critic_feedback", build_critic_feedback)
workflow.add_node("execute_sql", execute_sql)
workflow.add_node("semantic_result_check", semantic_result_check)
workflow.add_node("format_answer", format_answer)
workflow.add_node("recommend_chart", recommend_chart)
workflow.add_node("log_benchmark_record", log_benchmark_record)
workflow.add_node("fail_gracefully", fail_gracefully)

workflow.set_entry_point("initialize_trace")
workflow.add_edge("initialize_trace", "normalize_input")
workflow.add_edge("normalize_input", "classify_intent")
workflow.add_edge("classify_intent", "build_qir")

workflow.add_conditional_edges(
    "build_qir",
    route_pre_generation,
    {
        "reject_safely": "reject_safely",
        "ask_clarification": "ask_clarification",
        "explain_no_sql": "explain_no_sql",
        "link_schema": "link_schema",
    },
)

workflow.add_edge("link_schema", "retrieve_context")
workflow.add_edge("retrieve_context", "build_prompt")
workflow.add_edge("build_prompt", "generate_sql")
workflow.add_edge("generate_sql", "parse_llm_output")
workflow.add_edge("parse_llm_output", "validate_sql")

workflow.add_conditional_edges(
    "validate_sql",
    route_after_validation,
    {
        "execute_sql": "execute_sql",
        "try_sql_surgeon": "try_sql_surgeon",
        "build_critic_feedback": "build_critic_feedback",
        "fail_gracefully": "fail_gracefully",
    },
)

workflow.add_edge("try_sql_surgeon", "validate_sql")
workflow.add_edge("build_critic_feedback", "generate_sql")
workflow.add_edge("execute_sql", "semantic_result_check")

workflow.add_conditional_edges(
    "semantic_result_check",
    route_after_semantic_check,
    {
        "format_answer": "format_answer",
        "build_critic_feedback": "build_critic_feedback",
        "fail_gracefully": "fail_gracefully",
    },
)

workflow.add_edge("format_answer", "recommend_chart")
workflow.add_edge("recommend_chart", "log_benchmark_record")
workflow.add_edge("log_benchmark_record", END)
workflow.add_edge("reject_safely", "log_benchmark_record")
workflow.add_edge("ask_clarification", "log_benchmark_record")
workflow.add_edge("explain_no_sql", "log_benchmark_record")
workflow.add_edge("fail_gracefully", "log_benchmark_record")

app = workflow.compile()
```

---

## 6. Retry Policy

Use a strict retry policy:

```text
max_retries = 3
retry 0 = initial generation
retry 1 = fix syntax/schema errors
retry 2 = fix semantic or join errors
retry 3 = conservative repair or clarification
```

Stop early if:

1. The exact same SQL appears twice.
2. The same error type appears three times.
3. SQL similarity to previous attempt is above 0.92 and the error persists.
4. The LLM returns non-JSON twice.
5. The query is discovered to be ambiguous.

---

## 7. Node Contracts

### `normalize_input`

Input:

```json
{"raw_question": "چندتا دانشجو افسردگی شدید دارن؟"}
```

Output updates:

```json
{
  "normalized_question": "چند تا دانشجو افسردگی شدید دارند؟",
  "language": "fa"
}
```

### `build_qir`

Output updates:

```json
{
  "qir": {
    "task_type": "count_query",
    "metrics": ["severe_depression"],
    "filters": [{"concept": "student"}],
    "aggregation": "COUNT",
    "expected_result_shape": "single_value"
  }
}
```

### `link_schema`

Output updates:

```json
{
  "linked_schema": {
    "tables": ["individuals_core", "student_metrics", "clinical_assessments"],
    "columns": ["individuals_core.user_id", "student_metrics.user_id", "clinical_assessments.phq9_score"],
    "join_paths": ["individuals_core.user_id = student_metrics.user_id", "individuals_core.user_id = clinical_assessments.user_id"],
    "confidence": 0.91
  }
}
```

### `validate_sql`

Output updates:

```json
{
  "validation_errors": [
    {
      "type": "SCHEMA_ERROR",
      "message": "Column gpa does not exist. Did you mean student_metrics.cgpa?",
      "repairable": true
    }
  ]
}
```

---

## 8. LangGraph Checkpointing

Use SQLite checkpointing for:

1. Debugging failed attempts.
2. Resuming long evaluations.
3. Storing traces for research.
4. Replaying individual failed benchmark cases.

Recommended checkpoint fields:

```text
trace_id
config_id
node_name
state_json
created_at
```

---

## 9. LLM-Friendly Implementation Prompt

You can give this instruction to an LLM when implementing:

```text
Implement the LangGraph workflow from 02_LANGGRAPH_WORKFLOW_SPEC.md.
Respect every node contract. Do not merge validation into generation. Do not let the LLM execute SQL. Use Pydantic models for state and return only state updates from each node. Add pytest unit tests for each deterministic node before implementing the LLM node.
```


---

## 10. v2.3 State Extensions for Reliability and Abstention

Add these fields to the state contract when implementing the full research runtime:

```python
class CandidateSQL(BaseModel):
    candidate_id: str
    sql: str | None = None
    confidence: float = 0.0
    used_tables: list[str] = Field(default_factory=list)
    used_columns: list[str] = Field(default_factory=list)
    validation_passed: bool = False
    execution_passed: bool = False
    semantic_passed: bool = False
    result_hash: str | None = None
    error_type: str | None = None
    error_message: str | None = None

class ReliabilityReport(BaseModel):
    should_abstain: bool = False
    abstention_reason: str | None = None
    reliability_score: float = 0.0
    candidate_consistency_score: float | None = None
    warning_message_fa: str | None = None

class VTDState(BaseModel):
    execution_mode: Literal["research", "edge"] = "research"
    candidate_sqls: list[CandidateSQL] = Field(default_factory=list)
    selected_candidate_id: str | None = None
    reliability: ReliabilityReport | None = None
    value_links: list[dict[str, Any]] = Field(default_factory=list)
```

### New Optional Nodes

| Node | Type | Responsibility |
|---|---|---|
| `retrieve_values` | deterministic/hybrid | map user-facing values to DB values |
| `generate_candidates` | LLM | generate N candidate SQLs when enabled |
| `check_candidate_consistency` | deterministic | compare candidates and decide select/abstain |
| `compute_reliability` | deterministic | compute reliability score and abstention decision |
| `error_disclosure` | deterministic | return warning when result is executed but not semantically reliable |

### Reliability Route

```python
def route_after_reliability(state: VTDState) -> str:
    if state.reliability and state.reliability.should_abstain:
        if state.reliability.warning_message_fa:
            return "error_disclosure"
        return "ask_clarification"
    return "format_answer"
```

### Edge Runtime Note

This file specifies the research runtime. A future edge runtime should reuse the same contracts but may replace LangGraph with a simpler state machine for lower overhead.
