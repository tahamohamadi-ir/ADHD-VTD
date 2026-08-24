from __future__ import annotations

import time
from typing import Any, Callable

from src.runtime.caches import QuestionCache, SQLResultCache, normalize_key

_SAFE_SQL_PREFIXES = ("select", "with")


class EdgePipeline:
    """Lightweight deterministic fast-path pipeline (Phase 14 prototype).

    Reuses the same NLU/schema/retrieval/execution contracts as the LangGraph
    research runtime but without graph overhead. The SQL generator is injected,
    so the pipeline stays deterministic when no LLM is attached.
    """

    def __init__(
        self,
        *,
        normalizer: Any | None = None,
        intent_classifier: Any | None = None,
        schema_linker: Any | None = None,
        retriever: Any | None = None,
        executor: Any | None = None,
        sql_generator: Callable[[str], str] | None = None,
        question_cache: QuestionCache | None = None,
        result_cache: SQLResultCache | None = None,
    ) -> None:
        self._normalizer = normalizer
        self._intent_classifier = intent_classifier
        self._schema_linker = schema_linker
        self._retriever = retriever
        self._executor = executor
        self._sql_generator = sql_generator
        self._question_cache = question_cache
        self._result_cache = result_cache

    def _normalize(self, question: str) -> str:
        if self._normalizer is None:
            return question
        try:
            result = self._normalizer.normalize(question)
            return getattr(result, "normalized_text", None) or str(result) or question
        except Exception:
            return question

    def _classify_intent(self, normalized_question: str) -> str | None:
        if self._intent_classifier is None:
            return None
        try:
            decision = self._intent_classifier.classify(normalized_question)
        except Exception:
            return None
        label = getattr(decision, "label", None)
        if label is None and isinstance(decision, dict):
            label = decision.get("label")
        return str(getattr(label, "value", label)) if label is not None else None

    def _link_schema(self, normalized_question: str) -> dict[str, Any] | None:
        if self._schema_linker is None:
            return None
        try:
            linked = self._schema_linker.link(normalized_question)
            if isinstance(linked, dict):
                return linked
            dumped = getattr(linked, "model_dump", None)
            return dumped() if callable(dumped) else None
        except Exception:
            return None

    def _retrieve(self, normalized_question: str) -> list[dict[str, Any]]:
        if self._retriever is None:
            return []
        try:
            retrieved = self._retriever.retrieve(normalized_question, top_k=5)
            return [item.to_dict() for item in retrieved]
        except Exception:
            return []

    def run(self, question: str) -> dict[str, Any]:
        started = time.perf_counter()
        cache_key = normalize_key(question)
        if self._question_cache is not None:
            cached = self._question_cache.get(cache_key)
            if cached is not None:
                return {**cached, "cache_hit": True}

        payload = self._run_uncached(question, cache_key)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {**payload, "latency_ms": latency_ms}

    def _run_uncached(self, question: str, cache_key: str) -> dict[str, Any]:
        normalized_question = self._normalize(question)
        intent = self._classify_intent(normalized_question)

        if self._sql_generator is None:
            return {
                "action": "abstain_no_generator",
                "sql": None,
                "result": None,
                "cache_hit": False,
                "normalized_question": normalized_question,
                "intent": intent,
            }

        sql = str(self._sql_generator(question)).strip().rstrip(";")
        first_token = sql.split(" ", 1)[0].lower() if sql else ""
        if first_token not in _SAFE_SQL_PREFIXES:
            return {
                "action": "refuse_unsafe_sql",
                "sql": None,
                "result": None,
                "cache_hit": False,
            }

        schema_links = (
            self._link_schema(normalized_question) if intent not in {"definition_query"} else None
        )
        examples = self._retrieve(normalized_question)

        execution_error: str | None = None
        result_rows: Any = None
        if self._executor is not None:
            try:
                raw_result = self._executor.execute_readonly(sql)
            except Exception as exc:
                execution_error = f"{type(exc).__name__}: {exc}"
            else:
                error = getattr(raw_result, "error", None)
                if isinstance(raw_result, dict):
                    error = raw_result.get("error")
                    result_rows = raw_result.get("rows", raw_result.get("results"))
                else:
                    result_rows = getattr(raw_result, "rows", raw_result)
                execution_error = error if error else None

        action = "fail_gracefully" if execution_error else "format_answer"
        payload = {
            "action": action,
            "sql": sql,
            "result": result_rows,
            "execution_error": execution_error,
            "schema_links": schema_links,
            "retrieved_examples": len(examples),
            "cache_hit": False,
            "normalized_question": normalized_question,
            "intent": intent,
        }

        if action == "format_answer":
            if self._question_cache is not None:
                self._question_cache.set(cache_key, payload)
            if self._result_cache is not None and sql:
                self._result_cache.set_by_sql(sql, result_rows)
        return payload
