from __future__ import annotations

from typing import Any

from src.graph.nodes.generation_router import route_sql_generation
from src.graph.state import VTDState


class _FakeLLM:
    def __init__(self, response: str = '{"sql":"SELECT 1"}') -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def generate_json(self, prompt: str, **kwargs: Any) -> str:
        self.calls.append((prompt, kwargs))
        return self.response


def _state(**updates: Any) -> VTDState:
    data: dict[str, Any] = {
        "trace_id": "trace",
        "raw_question": "count students",
        "prompt": "PROMPT",
    }
    data.update(updates)
    return VTDState(**data)


def test_route_sql_generation_returns_empty_when_prompt_missing() -> None:
    calls: list[str] = []

    result = route_sql_generation(
        _state(prompt=""),
        llm_factory=lambda: calls.append("llm") or _FakeLLM(),
        template_generator=lambda _question: calls.append("template") or None,
        multi_candidate_generator=lambda *_args: {"unexpected": True},
        can_generate_extra_candidates_fn=lambda _state: calls.append("can_extra") or True,
        clock=lambda: 0.0,
        max_tokens_fn=lambda: 123,
    )

    assert result == {"generated_sql": ""}
    assert calls == []


def test_route_sql_generation_uses_deterministic_template_without_llm() -> None:
    result = route_sql_generation(
        _state(ablation_config={"deterministic_templates": True}),
        llm_factory=lambda: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
        template_generator=lambda _question: '{"sql":"SELECT COUNT(*) AS n FROM t"}',
        multi_candidate_generator=lambda *_args: {"unexpected": True},
        can_generate_extra_candidates_fn=lambda _state: True,
        clock=lambda: 0.0,
        max_tokens_fn=lambda: 123,
    )

    assert result == {
        "generated_sql": '{"sql":"SELECT COUNT(*) AS n FROM t"}',
        "raw_model_response": '{"sql":"SELECT COUNT(*) AS n FROM t"}',
        "generation_source": "deterministic_template",
        "generation_latency_ms": 0,
    }


def test_route_sql_generation_falls_back_to_llm_when_template_misses() -> None:
    llm = _FakeLLM('{"sql":"SELECT AVG(age) AS avg_age FROM student_depression"}')
    clock_values = iter([4.0, 4.125])

    result = route_sql_generation(
        _state(ablation_config={"deterministic_templates": True}),
        llm_factory=lambda: llm,
        template_generator=lambda _question: None,
        multi_candidate_generator=lambda *_args: {"unexpected": True},
        can_generate_extra_candidates_fn=lambda _state: False,
        clock=lambda: next(clock_values),
        max_tokens_fn=lambda: 256,
    )

    assert result["generated_sql"] == '{"sql":"SELECT AVG(age) AS avg_age FROM student_depression"}'
    assert result["raw_model_response"] == result["generated_sql"]
    assert result["generation_source"] == "llm"
    assert result["generation_latency_ms"] == 125
    assert llm.calls == [("PROMPT", {"enforce_json": True, "max_tokens": 256})]


def test_route_sql_generation_dispatches_multi_candidate_when_policy_allows() -> None:
    llm = _FakeLLM()
    captured: dict[str, Any] = {}

    def multi_candidate_generator(state: VTDState, passed_llm: Any, count: int) -> dict[str, Any]:
        captured["state"] = state
        captured["llm"] = passed_llm
        captured["count"] = count
        return {"generated_sql": "multi", "generation_source": "llm_multi_candidate"}

    state = _state(
        ablation_config={"multi_candidate_generation": True},
        multi_candidate_policy={"enabled": True, "candidate_count": 3},
    )

    result = route_sql_generation(
        state,
        llm_factory=lambda: llm,
        template_generator=lambda _question: None,
        multi_candidate_generator=multi_candidate_generator,
        can_generate_extra_candidates_fn=lambda _state: True,
        clock=lambda: 0.0,
        max_tokens_fn=lambda: 123,
    )

    assert result == {"generated_sql": "multi", "generation_source": "llm_multi_candidate"}
    assert captured == {"state": state, "llm": llm, "count": 3}
    assert llm.calls == []


def test_route_sql_generation_keeps_single_llm_when_multi_candidate_policy_is_inactive() -> None:
    llm = _FakeLLM('{"sql":"SELECT COUNT(*) AS n FROM student_depression"}')
    clock_values = iter([1.0, 1.01])

    result = route_sql_generation(
        _state(
            ablation_config={"multi_candidate_generation": True},
            multi_candidate_policy={"enabled": False, "candidate_count": 3},
        ),
        llm_factory=lambda: llm,
        template_generator=lambda _question: None,
        multi_candidate_generator=lambda *_args: {"unexpected": True},
        can_generate_extra_candidates_fn=lambda _state: True,
        clock=lambda: next(clock_values),
        max_tokens_fn=lambda: 512,
    )

    assert result == {
        "generated_sql": '{"sql":"SELECT COUNT(*) AS n FROM student_depression"}',
        "raw_model_response": '{"sql":"SELECT COUNT(*) AS n FROM student_depression"}',
        "generation_source": "llm",
        "generation_latency_ms": 10,
    }
    assert llm.calls == [("PROMPT", {"enforce_json": True, "max_tokens": 512})]
