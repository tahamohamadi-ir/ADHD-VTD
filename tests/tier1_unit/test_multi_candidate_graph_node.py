from __future__ import annotations

from types import SimpleNamespace

from src.graph.nodes.base_nodes import plan_multi_candidate
from src.graph.nodes import base_nodes
from src.graph.state import VTDState
from src.sql_validation.validation_result import ValidationIssue


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


def test_plan_multi_candidate_applies_trigger_allowlist_from_config():
    state = VTDState(
        trace_id="trace",
        raw_question="Show depression rate by gender.",
        normalized_question="Show depression rate by gender.",
        intent="rate_query",
        intent_confidence=0.9,
        qir={
            "intent": "rate_query",
            "metrics": ["depression_flag"],
            "dimensions": ["gender"],
            "filters": [],
            "expected_result_shape": "table",
        },
        ablation_config={
            "multi_candidate_allowed_triggers": ["validation_failed"],
        },
    )

    updates = plan_multi_candidate(state)

    assert updates["multi_candidate_policy"] == {
        "enabled": False,
        "candidate_count": 1,
        "reason": "triggers_filtered_by_policy",
        "triggers": [],
        "suppressed_triggers": ["complex_intent"],
    }


def test_plan_multi_candidate_keeps_allowed_validation_trigger_from_config():
    state = VTDState(
        trace_id="trace",
        raw_question="Show depression rate by sleep category.",
        normalized_question="Show depression rate by sleep category.",
        intent="rate_query",
        intent_confidence=0.9,
        retry_count=1,
        validation_errors=[{"message": "missing rate"}],
        generated_sql="SELECT missing_col FROM student_depression",
        ablation_config={
            "multi_candidate_allowed_triggers": ["validation_failed"],
        },
    )

    updates = plan_multi_candidate(state)

    assert updates["multi_candidate_policy"] == {
        "enabled": True,
        "candidate_count": 2,
        "reason": "adaptive_triggers_present",
        "triggers": ["validation_failed"],
        "suppressed_triggers": ["retry_in_progress"],
    }


class _FakeLLM:
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls = 0
        self.prompts: list[str] = []

    def generate_json(self, *args, **_kwargs):
        self.prompts.append(str(args[0]) if args else "")
        response = self.responses[self.calls]
        self.calls += 1
        return response


