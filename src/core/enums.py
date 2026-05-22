from __future__ import annotations

from enum import StrEnum


class IntentLabel(StrEnum):
    COUNT_QUERY = "count_query"
    AGGREGATION_QUERY = "aggregation_query"
    GROUPING_QUERY = "grouping_query"
    RANKING_QUERY = "ranking_query"
    TREND_QUERY = "trend_query"
    RATE_QUERY = "rate_query"
    RAW_RETRIEVAL_QUERY = "raw_retrieval_query"
    COMPARISON_QUERY = "comparison_query"
    DEFINITION_QUERY = "definition_query"
    CHART_QUERY = "chart_query"
    CLARIFICATION_RESPONSE = "clarification_response"
    AMBIGUOUS_QUERY = "ambiguous_query"
    OUT_OF_SCHEMA_QUERY = "out_of_schema_query"
    UNSAFE_QUERY = "unsafe_query"
    NON_SQL_REQUEST = "non_sql_request"
    UNKNOWN = "unknown"


class SafetyLabel(StrEnum):
    SAFE = "safe"
    UNSAFE_SQL = "unsafe_sql"
    PROMPT_INJECTION = "prompt_injection"
    PRIVACY_RISK = "privacy_risk"
    OUT_OF_SCOPE = "out_of_scope"
    UNKNOWN = "unknown"


class ExpectedAction(StrEnum):
    GENERATE_SQL = "generate_sql"
    ASK_CLARIFICATION = "ask_clarification"
    REFUSE_UNSAFE_SQL = "refuse_unsafe_sql"
    REFUSE_HALLUCINATION = "refuse_hallucination"
    REFUSE_SQL_EXPLAIN_SCHEMA_GAP = "refuse_sql_explain_schema_gap"
    ANSWER_WITHOUT_SQL = "answer_without_sql"
    ANSWER_CHART_RECOMMENDATION = "answer_chart_recommendation"
    ABSTAIN = "abstain"
    WARN_WITH_UNCERTAIN_RESULT = "warn_with_uncertain_result"


class EvaluationType(StrEnum):
    SQL_POSITIVE = "sql_positive"
    AMBIGUOUS = "ambiguous"
    OUT_OF_SCHEMA = "out_of_schema"
    NO_SQL = "no_sql"
    ADVERSARIAL = "adversarial"
    TYPO_SYNONYM = "typo_synonym"
    FINGLISH = "finglish"
    MULTI_TURN = "multi_turn"
    CHART_STORYTELLING = "chart_storytelling"
    JALALI_DATE = "jalali_date"
    ROBUSTNESS = "robustness"


class ErrorType(StrEnum):
    OUTPUT_FORMAT_ERROR = "OUTPUT_FORMAT_ERROR"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    SAFETY_ERROR = "SAFETY_ERROR"
    SCHEMA_TABLE_ERROR = "SCHEMA_TABLE_ERROR"
    SCHEMA_COLUMN_ERROR = "SCHEMA_COLUMN_ERROR"
    VALUE_LINKING_ERROR = "VALUE_LINKING_ERROR"
    JOIN_ERROR = "JOIN_ERROR"
    AGGREGATION_ERROR = "AGGREGATION_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    SEMANTIC_ERROR = "SEMANTIC_ERROR"
    EMPTY_RESULT_WARNING = "EMPTY_RESULT_WARNING"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    AMBIGUITY_ERROR = "AMBIGUITY_ERROR"
    INTENT_ERROR = "INTENT_ERROR"
    PERSIAN_NORMALIZATION_ERROR = "PERSIAN_NORMALIZATION_ERROR"
    DATE_NORMALIZATION_ERROR = "DATE_NORMALIZATION_ERROR"
    JALALI_MAPPING_ERROR = "JALALI_MAPPING_ERROR"
    COLLOQUIAL_MISMATCH_ERROR = "COLLOQUIAL_MISMATCH_ERROR"
    FINGLISH_RESOLUTION_ERROR = "FINGLISH_RESOLUTION_ERROR"
    CLINICAL_TERM_AMBIGUITY_ERROR = "CLINICAL_TERM_AMBIGUITY_ERROR"
    RAG_RETRIEVAL_ERROR = "RAG_RETRIEVAL_ERROR"
    REFLEXION_FAILURE = "REFLEXION_FAILURE"
    UNSUPPORTED_QUERY = "UNSUPPORTED_QUERY"
    UNKNOWN = "UNKNOWN"


class RuntimeMode(StrEnum):
    RESEARCH = "research"
    EDGE = "edge"
    BENCHMARK = "benchmark"
    DEBUG = "debug"


class MilestoneStage(StrEnum):
    PHASE_0_SCHEMA_FREEZE = "phase_0_schema_freeze"
    PHASE_0_50Q_AUDIT = "phase_0_50q_audit"
    MILESTONE_1_BASELINE = "milestone_1_baseline"
    MILESTONE_1_5_STRESS = "milestone_1_5_stress"
    PHASE_2_LOCAL_LLM = "phase_2_local_llm"
    PHASE_3_VALUE_LINKING = "phase_3_value_linking"
    PHASE_4_CAG = "phase_4_cag"
    PHASE_8_LANGGRAPH = "phase_8_langgraph"
    PHASE_9_REFLEXION = "phase_9_reflexion"


class AbstentionReason(StrEnum):
    LOW_CONFIDENCE = "low_confidence"
    AMBIGUOUS_QUESTION = "ambiguous_question"
    OUT_OF_SCHEMA = "out_of_schema"
    UNSAFE_REQUEST = "unsafe_request"
    INCONSISTENT_CANDIDATES = "inconsistent_candidates"
    VALIDATION_FAILED = "validation_failed"
    SEMANTIC_CRITIC_FAILED = "semantic_critic_failed"
    DATE_AMBIGUITY = "date_ambiguity"
    VALUE_LINKING_UNCERTAIN = "value_linking_uncertain"
    UNKNOWN = "unknown"
