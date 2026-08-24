from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl
from src.evaluation.judge_adjudication import (
    adjudicate_consensus,
    apply_adjudications,
    parse_third_judge_decisions,
)


def _write_judgment_dir(root: Path, *, model: str, rows: list[dict]) -> None:
    root.mkdir()
    write_json(
        root / "judge_summary.json",
        {
            "provider": "openrouter",
            "model": model,
            "prompt_version": "phase16_sql_business_logic_v1",
            "judge_policy": "semantic_user_question",
            "source_artifact": "results/benchmark/source",
            "total_judged": len(rows),
        },
    )
    write_jsonl(root / "judgments.jsonl", rows)


def _synthetic_consensus(tmp_path: Path) -> Path:
    qwen = tmp_path / "qwen"
    deepseek = tmp_path / "deepseek"
    _write_judgment_dir(
        qwen,
        model="qwen/qwen3.6-plus",
        rows=[
            {
                "case_id": "agree_correct",
                "authoritative": True,
                "semantic_business_correct": True,
                "verdict": "business_correct",
            },
            {
                "case_id": "dispute",
                "authoritative": True,
                "semantic_business_correct": True,
                "verdict": "business_correct",
            },
            {
                "case_id": "partial_case",
                "authoritative": True,
                "semantic_business_correct": None,
                "verdict": "partial_business_match",
            },
        ],
    )
    _write_judgment_dir(
        deepseek,
        model="deepseek/deepseek-v4-flash",
        rows=[
            {
                "case_id": "agree_correct",
                "authoritative": True,
                "semantic_business_correct": True,
                "verdict": "business_correct",
            },
            {
                "case_id": "dispute",
                "authoritative": True,
                "semantic_business_correct": False,
                "verdict": "business_incorrect",
            },
            {
                "case_id": "partial_case",
                "authoritative": True,
                "semantic_business_correct": None,
                "verdict": "partial_business_match",
            },
        ],
    )
    from src.evaluation.judge_consensus import build_judge_consensus

    paths = build_judge_consensus([qwen, deepseek], output_dir=tmp_path / "consensus")
    return paths["summary"].parent


def _write_decisions_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "adjudicated_label",
                "adjudicator",
                "adjudicator_type",
                "reason",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_apply_overrides_including_non_required_labels_and_recompute_counts(tmp_path):
    consensus_dir = _synthetic_consensus(tmp_path)
    decisions_csv = _write_decisions_csv(
        tmp_path / "decisions.csv",
        [
            {
                "case_id": "dispute",
                "adjudicated_label": "semantic_correct",
                "adjudicator": "reviewer_a",
                "adjudicator_type": "human",
                "reason": "answer matches user intent",
            },
            {
                "case_id": "agree_correct",
                "adjudicated_label": "semantic_incorrect",
                "adjudicator": "reviewer_a",
                "adjudicator_type": "human",
                "reason": "overriding a consensus label",
            },
        ],
    )

    paths = adjudicate_consensus(
        consensus_dir,
        decisions_csv=decisions_csv,
        output_dir=tmp_path / "out",
    )

    cases = {row["case_id"]: row for row in read_jsonl(paths["cases"])}
    summary = read_json(paths["summary"])
    report = paths["report"].read_text(encoding="utf-8")

    assert cases["dispute"]["final_label"] == "consensus_correct"
    assert cases["dispute"]["prior_final_label"] == "adjudication_required"
    assert cases["dispute"]["adjudication"]["adjudicator"] == "reviewer_a"
    assert cases["agree_correct"]["final_label"] == "consensus_incorrect"
    assert cases["agree_correct"]["prior_final_label"] == "consensus_correct"
    assert cases["partial_case"]["final_label"] == "consensus_partial_business_match"
    assert summary["final_counts"] == {
        "consensus_correct": 1,
        "consensus_incorrect": 1,
        "consensus_partial_business_match": 1,
    }
    assert summary["metric_policy_counts"]["needs_human_review"] == 0
    assert summary["metric_policy_counts"]["semantic_correct"] == 1
    assert summary["metric_policy_counts"]["semantic_incorrect"] == 1
    assert summary["metric_policy_counts"]["partial_business_match"] == 1
    assert summary["adjudication"]["remaining_adjudication_required"] == 0
    assert "| dispute | adjudication_required | consensus_correct |" in report
    assert "| agree_correct | consensus_correct | consensus_incorrect |" in report
    original_summary = read_json(consensus_dir / "judge_consensus.json")
    assert original_summary["final_counts"]["adjudication_required"] == 1


def test_unknown_and_duplicate_decision_case_ids_raise(tmp_path):
    consensus_dir = _synthetic_consensus(tmp_path)
    unknown_csv = _write_decisions_csv(
        tmp_path / "unknown.csv",
        [{"case_id": "missing-case", "adjudicated_label": "semantic_correct"}],
    )
    with pytest.raises(ValueError, match="Unknown case_id"):
        adjudicate_consensus(
            consensus_dir, decisions_csv=unknown_csv, output_dir=tmp_path / "out_unknown"
        )

    duplicate_csv = _write_decisions_csv(
        tmp_path / "duplicate.csv",
        [
            {"case_id": "dispute", "adjudicated_label": "semantic_correct"},
            {"case_id": "dispute", "adjudicated_label": "semantic_incorrect"},
        ],
    )
    with pytest.raises(ValueError, match="Duplicate"):
        adjudicate_consensus(
            consensus_dir, decisions_csv=duplicate_csv, output_dir=tmp_path / "out_dup"
        )


