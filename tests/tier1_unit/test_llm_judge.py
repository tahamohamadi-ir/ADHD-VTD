from __future__ import annotations

import json
import http.client
from pathlib import Path

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl
from src.evaluation.llm_judge import (
    MockJudgeProvider,
    OpenRouterJudgeProvider,
    judge_benchmark_artifact,
    validate_judge_artifact,
)


def _write_artifact(root: Path) -> None:
    prefix = "20260519_test"
    write_json(
        root / f"{prefix}_summary.json",
        {
            "config": {
                "model_name": "mock-model",
                "dataset_hash": "dataset-hash",
                "selected_cases_hash": "selected-hash",
            },
            "dataset": {"total_evaluated": 3},
        },
    )
    predictions = [
        {
            "id": "exact",
            "ok": True,
            "execution_correct": True,
            "valid_sql": True,
            "generated_sql": "SELECT 1;",
            "gold_sql": "select 1",
        },
        {
            "id": "mismatch",
            "ok": False,
            "execution_correct": False,
            "valid_sql": True,
            "error": "RESULT_MISMATCH",
            "generated_sql": "SELECT 1",
            "gold_sql": "SELECT 2",
        },
        {
            "id": "invalid",
            "ok": False,
            "execution_correct": False,
            "valid_sql": False,
            "error": "INVALID_SQL",
            "generated_sql": "SELECT missing_column FROM table",
            "gold_sql": "SELECT 2",
        },
    ]
    write_jsonl(root / f"{prefix}_predictions.jsonl", predictions)
    write_jsonl(root / f"{prefix}_attempts.jsonl", [])
    write_jsonl(root / f"{prefix}_failures.jsonl", predictions[1:])


def _write_authoritative_judge_artifact(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    judgments = [
        {
            "case_id": "case-1",
            "provider": "openrouter",
            "model": "qwen/qwen3.6-plus",
            "prompt_version": "phase16_sql_business_logic_v1",
            "judge_policy": "semantic_user_question",
            "verdict": "business_correct",
            "semantic_business_correct": True,
            "authoritative": True,
            "redacted": True,
        },
        {
            "case_id": "case-2",
            "provider": "openrouter",
            "model": "qwen/qwen3.6-plus",
            "prompt_version": "phase16_sql_business_logic_v1",
            "judge_policy": "semantic_user_question",
            "verdict": "business_incorrect",
            "semantic_business_correct": False,
            "authoritative": True,
            "redacted": True,
        },
    ]
    write_jsonl(root / "judgments.jsonl", judgments)
    write_json(
        root / "judge_summary.json",
        {
            "generated_at": "2026-06-28T00:00:00",
            "provider": "openrouter",
            "model": "qwen/qwen3.6-plus",
            "prompt_version": "phase16_sql_business_logic_v1",
            "judge_policy": "semantic_user_question",
            "authoritative": True,
            "authoritative_judgments": 2,
            "non_authoritative_judgments": 0,
            "total_predictions": 2,
            "total_judged": 2,
            "verdict_counts": {"business_correct": 1, "business_incorrect": 1},
            "semantic_business_counts": {
                "correct": 1,
                "incorrect": 1,
                "unjudged": 0,
                "provider_error": 0,
                "provider_parse_error": 0,
            },
            "redaction_policy": {
                "redaction_applied": True,
                "raw_rows_sent": False,
                "result_previews_sent": False,
                "prompt_response_trace_sent": False,
            },
            "anti_fake_policy": "Live judge artifact. No judgments are inferred or rewritten.",
        },
    )
    write_json(
        root / "judge_costs.json",
        {
            "provider": "openrouter",
            "model": "qwen/qwen3.6-plus",
            "judge_policy": "semantic_user_question",
            "input_tokens": 100,
            "output_tokens": 50,
            "reasoning_tokens": 0,
            "estimated_cost_usd": 0.01,
            "cost_authoritative": True,
        },
    )
    (root / "semantic_business_summary.csv").write_text(
        "prompt_version,judge_policy,authoritative,total_judged,semantic_correct\n"
        "phase16_sql_business_logic_v1,semantic_user_question,true,2,1\n",
        encoding="utf-8",
    )
    (root / "judge_reasoning.md").write_text("# Judge Reasoning\n", encoding="utf-8")


def test_validate_judge_artifact_accepts_authoritative_openrouter_artifact(tmp_path):
    root = tmp_path / "judge"
    _write_authoritative_judge_artifact(root)

    report = validate_judge_artifact(root, require_authoritative=True)

    assert report.ok
    assert report.checked["provider"] == "openrouter"
    assert report.checked["total_judged"] == 2


def test_validate_judge_artifact_rejects_non_authoritative_final_claim(tmp_path):
    root = tmp_path / "judge"
    _write_authoritative_judge_artifact(root)
    summary_path = root / "judge_summary.json"
    summary = read_json(summary_path)
    summary["authoritative"] = False
    write_json(summary_path, summary)

    report = validate_judge_artifact(root, require_authoritative=True)

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"JUDGE_ARTIFACT_NOT_AUTHORITATIVE"}


