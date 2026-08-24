from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from scripts.run_benchmark import agent_prediction, parse_max_retries_override, split_module_flags
from src.evaluation.ablation_flags import ablation_runtime_contract, normalize_feature_flags


class _CapturingWorkflow:
    def __init__(self) -> None:
        self.initial_state: dict | None = None

    def invoke(self, state: dict) -> dict:
        self.initial_state = state
        return {
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "validation_errors": [],
            "execution_result": [{"n": 10}],
            "execution_error": None,
            "final_answer": "done",
            "intent": "count_query",
            "intent_confidence": 0.9,
            "retry_count": 0,
            "max_retries": state["max_retries"],
            "needs_clarification": False,
            "safety_label": "safe",
            "attempts": [],
        }


class _MatchingExecutor:
    def compare_results(self, _generated_sql: str, _gold_sql: str) -> dict:
        return {
            "match": True,
            "generated_hash": "generated-hash",
            "gold_hash": "gold-hash",
        }


def test_parse_max_retries_override_accepts_non_negative_integer_values():
    assert parse_max_retries_override({"max_retries": 1}) == 1
    assert parse_max_retries_override({"max_retries": "2"}) == 2
    assert parse_max_retries_override({"nlu": True}) is None


@pytest.mark.parametrize("value", [-1, True, "not-an-int"])
def test_parse_max_retries_override_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        parse_max_retries_override({"max_retries": value})


def test_agent_prediction_passes_max_retries_override_to_initial_state():
    workflow = _CapturingWorkflow()

    prediction = agent_prediction(
        {
            "id": "synthetic-case",
            "question": "count rows",
            "gold_sql": "SELECT COUNT(*) AS n FROM student_depression",
            "expected_action": "generate_sql",
        },
        workflow,
        _MatchingExecutor(),
        ablation_config={"repair": True, "reflexion": True},
        max_retries_override=1,
    )

    assert workflow.initial_state is not None
    assert workflow.initial_state["max_retries"] == 1
    assert prediction["max_retries"] == 1


def test_abstention_flag_is_reported_as_locked_runtime_policy():
    contract = ablation_runtime_contract({"abstention": True})

    assert contract["runtime_locked"]["abstention"] is True
    assert contract["unknown"] == {}
    assert contract["warnings"] == []


def test_runtime_parameters_survive_feature_normalization_without_module_flags():
    features = normalize_feature_flags(
        {
            "multi_candidate_generation": True,
            "multi_candidate_allowed_triggers": ["validation_failed", "complex_intent"],
            "multi_candidate_blocked_triggers": ["difficulty_hint"],
            "multi_candidate_extra_generation_budget_ms": 60000,
            "unknown_parameter": ["ignored"],
        }
    )
    contract = ablation_runtime_contract(features)
    enabled, disabled = split_module_flags(features)

    assert features["multi_candidate_allowed_triggers"] == [
        "validation_failed",
        "complex_intent",
    ]
    assert features["multi_candidate_blocked_triggers"] == ["difficulty_hint"]
    assert contract["runtime_parameters"]["multi_candidate_allowed_triggers"] == [
        "validation_failed",
        "complex_intent",
    ]
    assert contract["runtime_parameters"]["multi_candidate_blocked_triggers"] == ["difficulty_hint"]
    assert contract["runtime_parameters"]["multi_candidate_extra_generation_budget_ms"] == 60000
    assert contract["unknown"] == {}
    assert enabled == ["multi_candidate_generation"]
    assert disabled == []


@pytest.mark.parametrize(
    ("config_name", "adoption_enabled"),
    [
        ("phase7_promptdiverse_shadow_spl15_diagnostic.yaml", False),
        ("phase7_promptdiverse_adopt_spl15_diagnostic.yaml", True),
    ],
)
def test_phase7_spl15_candidate_diagnostic_configs_are_not_paper_metrics(
    config_name,
    adoption_enabled,
):
    config_path = Path("experiments") / "configs" / config_name
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    features = config["features"]
    reporting = config["reporting"]
    contract = ablation_runtime_contract(features)

    assert config["dataset"] == {"split": "positive400"}
    assert config["sampling"] == {"samples_per_level": 15}
    assert features["multi_candidate_generation"] is True
    assert features["multi_candidate_verifier"] is True
    assert features["multi_candidate_adoption"] is adoption_enabled
    assert features["deterministic_templates"] is False
    assert features["llm_judge"] is False
    assert features["max_retries"] == 0
    assert reporting["result_status"] == "diagnostic_only_not_paper_result"
    assert reporting["paper_metric_allowed"] is False
    assert contract["unknown"] == {}
    assert contract["runtime_parameters"]["max_retries"] == 0


@pytest.mark.parametrize(
    ("config_name", "adoption_enabled"),
    [
        ("phase7_promptdiverse_shadow_spl15_runtime_guarded_diagnostic.yaml", False),
        ("phase7_promptdiverse_adopt_spl15_runtime_guarded_diagnostic.yaml", True),
    ],
)
def test_phase7_runtime_guarded_candidate_configs_are_not_paper_metrics(
    config_name,
    adoption_enabled,
):
    config_path = Path("experiments") / "configs" / config_name
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    features = config["features"]
    normalized = normalize_feature_flags(features)
    contract = ablation_runtime_contract(normalized)

    assert config["dataset"] == {"split": "positive400"}
    assert config["sampling"] == {"samples_per_level": 15}
    assert normalized["multi_candidate_generation"] is True
    assert normalized["multi_candidate_verifier"] is True
    assert normalized["multi_candidate_adoption"] is adoption_enabled
    assert normalized["multi_candidate_allowed_triggers"] == [
        "complex_intent",
        "validation_failed",
        "missing_generated_sql",
        "execution_failed",
    ]
    assert normalized["multi_candidate_blocked_triggers"] == [
        "difficulty_hint",
        "complex_category",
        "low_intent_confidence",
    ]
    assert normalized["multi_candidate_extra_generation_budget_ms"] == 60000
    assert features["deterministic_templates"] is False
    assert features["llm_judge"] is False
    assert features["max_retries"] == 0
    assert config["reporting"]["result_status"] == "diagnostic_only_not_paper_result"
    assert config["reporting"]["paper_metric_allowed"] is False
    assert contract["unknown"] == {}
    assert contract["runtime_parameters"]["max_retries"] == 0