def test_third_judge_parsing_maps_labels_and_skips_non_authoritative(tmp_path):
    third = tmp_path / "third_judge"
    _write_judgment_dir(
        third,
        model="openai/gpt-5.1",
        rows=[
            {
                "case_id": "case_ok",
                "authoritative": True,
                "semantic_business_correct": True,
                "verdict": "business_correct",
            },
            {
                "case_id": "case_bad",
                "authoritative": True,
                "semantic_business_correct": False,
                "verdict": "business_incorrect",
            },
            {
                "case_id": "case_non_auth",
                "authoritative": False,
                "semantic_business_correct": True,
                "verdict": "business_correct",
            },
            {
                "case_id": "case_partial",
                "authoritative": True,
                "semantic_business_correct": None,
                "verdict": "partial_business_match",
            },
            {
                "case_id": "case_review",
                "authoritative": True,
                "semantic_business_correct": None,
                "needs_human_review": True,
                "verdict": "business_correct",
            },
            {
                "case_id": "case_error",
                "authoritative": True,
                "semantic_business_correct": None,
                "verdict": "provider_error",
            },
        ],
    )
    decisions, skipped = parse_third_judge_decisions(third)

    by_case = {decision["case_id"]: decision for decision in decisions}
    assert set(by_case) == {"case_ok", "case_bad"}
    assert by_case["case_ok"]["adjudicated_label"] == "semantic_correct"
    assert by_case["case_ok"]["final_label"] == "consensus_correct"
    assert by_case["case_bad"]["adjudicated_label"] == "semantic_incorrect"
    assert all(d["adjudicator_type"] == "third_judge" for d in decisions)
    assert all(d["adjudicator"] == "openai/gpt-5.1" for d in decisions)
    assert skipped == {
        "needs_human_review": 1,
        "non_authoritative": 1,
        "partial_business_match": 1,
        "unjudged_or_provider_error": 1,
    }

    qwen = tmp_path / "third_qwen"
    deepseek = tmp_path / "third_deepseek"
    _write_judgment_dir(
        qwen,
        model="qwen/qwen3.6-plus",
        rows=[
            {
                "case_id": "case_ok",
                "authoritative": True,
                "semantic_business_correct": True,
                "verdict": "business_correct",
            },
            {
                "case_id": "case_bad",
                "authoritative": True,
                "semantic_business_correct": False,
                "verdict": "business_incorrect",
            },
        ],
    )
    _write_judgment_dir(
        deepseek,
        model="deepseek/deepseek-v4-flash",
        rows=[
            {
                "case_id": "case_ok",
                "authoritative": True,
                "semantic_business_correct": False,
                "verdict": "business_incorrect",
            },
            {
                "case_id": "case_bad",
                "authoritative": True,
                "semantic_business_correct": True,
                "verdict": "business_correct",
            },
        ],
    )
    from src.evaluation.judge_consensus import build_judge_consensus

    paths = build_judge_consensus([qwen, deepseek], output_dir=tmp_path / "consensus_third")
    adjudicated = adjudicate_consensus(
        paths["summary"].parent,
        third_judge_dirs=[third],
        output_dir=tmp_path / "out_third",
        fail_on_unresolved=True,
    )
    summary = read_json(adjudicated["summary"])
    assert summary["adjudication"]["skipped_counts"] == skipped
    assert summary["final_counts"]["consensus_correct"] == 1
    assert summary["final_counts"]["consensus_incorrect"] == 1
    assert summary["adjudication"]["remaining_adjudication_required"] == 0


def test_fail_on_unresolved_flag_blocks_remaining_cases(tmp_path):
    consensus_dir = _synthetic_consensus(tmp_path)
    decisions_csv = _write_decisions_csv(
        tmp_path / "override_one.csv",
        [{"case_id": "agree_correct", "adjudicated_label": "semantic_incorrect"}],
    )
    with pytest.raises(RuntimeError, match="still require adjudication"):
        adjudicate_consensus(
            consensus_dir,
            decisions_csv=decisions_csv,
            output_dir=tmp_path / "out_fail",
            fail_on_unresolved=True,
        )
    assert not (tmp_path / "out_fail").exists()

    paths = adjudicate_consensus(
        consensus_dir,
        decisions_csv=decisions_csv,
        output_dir=tmp_path / "out_lenient",
    )
    summary = read_json(paths["summary"])
    assert summary["adjudication"]["remaining_adjudication_required"] == 1


def test_apply_adjudications_is_pure_on_input_cases():
    cases = [
        {"case_id": "a", "final_label": "adjudication_required"},
        {"case_id": "b", "final_label": "consensus_correct"},
    ]
    decisions = [{"case_id": "a", "final_label": "consensus_incorrect"}]
    updated = apply_adjudications(cases, decisions)
    assert updated[0]["final_label"] == "consensus_incorrect"
    assert cases[0]["final_label"] == "adjudication_required"