def test_validate_judge_artifact_rejects_mock_authoritative_artifact(tmp_path):
    root = tmp_path / "judge"
    _write_authoritative_judge_artifact(root)
    summary_path = root / "judge_summary.json"
    costs_path = root / "judge_costs.json"
    summary = read_json(summary_path)
    costs = read_json(costs_path)
    judgments = read_jsonl(root / "judgments.jsonl")
    summary["provider"] = "mock"
    costs["provider"] = "mock"
    costs["cost_authoritative"] = False
    for row in judgments:
        row["provider"] = "mock"
    write_json(summary_path, summary)
    write_json(costs_path, costs)
    write_jsonl(root / "judgments.jsonl", judgments)

    report = validate_judge_artifact(root, require_authoritative=True)

    assert not report.ok
    assert {issue.code for issue in report.issues} == {"MOCK_JUDGE_AUTHORITATIVE"}


def test_mock_judge_does_not_invent_semantic_label_for_valid_mismatch():
    result = MockJudgeProvider().judge(
        {
            "id": "case",
            "valid_sql": True,
            "error": "RESULT_MISMATCH",
            "generated_sql": "SELECT 1",
            "gold_sql": "SELECT 2",
        }
    )

    assert result.verdict == "requires_semantic_review"
    assert result.semantic_business_correct is None
    assert result.authoritative is False


def test_mock_judge_strict_policy_marks_result_mismatch_incorrect():
    result = MockJudgeProvider(judge_policy="strict").judge(
        {
            "id": "case",
            "valid_sql": True,
            "error": "RESULT_MISMATCH",
            "generated_sql": "SELECT 1",
            "gold_sql": "SELECT 2",
        }
    )

    assert result.judge_policy == "strict_reference"
    assert result.verdict == "strict_reference_mismatch"
    assert result.semantic_business_correct is False
    assert result.authoritative is False


def test_mock_judge_marks_exact_sql_match_as_scaffold_correct():
    result = MockJudgeProvider().judge(
        {
            "id": "case",
            "valid_sql": True,
            "generated_sql": " SELECT 1 ; ",
            "gold_sql": "select 1",
        }
    )

    assert result.verdict == "exact_sql_match"
    assert result.semantic_business_correct is True
    assert result.score == 1.0


def test_judge_benchmark_artifact_writes_non_authoritative_artifacts(tmp_path):
    artifact = tmp_path / "benchmark"
    artifact.mkdir()
    output = tmp_path / "judgments"
    _write_artifact(artifact)

    paths = judge_benchmark_artifact(artifact, output_dir=output)

    assert paths["judgments"].exists()
    assert paths["summary"].exists()
    assert paths["costs"].exists()
    assert paths["semantic_summary"].exists()
    assert paths["reasoning"].exists()

    judgments = read_jsonl(paths["judgments"])
    summary = read_json(paths["summary"])
    costs = read_json(paths["costs"])
    reasoning = paths["reasoning"].read_text(encoding="utf-8")
    semantic_summary = paths["semantic_summary"].read_text(encoding="utf-8")

    assert [row["case_id"] for row in judgments] == ["mismatch", "invalid"]
    assert summary["total_predictions"] == 3
    assert summary["total_judged"] == 2
    assert summary["judge_policy"] == "semantic_user_question"
    assert summary["authoritative"] is False
    assert summary["verdict_counts"]["requires_semantic_review"] == 1
    assert costs["estimated_cost_usd"] == 0.0
    assert "semantic_unjudged" in semantic_summary
    assert "requires_semantic_review" in semantic_summary
    assert "Mock judgments are deterministic scaffold labels only" in reasoning


