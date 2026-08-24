from __future__ import annotations

from pathlib import Path

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl
from src.evaluation.judge_agreement import analyze_judge_agreement


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


def test_analyze_judge_agreement_marks_partial_as_adjudication_required(tmp_path):
    left = tmp_path / "qwen"
    right = tmp_path / "deepseek"
    _write_judgment_dir(
        left,
        model="qwen/qwen3.6-plus",
        rows=[
            {
                "case_id": "bad",
                "verdict": "business_incorrect",
                "semantic_business_correct": False,
                "reason": "Wrong metric.",
            },
            {
                "case_id": "partial",
                "verdict": "partial_business_match",
                "semantic_business_correct": None,
                "raw_provider_verdict": "partial_match",
                "reason": "Core metric only.",
            },
        ],
    )
    _write_judgment_dir(
        right,
        model="deepseek/deepseek-v4-flash",
        rows=[
            {
                "case_id": "bad",
                "verdict": "business_incorrect",
                "semantic_business_correct": False,
                "reason": "Wrong metric.",
            },
            {
                "case_id": "partial",
                "verdict": "partial_business_match",
                "semantic_business_correct": None,
                "raw_provider_verdict": "partial_match",
                "reason": "Needs review.",
            },
        ],
    )

    paths = analyze_judge_agreement(left, right, output_dir=tmp_path / "agreement")

    summary = read_json(paths["summary"])
    cases = read_jsonl(paths["cases"])
    report = paths["report"].read_text(encoding="utf-8")

    assert summary["common_cases"] == 2
    assert summary["same_prompt_version"] is True
    assert summary["same_judge_policy"] is True
    assert summary["left_prompt_version"] == "phase16_sql_business_logic_v1"
    assert summary["left_judge_policy"] == "semantic_user_question"
    assert summary["semantic_agreement_count"] == 2
    assert summary["final_counts"] == {
        "agreed_incorrect": 1,
        "adjudication_required": 1,
    }
    partial_case = next(row for row in cases if row["case_id"] == "partial")
    assert partial_case["adjudication_required"] is True
    assert partial_case["final_label"] == "adjudication_required"
    assert "does not call a model" in report
    assert "same_judge_policy" in report


def test_analyze_judge_agreement_records_case_mismatch(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    _write_judgment_dir(
        left,
        model="a",
        rows=[{"case_id": "left-only", "verdict": "business_incorrect", "semantic_business_correct": False}],
    )
    _write_judgment_dir(
        right,
        model="b",
        rows=[{"case_id": "right-only", "verdict": "business_incorrect", "semantic_business_correct": False}],
    )

    paths = analyze_judge_agreement(left, right, output_dir=tmp_path / "agreement")

    summary = read_json(paths["summary"])
    assert summary["common_cases"] == 0
    assert summary["left_only_cases"] == ["left-only"]
    assert summary["right_only_cases"] == ["right-only"]
