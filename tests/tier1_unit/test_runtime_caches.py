from __future__ import annotations

import src.runtime.caches as caches_module
from src.runtime.caches import QuestionCache, SQLResultCache, normalize_key


def test_normalize_key_collapses_whitespace_and_lowercases():
    assert normalize_key("  تعداد   دانشجوها؟  ") == "تعداد دانشجوها؟"


def test_question_cache_hit_miss_and_stats():
    cache = QuestionCache(max_size=4, ttl_seconds=60)

    assert cache.get("q1") is None
    cache.set("q1", {"answer": 42})
    assert cache.get("q1") == {"answer": 42}
    assert cache.stats() == {"hits": 1, "misses": 1, "size": 1}


def test_question_cache_ttl_expiry(monkeypatch):
    clock = {"now": 100.0}
    monkeypatch.setattr(caches_module._TTLLRU, "_now", staticmethod(lambda: clock["now"]))
    cache = QuestionCache(max_size=2, ttl_seconds=10)
    cache.set("q", "v")

    assert cache.get("q") == "v"
    clock["now"] = 111.0
    assert cache.get("q") is None


def test_question_cache_evicts_lru_beyond_max_size():
    cache = QuestionCache(max_size=2, ttl_seconds=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")
    cache.set("c", 3)

    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert cache.stats()["size"] == 2


def test_sql_result_cache_key_is_stable_under_whitespace():
    key_one = SQLResultCache.sql_key("SELECT  1\n FROM t")
    key_two = SQLResultCache.sql_key("select 1 from t")

    assert key_one == key_two

    cache = SQLResultCache()
    cache.set_by_sql("SELECT 1 FROM t", [{"n": 1}])
    assert cache.get_by_sql("select  1 from t") == [{"n": 1}]