def test_judge_benchmark_artifact_passes_openrouter_model_without_api_key(tmp_path, monkeypatch):
    artifact = tmp_path / "benchmark"
    artifact.mkdir()
    output = tmp_path / "judgments"
    _write_artifact(artifact)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    paths = judge_benchmark_artifact(
        artifact,
        output_dir=output,
        provider_name="openrouter",
        judge_model="deepseek/deepseek-v4-flash",
        sample_size=1,
    )
    summary = read_json(paths["summary"])

    assert summary["provider"] == "openrouter"
    assert summary["model"] == "deepseek/deepseek-v4-flash"
    assert summary["verdict_counts"]["provider_not_configured"] == 1


def test_judge_benchmark_artifact_can_filter_by_case_ids(tmp_path):
    artifact = tmp_path / "benchmark"
    artifact.mkdir()
    output = tmp_path / "judgments"
    _write_artifact(artifact)

    paths = judge_benchmark_artifact(
        artifact,
        output_dir=output,
        provider_name="mock",
        failures_only=False,
        case_ids=["exact", "invalid"],
    )

    judgments = read_jsonl(paths["judgments"])
    summary = read_json(paths["summary"])

    assert [row["case_id"] for row in judgments] == ["exact", "invalid"]
    assert summary["case_ids"] == ["exact", "invalid"]


def test_judge_benchmark_artifact_can_run_strict_policy(tmp_path):
    artifact = tmp_path / "benchmark"
    artifact.mkdir()
    output = tmp_path / "judgments"
    _write_artifact(artifact)

    paths = judge_benchmark_artifact(
        artifact,
        output_dir=output,
        provider_name="mock",
        judge_policy="strict",
    )

    judgments = read_jsonl(paths["judgments"])
    summary = read_json(paths["summary"])
    semantic_summary = paths["semantic_summary"].read_text(encoding="utf-8")

    assert summary["judge_policy"] == "strict_reference"
    assert summary["verdict_counts"]["strict_reference_mismatch"] == 1
    assert judgments[0]["semantic_business_correct"] is False
    assert "strict_reference" in semantic_summary


def test_openrouter_provider_without_api_key_does_not_call_network(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    result = OpenRouterJudgeProvider(api_key=None).judge(
        {"id": "case", "generated_sql": "SELECT 1", "gold_sql": "SELECT 1"}
    )

    assert result.verdict == "provider_not_configured"
    assert result.authoritative is False
    assert result.needs_human_review is True


def test_openrouter_provider_parses_json_response(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "model": "qwen/qwen3.6-plus",
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "verdict": "business_correct",
                                        "semantic_business_correct": True,
                                        "score": 5,
                                        "reason": "The SQL answers the question.",
                                        "metric_correct": True,
                                        "filter_correct": True,
                                        "join_logic_correct": None,
                                        "aggregation_correct": True,
                                        "needs_human_review": False,
                                    }
                                )
                            }
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "reasoning_tokens": 4,
                    },
                }
            ).encode("utf-8")

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OpenRouterJudgeProvider(
        api_key="test-key",
        model_name="qwen/qwen3.6-plus",
        base_url="https://openrouter.ai/api/v1",
    )

    result = provider.judge(
        {
            "id": "case",
            "question": "question",
            "valid_sql": True,
            "generated_sql": "SELECT 1",
            "gold_sql": "SELECT 1",
            "execution_result_preview": [{"name": "raw row"}],
            "gold_result_preview": [{"name": "gold row"}],
            "raw_model_response": "sensitive raw response",
        }
    )

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["body"]["model"] == "qwen/qwen3.6-plus"
    payload = json.loads(captured["body"]["messages"][1]["content"])["artifact"]
    assert "execution_result_preview" not in payload
    assert "gold_result_preview" not in payload
    assert "raw_model_response" not in payload
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert result.authoritative is True
    assert result.judge_policy == "semantic_user_question"
    assert result.semantic_business_correct is True
    assert result.score == 5.0
    assert result.input_tokens == 10
    assert result.output_tokens == 5
    assert result.reasoning_tokens == 4


