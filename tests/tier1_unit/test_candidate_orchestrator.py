import json
from types import SimpleNamespace

from src.graph.nodes.candidate_helpers import candidate_adoption_id
from src.graph.nodes.candidate_orchestrator import generate_sql_candidates
from src.graph.state import VTDState


class _FakeLLM:
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls = 0
        self.prompts: list[str] = []

    def generate_json(self, prompt, **_kwargs):
        self.prompts.append(prompt)
        response = self.responses[self.calls]
        self.calls += 1
        return response


class _ConsistencyReport:
    def __init__(self, *, passed=True, selected_candidate_id="candidate_1"):
        self.passed = passed
        self.selected_candidate_id = selected_candidate_id

    def as_dict(self):
        return {
            "passed": self.passed,
            "selected_candidate_id": self.selected_candidate_id,
            "issues": [],
        }


class _VerificationReport:
    def __init__(self, candidates, *, action="select", selected_candidate_id="candidate_1"):
        self.action = action
        self.selected_candidate_id = selected_candidate_id
        self.candidates = candidates

    def as_dict(self):
        return {
            "action": self.action,
            "selected_candidate_id": self.selected_candidate_id,
            "issues": [],
            "latency_ms": 0,
        }


def _state(**updates):
    data = {
        "trace_id": "t",
        "raw_question": "q",
        "prompt": "base prompt",
        "ablation_config": {"multi_candidate_generation": True},
    }
    data.update(updates)
    return VTDState(**data)


def _candidate_prompt(base_prompt, prompt_variant):
    return f"{base_prompt}::{prompt_variant}"


def _inspect_candidate(**kwargs):
    candidate_id = kwargs["candidate_id"]
    sql = kwargs["sql"]
    score = 8.0 if candidate_id == "candidate_1" else 9.0
    return {
        "candidate_id": candidate_id,
        "sql": sql,
        "valid_sql": bool(sql),
        "execution_passed": bool(sql),
        "result_hash": "same",
        "metadata": {
            "prompt_variant": kwargs["prompt_variant"],
            "candidate_score": {"score": score},
        },
    }


def _base_kwargs(**overrides):
    data = {
        "clock": iter([0.0, 0.01, 0.02, 0.03, 0.04]).__next__,
        "max_tokens_fn": lambda: 128,
        "extra_generation_budget_ms_fn": lambda _config: None,
        "prompt_variant_fn": lambda index: "primary" if index == 0 else "variant",
        "candidate_prompt_fn": _candidate_prompt,
        "parse_json_fn": json.loads,
        "inspect_candidate_fn": _inspect_candidate,
        "consistency_candidate_factory": lambda **kwargs: SimpleNamespace(**kwargs),
        "analyze_consistency_fn": lambda _candidates: _ConsistencyReport(
            passed=True,
            selected_candidate_id="candidate_1",
        ),
        "verify_candidates_fn": lambda candidates, **_kwargs: _VerificationReport(candidates),
        "adoption_id_fn": candidate_adoption_id,
    }
    data.update(overrides)
    return data


def test_generate_sql_candidates_records_review_only_candidates_by_default():
    llm = _FakeLLM(
        [
            '{"sql": "SELECT 1 AS n"}',
            '{"sql": "SELECT 1 AS n"}',
        ]
    )

    result = generate_sql_candidates(_state(), llm, 2, **_base_kwargs())

    assert llm.calls == 2
    assert result["generation_source"] == "llm_multi_candidate"
    assert len(result["candidate_sqls"]) == 2
    assert result["selected_candidate_id"] is None
    assert result["candidate_verification"]["action"] == "select"
    assert result["raw_model_response"] == llm.responses[0]
    assert llm.prompts == ["base prompt::primary", "base prompt::variant"]


def test_generate_sql_candidates_respects_extra_generation_budget():
    llm = _FakeLLM(
        [
            '{"sql": "SELECT 1 AS n"}',
            '{"sql": "SELECT 2 AS n"}',
        ]
    )
    clock = iter([0.0, 0.2, 0.2]).__next__

    result = generate_sql_candidates(
        _state(ablation_config={"multi_candidate_extra_generation_budget_ms": 100}),
        llm,
        2,
        **_base_kwargs(
            clock=clock,
            extra_generation_budget_ms_fn=lambda _config: 100,
        ),
    )

    assert llm.calls == 1
    assert result["multi_candidate_generation_budget"] == {
        "configured_budget_ms": 100,
        "requested_candidate_count": 2,
        "generated_candidate_count": 1,
        "budget_exhausted": True,
    }


def test_generate_sql_candidates_adopts_non_primary_when_verifier_selects_improvement():
    llm = _FakeLLM(
        [
            '{"sql": "SELECT 1 AS n"}',
            '{"sql": "SELECT 2 AS n"}',
        ]
    )

    result = generate_sql_candidates(
        _state(ablation_config={"multi_candidate_adoption": True}),
        llm,
        2,
        **_base_kwargs(
            analyze_consistency_fn=lambda _candidates: _ConsistencyReport(
                passed=True,
                selected_candidate_id="candidate_2",
            ),
            verify_candidates_fn=lambda candidates, **_kwargs: _VerificationReport(
                candidates,
                action="select",
                selected_candidate_id="candidate_2",
            ),
        ),
    )

    assert result["selected_candidate_id"] == "candidate_2"
    assert result["raw_model_response"] == llm.responses[1]
    assert result["parsed_payload"] == {"sql": "SELECT 2 AS n"}


def test_generate_sql_candidates_keeps_primary_when_verifier_requests_clarification():
    llm = _FakeLLM(
        [
            '{"sql": "SELECT 1 AS n"}',
            '{"sql": "SELECT 2 AS n"}',
        ]
    )

    result = generate_sql_candidates(
        _state(ablation_config={"multi_candidate_adoption": True}),
        llm,
        2,
        **_base_kwargs(
            analyze_consistency_fn=lambda _candidates: _ConsistencyReport(
                passed=True,
                selected_candidate_id="candidate_2",
            ),
            verify_candidates_fn=lambda candidates, **_kwargs: _VerificationReport(
                candidates,
                action="clarify",
                selected_candidate_id="candidate_2",
            ),
        ),
    )

    assert result["selected_candidate_id"] is None
    assert result["raw_model_response"] == llm.responses[0]
    assert result["candidate_verification"]["action"] == "clarify"


def test_generate_sql_candidates_can_run_without_verifier_but_keeps_policy_gate():
    llm = _FakeLLM(
        [
            '{"sql": "SELECT 1 AS n"}',
            '{"sql": "SELECT 2 AS n"}',
        ]
    )

    result = generate_sql_candidates(
        _state(
            ablation_config={
                "multi_candidate_adoption": True,
                "multi_candidate_verifier": False,
            }
        ),
        llm,
        2,
        **_base_kwargs(
            analyze_consistency_fn=lambda _candidates: _ConsistencyReport(
                passed=True,
                selected_candidate_id="candidate_2",
            ),
        ),
    )

    assert result["candidate_verification"] is None
    assert result["selected_candidate_id"] == "candidate_2"
    assert result["raw_model_response"] == llm.responses[1]