def test_generate_sql_keeps_single_candidate_when_generation_flag_disabled(monkeypatch):
    llm = _FakeLLM(
        ['{"sql": "SELECT COUNT(*) AS n FROM student_depression", "needs_clarification": false}']
    )
    monkeypatch.setattr(base_nodes, "_get_local_llm", lambda: llm)

    state = VTDState(
        trace_id="trace",
        raw_question="count students",
        prompt="prompt",
        ablation_config={"multi_candidate_generation": False},
        multi_candidate_policy={
            "enabled": True,
            "candidate_count": 2,
            "triggers": ["difficulty_hint"],
        },
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 1
    assert updates.get("candidate_sqls", []) == []
    assert updates.get("selected_candidate_id") is None


def test_generate_sql_requires_explicit_multi_candidate_generation_flag(monkeypatch):
    llm = _FakeLLM(
        ['{"sql": "SELECT COUNT(*) AS n FROM student_depression", "needs_clarification": false}']
    )
    monkeypatch.setattr(base_nodes, "_get_local_llm", lambda: llm)

    state = VTDState(
        trace_id="trace",
        raw_question="count students",
        prompt="prompt",
        ablation_config={},
        multi_candidate_policy={
            "enabled": True,
            "candidate_count": 2,
            "triggers": ["difficulty_hint"],
        },
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 1
    assert updates.get("candidate_sqls", []) == []
    assert updates.get("candidate_verification") is None


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
        multi_candidate_policy={
            "enabled": True,
            "candidate_count": 2,
            "triggers": ["difficulty_hint"],
        },
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 2
    assert len(updates["candidate_sqls"]) == 2
    assert updates["selected_candidate_id"] is None
    assert updates["candidate_consistency"]["passed"] is True
    assert updates["candidate_consistency"]["selected_candidate_id"] == "candidate_1"
    assert updates["candidate_verification"]["action"] == "select"
    assert updates["candidate_verification"]["selected_candidate_id"] == "candidate_1"
    assert updates["candidate_verification"]["latency_ms"] >= 0
    assert "candidate_score" in updates["candidate_sqls"][0]["metadata"]
    assert llm.prompts[0] == "prompt"
    assert llm.prompts[1] != "prompt"
    assert "Candidate verifier variant 2" in llm.prompts[1]
    assert updates["candidate_sqls"][0]["metadata"]["prompt_variant"] == "primary"
    assert (
        updates["candidate_sqls"][1]["metadata"]["prompt_variant"]
        == "variant_2_independent_equivalent"
    )


def test_generate_sql_stops_extra_candidates_when_runtime_budget_is_exhausted(monkeypatch):
    llm = _FakeLLM(
        [
            '{"sql": "SELECT COUNT(*) AS n FROM student_depression", "needs_clarification": false}',
            '{"sql": "SELECT AVG(age) AS avg_age FROM student_depression", "needs_clarification": false}',
        ]
    )
    clock = iter([0.0, 0.2, 0.2, 0.2, 0.2])
    monkeypatch.setattr(base_nodes.time, "perf_counter", lambda: next(clock))
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
        ablation_config={
            "multi_candidate_generation": True,
            "multi_candidate_extra_generation_budget_ms": 100,
        },
        multi_candidate_policy={
            "enabled": True,
            "candidate_count": 2,
            "triggers": ["complex_intent"],
        },
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 1
    assert len(updates["candidate_sqls"]) == 1
    assert updates["multi_candidate_generation_budget"] == {
        "configured_budget_ms": 100,
        "requested_candidate_count": 2,
        "generated_candidate_count": 1,
        "budget_exhausted": True,
    }
    assert updates["candidate_consistency"]["issues"][0]["code"] == "SINGLE_VIABLE_CANDIDATE"
    assert updates["candidate_verification"]["action"] == "select"


def test_generate_sql_does_not_adopt_primary_candidate_as_improvement(monkeypatch):
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
        multi_candidate_policy={
            "enabled": True,
            "candidate_count": 2,
            "triggers": ["difficulty_hint"],
        },
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 2
    assert updates["selected_candidate_id"] is None
    assert updates["candidate_consistency"]["passed"] is True
    assert updates["candidate_verification"]["selected_candidate_id"] == "candidate_1"


def test_generate_sql_adopts_non_primary_candidate_only_when_score_improves(monkeypatch):
    responses = [
        '{"sql": "SELECT COUNT(*) AS n FROM student_depression", "needs_clarification": false, "assumptions": ["primary"]}',
        '{"sql": "SELECT COUNT(*) AS n FROM student_depression", "needs_clarification": false, "assumptions": ["candidate_2"]}',
    ]
    llm = _FakeLLM(responses)
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

    class _FakeVerificationReport:
        action = "select"
        selected_candidate_id = "candidate_2"

        def __init__(self, candidates):
            self.candidates = [
                {
                    **candidates[0],
                    "metadata": {
                        **candidates[0]["metadata"],
                        "candidate_score": {"score": 8.0},
                    },
                },
                {
                    **candidates[1],
                    "metadata": {
                        **candidates[1]["metadata"],
                        "candidate_score": {"score": 9.0},
                    },
                },
            ]

        def as_dict(self):
            return {
                "action": self.action,
                "reason": "best_runtime_candidate",
                "selected_candidate_id": self.selected_candidate_id,
                "disagreement_high": False,
                "issues": [],
            }

    monkeypatch.setattr(
        base_nodes,
        "verify_sql_candidates",
        lambda candidates, **_kwargs: _FakeVerificationReport(candidates),
    )

    state = VTDState(
        trace_id="trace",
        raw_question="count students",
        prompt="prompt",
        ablation_config={"multi_candidate_generation": True, "multi_candidate_adoption": True},
        multi_candidate_policy={
            "enabled": True,
            "candidate_count": 2,
            "triggers": ["difficulty_hint"],
        },
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 2
    assert updates["selected_candidate_id"] == "candidate_2"
    assert updates["raw_model_response"] == responses[1]
    assert updates["candidate_verification"]["selected_candidate_id"] == "candidate_2"


def test_generate_sql_does_not_add_candidates_on_retry_even_when_policy_enabled(monkeypatch):
    llm = _FakeLLM(
        ['{"sql": "SELECT COUNT(*) AS n FROM student_depression", "needs_clarification": false}']
    )
    monkeypatch.setattr(base_nodes, "_get_local_llm", lambda: llm)

    state = VTDState(
        trace_id="trace",
        raw_question="count students",
        prompt="prompt",
        retry_count=1,
        validation_errors=[{"message": "previous invalid sql"}],
        ablation_config={"multi_candidate_generation": True},
        multi_candidate_policy={
            "enabled": True,
            "candidate_count": 2,
            "triggers": ["retry_in_progress"],
        },
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
        multi_candidate_policy={
            "enabled": True,
            "candidate_count": 2,
            "triggers": ["complex_intent"],
        },
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 2
    assert len(updates["candidate_sqls"]) == 2
    assert updates["selected_candidate_id"] is None
    assert updates["candidate_consistency"]["passed"] is False
    assert updates["candidate_verification"]["action"] == "clarify"
    assert updates["generated_sql"] == llm.responses[0]


def test_generate_sql_does_not_execute_unsafe_candidate(monkeypatch):
    llm = _FakeLLM(
        [
            '{"sql": "DROP TABLE student_depression", "needs_clarification": false}',
            '{"sql": "DELETE FROM student_depression", "needs_clarification": false}',
        ]
    )
    monkeypatch.setattr(base_nodes, "_get_local_llm", lambda: llm)
    monkeypatch.setattr(
        base_nodes.ValidationPipeline,
        "validate",
        lambda _self, _sql: SimpleNamespace(
            ok=False,
            normalized_sql=None,
            issues=[
                ValidationIssue(
                    "FORBIDDEN_KEYWORD",
                    "Forbidden SQL keyword.",
                )
            ],
        ),
    )

    execution_calls = {"count": 0}

    def _fail_if_executed(_self, _sql):
        execution_calls["count"] += 1
        raise AssertionError("Unsafe candidate should not be executed.")

    monkeypatch.setattr(base_nodes.ReadOnlyExecutor, "execute_readonly", _fail_if_executed)

    state = VTDState(
        trace_id="trace",
        raw_question="unsafe query",
        prompt="prompt",
        ablation_config={"multi_candidate_generation": True},
        multi_candidate_policy={
            "enabled": True,
            "candidate_count": 2,
            "triggers": ["difficulty_hint"],
        },
    )

    updates = base_nodes.generate_sql(state)

    assert llm.calls == 2
    assert execution_calls["count"] == 0
    assert updates["candidate_verification"]["action"] == "clarify"
    assert updates["candidate_sqls"][0]["metadata"]["candidate_score"]["unsafe_penalty"] == 1.0