def test_openrouter_provider_parses_embedded_json_after_non_json_braces(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            content = (
                "I will return JSON after this malformed note {not json}.\n"
                '{"verdict":"business_correct","semantic_business_correct":true,'
                '"score":5,"reason":"The SQL answers the question.",'
                '"needs_human_review":false}'
            )
            return json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: FakeResponse())

    result = OpenRouterJudgeProvider(
        api_key="test-key",
        model_name="deepseek/deepseek-v4-flash",
        max_retries=0,
    ).judge({"id": "case", "generated_sql": "SELECT 1", "gold_sql": "SELECT 1"})

    assert result.verdict == "business_correct"
    assert result.semantic_business_correct is True
    assert result.authoritative is True


def test_judge_benchmark_artifact_records_redaction_policy(tmp_path):
    artifact = tmp_path / "benchmark"
    artifact.mkdir()
    output = tmp_path / "judgments"
    _write_artifact(artifact)

    paths = judge_benchmark_artifact(artifact, output_dir=output)
    summary = read_json(paths["summary"])

    assert summary["redaction_policy"]["redaction_applied"] is True
    assert summary["redaction_policy"]["raw_rows_sent"] is False
    assert "execution_result_preview" in summary["redaction_policy"]["excluded_fields"]


def test_openrouter_provider_can_enable_reasoning(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"verdict": "ok", "semantic_business_correct": True}
                                ),
                                "reasoning_details": [{"type": "reasoning"}],
                            }
                        }
                    ],
                    "usage": {"reasoningTokens": 7},
                }
            ).encode("utf-8")

    captured = {}

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = OpenRouterJudgeProvider(
        api_key="test-key",
        model_name="qwen/qwen3.6-plus",
        reasoning_enabled=True,
    ).judge({"id": "case", "generated_sql": "SELECT 1", "gold_sql": "SELECT 1"})

    assert captured["body"]["reasoning"] == {"enabled": True}
    assert result.reasoning_tokens == 7
    assert result.reasoning_details_present is True


def test_openrouter_provider_can_use_strict_reference_policy(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "verdict": "business_incorrect",
                                        "semantic_business_correct": False,
                                        "score": 2,
                                        "reason": "Missing reference-required support column.",
                                        "needs_human_review": False,
                                    }
                                )
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    captured = {}

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = OpenRouterJudgeProvider(
        api_key="test-key",
        model_name="qwen/qwen3.6-plus",
        judge_policy="strict",
    ).judge(
        {
            "id": "case",
            "valid_sql": True,
            "generated_sql": "SELECT 1",
            "gold_sql": "SELECT 2",
        }
    )

    prompt_payload = json.loads(captured["body"]["messages"][1]["content"])
    assert "strict_reference" in captured["body"]["messages"][0]["content"]
    assert prompt_payload["rubric"]["judge_policy"] == "strict_reference"
    assert result.judge_policy == "strict_reference"
    assert result.verdict == "business_incorrect"
    assert result.semantic_business_correct is False


def test_openrouter_provider_turns_incomplete_read_into_provider_error(monkeypatch):
    class BrokenResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            raise http.client.IncompleteRead(b'{"partial": true')

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: BrokenResponse())
    provider = OpenRouterJudgeProvider(
        api_key="test-key", model_name="qwen/qwen3.6-plus", max_retries=0
    )

    result = provider.judge(
        {
            "id": "case",
            "valid_sql": True,
            "generated_sql": "SELECT 1",
            "gold_sql": "SELECT 2",
        }
    )

    assert result.verdict == "provider_error"
    assert result.semantic_business_correct is None
    assert result.needs_human_review is True


def test_openrouter_provider_retries_transient_incomplete_read(monkeypatch):
    calls = {"n": 0}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            calls["n"] += 1
            if calls["n"] == 1:
                raise http.client.IncompleteRead(b'{"partial": true')
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "verdict": "fail",
                                        "semantic_business_correct": False,
                                        "score": 1,
                                        "reason": "Wrong metric.",
                                        "needs_human_review": False,
                                    }
                                )
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 3},
                }
            ).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    result = OpenRouterJudgeProvider(
        api_key="test-key",
        model_name="qwen/qwen3.6-plus",
        max_retries=1,
    ).judge({"id": "case", "generated_sql": "SELECT 1", "gold_sql": "SELECT 2"})

    assert calls["n"] == 2
    assert result.verdict == "business_incorrect"
    assert result.semantic_business_correct is False
    assert result.authoritative is True


