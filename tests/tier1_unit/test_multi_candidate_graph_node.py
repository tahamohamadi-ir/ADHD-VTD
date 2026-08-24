from __future__ import annotations

from types import SimpleNamespace

from src.graph.nodes.base_nodes import plan_multi_candidate
from src.graph.nodes import base_nodes
from src.graph.state import VTDState


def test_plan_multi_candidate_keeps_simple_confident_question_single_candidate():
    state = VTDState(
        trace_id="trace",
        raw_question="How many students are depressed?",
        normalized_question="How many students are depressed?",
        intent="count_query",
        intent_confidence=0.95,
    )

    updates = plan_multi_candidate(state)

    assert updates["multi_candidate_policy"] == {
        "enabled": False,
        "candidate_count": 1,
        "reason": "simple_or_confident_query",
        "triggers": [],
    }


def test_plan_multi_candidate_triggers_after_validation_failure_retry():
    state = VTDState(
        trace_id="trace",
        raw_question="Show the depression rate by sleep category.",
        normalized_question="Show the depression rate by sleep category.",
        intent="rate_query",
        intent_confidence=0.9,
        retry_count=1,
        validation_errors=[{"message": "missing rate"}],
        generated_sql="SELECT sleep_duration_category, COUNT(*) AS n FROM student_depression GROUP BY sleep_duration_category",
    )

    updates = plan_multi_candidate(state)

    decision = updates["multi_candidate_policy"]
    assert decision["enabled"] is True
    assert decision["candidate_count"] == 2
    assert "retry_in_progress" in decision["triggers"]
    assert "validation_failed" in decision["triggers"]


class _FakeLLM:
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls = 0

    def generate_json(self, *_args, **_kwargs):
        response = self.responses[self.calls]
        self.calls += 1
        return response


def test_generate_sql_keeps_single_candidate_when_generation_flag_disabled(monkeypatch):
    llm = _FakeLLM(['{"sql": "SELECT COUNT(*) AS n FROM student_depression", "needs_clarification": false}'])
    monkeypatch.setattr(base_nodes, "_get_local_llm", lambda: llm)

    state = VTDState(
        trace_id="trace",
        raw_question="count students",
        prompt="prompt",
        ablation_config={"multi_candidate_generation": False},
        multi_candidate_policy={"enabled": True, "candidate_count": 2, "triggers": ["difficulty_hint"]},
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 1
    assert updates.get("candidate_sqls", []) == []
    assert updates.get("selected_candidate_id") is None


def test_generate_sql_records_candidates_but_does_not_adopt_by_default(monkeypatch):
    llm = _FakeLLM(
        [
            '{"sql": "SELECT COUNT(*) AS n FROM student_depression", "needs_clarification": false}',
            '{"sql": "SELECT COUNT(*) AS n FROM student_depression", "needs_clarification": false}',
        ]
    )
    monkeypatch.setattr(base_nodes, "_get_local_llm", lambda: llm)
    monkeypatch.setattr(
        base_nodes.ValidationPipeline,
        "validate",
        lambda _self, sql: SimpleNamespace(ok=True, normalized_sql=sql, issues=[]),
    )
    monkeypatch.setattr(
        base_nodes.SQLShapeValidator,
        "validate",
        lambda _self, *_args, **_kwargs: SimpleNamespace(ok=True, issues=[]),
    )
    monkeypatch.setattr(
        base_nodes.ReadOnlyExecutor,
        "execute_readonly",
        lambda _self, _sql: SimpleNamespace(
            ok=True,
            rows=[{"n": 1}],
            result_hash="same-hash",
            latency_ms=3,
            error=None,
        ),
    )

    state = VTDState(
        trace_id="trace",
        raw_question="count students",
        prompt="prompt",
        ablation_config={"multi_candidate_generation": True},
        multi_candidate_policy={"enabled": True, "candidate_count": 2, "triggers": ["difficulty_hint"]},
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 2
    assert len(updates["candidate_sqls"]) == 2
    assert updates["selected_candidate_id"] is None
    assert updates["candidate_consistency"]["passed"] is True
    assert updates["candidate_consistency"]["selected_candidate_id"] == "candidate_1"


def test_generate_sql_can_adopt_candidate_when_adoption_flag_enabled(monkeypatch):
    llm = _FakeLLM(
        [
            '{"sql": "SELECT COUNT(*) AS n FROM student_depression", "needs_clarification": false}',
            '{"sql": "SELECT COUNT(*) AS n FROM student_depression", "needs_clarification": false}',
        ]
    )
    monkeypatch.setattr(base_nodes, "_get_local_llm", lambda: llm)
    monkeypatch.setattr(
        base_nodes.ValidationPipeline,
        "validate",
        lambda _self, sql: SimpleNamespace(ok=True, normalized_sql=sql, issues=[]),
    )
    monkeypatch.setattr(
        base_nodes.SQLShapeValidator,
        "validate",
        lambda _self, *_args, **_kwargs: SimpleNamespace(ok=True, issues=[]),
    )
    monkeypatch.setattr(
        base_nodes.ReadOnlyExecutor,
        "execute_readonly",
        lambda _self, _sql: SimpleNamespace(
            ok=True,
            rows=[{"n": 1}],
            result_hash="same-hash",
            latency_ms=3,
            error=None,
        ),
    )

    state = VTDState(
        trace_id="trace",
        raw_question="count students",
        prompt="prompt",
        ablation_config={"multi_candidate_generation": True, "multi_candidate_adoption": True},
        multi_candidate_policy={"enabled": True, "candidate_count": 2, "triggers": ["difficulty_hint"]},
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 2
    assert updates["selected_candidate_id"] == "candidate_1"
    assert updates["candidate_consistency"]["passed"] is True


def test_generate_sql_does_not_add_candidates_on_retry_even_when_policy_enabled(monkeypatch):
    llm = _FakeLLM(['{"sql": "SELECT COUNT(*) AS n FROM student_depression", "needs_clarification": false}'])
    monkeypatch.setattr(base_nodes, "_get_local_llm", lambda: llm)

    state = VTDState(
        trace_id="trace",
        raw_question="count students",
        prompt="prompt",
        retry_count=1,
        validation_errors=[{"message": "previous invalid sql"}],
        ablation_config={"multi_candidate_generation": True},
        multi_candidate_policy={"enabled": True, "candidate_count": 2, "triggers": ["retry_in_progress"]},
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 1
    assert updates.get("candidate_sqls", []) == []
    assert updates.get("candidate_consistency") is None


def test_generate_sql_keeps_primary_as_review_only_when_no_candidate_is_viable(monkeypatch):
    llm = _FakeLLM(
        [
            '{"sql": "SELECT missing_column FROM student_depression", "needs_clarification": false}',
            '{"sql": "SELECT another_missing_column FROM student_depression", "needs_clarification": false}',
        ]
    )
    monkeypatch.setattr(base_nodes, "_get_local_llm", lambda: llm)
    monkeypatch.setattr(
        base_nodes.ValidationPipeline,
        "validate",
        lambda _self, _sql: SimpleNamespace(ok=False, normalized_sql=None, issues=["bad column"]),
    )

    state = VTDState(
        trace_id="trace",
        raw_question="hard query",
        prompt="prompt",
        ablation_config={"multi_candidate_generation": True},
        multi_candidate_policy={"enabled": True, "candidate_count": 2, "triggers": ["complex_intent"]},
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 2
    assert len(updates["candidate_sqls"]) == 2
    assert updates["selected_candidate_id"] is None
    assert updates["candidate_consistency"]["passed"] is False
    assert updates["generated_sql"] == llm.responses[0]
