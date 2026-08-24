from __future__ import annotations

from pathlib import Path

import pytest

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl
from src.evaluation.judge_consensus import build_judge_consensus


def _write_judgment_dir(
    root: Path,
    *,
    model: str,
    rows: list[dict],
    prompt_version: str = "phase16_sql_business_logic_v1",
    judge_policy: str = "semantic_user_question",
) -> None:
    root.mkdir()
    write_json(
        root / "judge_summary.json",
        {
            "provider": "openrouter",
            "model": model,
            "prompt_version": prompt_version,
            "judge_policy": judge_policy,
            "source_artifact": "results/benchmark/source",
            "total_judged": len(rows),
        },
    )
    write_jsonl(root / "judgments.jsonl", rows)


def test_judge_consensus_requires_two_non_null_authoritative_votes(tmp_path):
    qwen = tmp_path / "qwen"
    deepseek = tmp_path / "deepseek"
    gpt = tmp_path / "gpt"
    _write_judgment_dir(
        qwen,
        model="qwen/qwen3.6-plus",
        rows=[
            {"case_id": "correct", "authoritative": True, "semantic_business_correct": True, "verdict": "business_correct"},
            {"case_id": "bad", "authoritative": True, "semantic_business_correct": False, "verdict": "business_incorrect"},
            {"case_id": "single", "authoritative": True, "semantic_business_correct": False, "verdict": "business_incorrect"},
            {"case_id": "conflict", "authoritative": True, "semantic_business_correct": True, "verdict": "business_correct"},
            {"case_id": "partial", "authoritative": True, "semantic_business_correct": None, "verdict": "partial_business_match"},
        ],
    )
    _write_judgment_dir(
        deepseek,
        model="deepseek/deepseek-v4-flash",
        rows=[
            {"case_id": "correct", "authoritative": True, "semantic_business_correct": True, "verdict": "business_correct"},
            {"case_id": "bad", "authoritative": True, "semantic_business_correct": None, "verdict": "requires_semantic_review"},
            {"case_id": "single", "authoritative": False, "semantic_business_correct": False, "verdict": "provider_error"},
            {"case_id": "conflict", "authoritative": True, "semantic_business_correct": False, "verdict": "business_incorrect"},
            {"case_id": "partial", "authoritative": True, "semantic_business_correct": None, "verdict": "partial_business_match"},
        ],
    )
    _write_judgment_dir(
        gpt,
        model="openai/gpt-5.1",
        rows=[
            {"case_id": "bad", "authoritative": True, "semantic_business_correct": False, "verdict": "business_incorrect"},
        ],
    )

    paths = build_judge_consensus(
        [qwen, deepseek, gpt],
        output_dir=tmp_path / "consensus",
    )

    summary = read_json(paths["summary"])
    cases = {row["case_id"]: row for row in read_jsonl(paths["cases"])}
    report = paths["report"].read_text(encoding="utf-8")

    assert summary["final_counts"] == {
        "consensus_incorrect": 1,
        "adjudication_required": 2,
        "consensus_correct": 1,
        "consensus_partial_business_match": 1,
    }
    assert summary["metric_policy_counts"] == {
        "semantic_correct": 1,
        "semantic_incorrect": 1,
        "partial_business_match": 1,
        "needs_human_review": 2,
    }
    assert summary["same_prompt_version"] is True
    assert summary["same_judge_policy"] is True
    assert summary["prompt_versions"] == [
        "phase16_sql_business_logic_v1",
        "phase16_sql_business_logic_v1",
        "phase16_sql_business_logic_v1",
    ]
    assert summary["judge_policies"] == [
        "semantic_user_question",
        "semantic_user_question",
        "semantic_user_question",
    ]
    assert cases["correct"]["final_label"] == "consensus_correct"
    assert cases["bad"]["final_label"] == "consensus_incorrect"
    assert cases["single"]["final_label"] == "adjudication_required"
    assert cases["conflict"]["final_label"] == "adjudication_required"
    assert cases["partial"]["final_label"] == "consensus_partial_business_match"
    assert cases["partial"]["authoritative_partial_count"] == 2
    assert "same_prompt_version" in report
    assert "same_judge_policy" in report
    assert "Single-judge" in report


def test_judge_consensus_rejects_single_judge_or_single_vote_policy(tmp_path):
    qwen = tmp_path / "qwen"
    _write_judgment_dir(
        qwen,
        model="qwen/qwen3.6-plus",
        rows=[{"case_id": "case", "authoritative": True, "semantic_business_correct": True}],
    )

    with pytest.raises(ValueError, match="At least two"):
        build_judge_consensus([qwen], output_dir=tmp_path / "out")

    deepseek = tmp_path / "deepseek"
    _write_judgment_dir(
        deepseek,
        model="deepseek/deepseek-v4-flash",
        rows=[{"case_id": "case", "authoritative": True, "semantic_business_correct": True}],
    )
    with pytest.raises(ValueError, match="min_agree"):
        build_judge_consensus([qwen, deepseek], output_dir=tmp_path / "out2", min_agree=1)