def test_openrouter_provider_handles_empty_content_as_parse_error(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": None}}]}).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())

    result = OpenRouterJudgeProvider(
        api_key="test-key",
        model_name="deepseek/deepseek-v4-flash",
        max_retries=0,
    ).judge({"id": "case", "generated_sql": "SELECT 1", "gold_sql": "SELECT 2"})

    assert result.verdict == "provider_parse_error"
    assert result.semantic_business_correct is None
    assert result.needs_human_review is True


def test_judge_benchmark_artifact_counts_provider_parse_errors_separately(
    tmp_path,
    monkeypatch,
):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": None}}]}).encode("utf-8")

    artifact = tmp_path / "benchmark"
    artifact.mkdir()
    output = tmp_path / "judgments"
    _write_artifact(artifact)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())

    paths = judge_benchmark_artifact(
        artifact,
        output_dir=output,
        provider_name="openrouter",
        judge_model="deepseek/deepseek-v4-flash",
        sample_size=1,
    )
    summary = read_json(paths["summary"])
    report = validate_judge_artifact(output)

    assert summary["semantic_business_counts"]["provider_parse_error"] == 1
    assert summary["semantic_business_counts"].get("unjudged", 0) == 0
    assert report.ok


def test_openrouter_provider_promotes_partial_label_when_user_question_is_answered(
    monkeypatch,
):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "verdict": "partial_match",
                                        "semantic_business_correct": True,
                                        "score": 4,
                                        "reason": "Core metric is correct but support columns are missing.",
                                        "needs_human_review": False,
                                    }
                                )
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())

    result = OpenRouterJudgeProvider(
        api_key="test-key",
        model_name="qwen/qwen3.6-plus",
        max_retries=0,
    ).judge(
        {
            "id": "case",
            "valid_sql": True,
            "generated_sql": "SELECT 1",
            "gold_sql": "SELECT 2",
        }
    )

    assert result.verdict == "business_correct"
    assert result.raw_provider_verdict == "partial_match"
    assert result.semantic_business_correct is True
    assert result.needs_human_review is False


def test_openrouter_provider_keeps_partial_label_unjudged_without_semantic_boolean(
    monkeypatch,
):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "verdict": "partial_business_match",
                                        "semantic_business_correct": None,
                                        "score": 3,
                                        "reason": "Some requested logic may be missing.",
                                        "needs_human_review": True,
                                    }
                                )
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())

    result = OpenRouterJudgeProvider(
        api_key="test-key",
        model_name="qwen/qwen3.6-plus",
        max_retries=0,
    ).judge(
        {
            "id": "case",
            "valid_sql": True,
            "generated_sql": "SELECT 1",
            "gold_sql": "SELECT 2",
        }
    )

    assert result.verdict == "partial_business_match"
    assert result.semantic_business_correct is None
    assert result.needs_human_review is True


def test_openrouter_provider_demotes_partial_label_when_user_question_is_not_answered(
    monkeypatch,
):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "verdict": "partial_match",
                                        "semantic_business_correct": False,
                                        "score": 2,
                                        "reason": "Relevant table, wrong grouping.",
                                        "needs_human_review": False,
                                    }
                                )
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())

    result = OpenRouterJudgeProvider(
        api_key="test-key",
        model_name="qwen/qwen3.6-plus",
        max_retries=0,
    ).judge(
        {
            "id": "case",
            "valid_sql": True,
            "generated_sql": "SELECT 1",
            "gold_sql": "SELECT 2",
        }
    )

    assert result.verdict == "business_incorrect"
    assert result.semantic_business_correct is False
    assert result.needs_human_review is False


def test_openrouter_provider_canonicalizes_invalid_label_for_valid_sql(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "verdict": "invalid",
                                        "semantic_business_correct": False,
                                        "score": 1,
                                        "reason": "The SQL is valid but business shape is wrong.",
                                        "needs_human_review": False,
                                    }
                                )
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())

    result = OpenRouterJudgeProvider(
        api_key="test-key",
        model_name="deepseek/deepseek-v4-flash",
        max_retries=0,
    ).judge(
        {
            "id": "case",
            "valid_sql": True,
            "generated_sql": "SELECT 1",
            "gold_sql": "SELECT 2",
        }
    )

    assert result.verdict == "business_incorrect"
    assert result.raw_provider_verdict == "invalid"
    assert result.semantic_business_correct is False
    assert result.needs_human_review is False
