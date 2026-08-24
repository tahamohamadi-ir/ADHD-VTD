from __future__ import annotations

from src.runtime.caches import QuestionCache
from src.runtime.edge_pipeline import EdgePipeline


class _StubNormalizer:
    def normalize(self, text: str):
        return type("R", (), {"normalized_text": text.strip().lower()})()


class _StubIntentClassifier:
    def classify(self, text: str):
        return type("D", (), {"label": type("L", (), {"value": "data_query"})()})()


class _StubExecutor:
    def __init__(self, rows=None, error=None, raise_exc=None) -> None:
        self.rows = rows if rows is not None else [{"n": 7}]
        self.error = error
        self.raise_exc = raise_exc

    def execute_readonly(self, sql: str):
        if self.raise_exc:
            raise self.raise_exc
        return type("R", (), {"rows": self.rows, "error": self.error})()


def _pipeline(**kwargs) -> EdgePipeline:
    defaults = dict(
        normalizer=_StubNormalizer(),
        intent_classifier=_StubIntentClassifier(),
        executor=_StubExecutor(),
        sql_generator=lambda q: "SELECT COUNT(*) AS n FROM t;",
    )
    defaults.update(kwargs)
    return EdgePipeline(**defaults)


def test_refuses_non_select_sql():
    result = _pipeline(sql_generator=lambda q: "DROP TABLE t").run("سوال")

    assert result["action"] == "refuse_unsafe_sql"
    assert result["sql"] is None


def test_abstains_without_generator():
    pipeline = EdgePipeline()

    result = pipeline.run("سوال")

    assert result["action"] == "abstain_no_generator"


def test_fail_gracefully_on_executor_exception():
    result = _pipeline(executor=_StubExecutor(raise_exc=RuntimeError("db down"))).run("سوال")

    assert result["action"] == "fail_gracefully"
    assert "RuntimeError" in (result["execution_error"] or "")


def test_fail_gracefully_on_executor_error_field():
    result = _pipeline(executor=_StubExecutor(error="syntax")).run("سوال")

    assert result["action"] == "fail_gracefully"


def test_success_formats_and_reports_examples():
    class _Retriever:
        def retrieve(self, query, top_k=5):
            return [type("E", (), {"to_dict": lambda self: {"id": "x"}})()]

    result = _pipeline(retriever=_Retriever()).run("سوال")

    assert result["action"] == "format_answer"
    assert result["result"] == [{"n": 7}]
    assert result["retrieved_examples"] == 1
    assert result["cache_hit"] is False


def test_second_call_hits_question_cache():
    calls = {"n": 0}

    def generator(q: str) -> str:
        calls["n"] += 1
        return "SELECT 1"

    cache = QuestionCache()
    pipeline = _pipeline(sql_generator=generator, question_cache=cache)

    first = pipeline.run("تعداد")
    second = pipeline.run("  تعداد  ")

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["sql"] == "SELECT 1"
    assert calls["n"] == 1
