from __future__ import annotations

from pathlib import Path

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl
from src.evaluation.dual_policy_report import build_dual_policy_report


def _write_agreement_dir(root: Path, *, rows: list[dict], policy: str) -> None:
    root.mkdir()
    write_json(
        root / "judge_agreement.json",
        {
            "left_source_artifact": "results/benchmark/source",
            "right_source_artifact": "results/benchmark/source",
            "left_prompt_version": "phase16_sql_business_logic_v1",
            "right_prompt_version": "phase16_sql_business_logic_v1",
            "left_judge_policy": policy,
            "right_judge_policy": policy,
        },
    )
    write_jsonl(root / "judge_agreement_cases.jsonl", rows)


def test_build_dual_policy_report_merges_agreement_reports(tmp_path):
    semantic = tmp_path / "semantic"
    strict = tmp_path / "strict"
    _write_agreement_dir(
        semantic,
        policy="semantic_user_question",
        rows=[
            {"case_id": "case-a", "final_label": "agreed_correct"},
            {"case_id": "case-b", "final_label": "adjudication_required"},
        ],
    )
    _write_agreement_dir(
        strict,
        policy="strict_reference",
        rows=[
            {"case_id": "case-a", "final_label": "agreed_incorrect"},
            {"case_id": "case-b", "final_label": "agreed_correct"},
        ],
    )

    paths = build_dual_policy_report(
        semantic,
        strict,
        output_dir=tmp_path / "dual",
    )

    summary = read_json(paths["summary"])
    cases = {row["case_id"]: row for row in read_jsonl(paths["cases"])}
    report = paths["report"].read_text(encoding="utf-8")

    assert summary["common_cases"] == 2
    assert summary["semantic_counts"] == {"correct": 1, "adjudication_required": 1}
    assert summary["strict_counts"] == {"incorrect": 1, "correct": 1}
    assert summary["combined_counts"] == {
        "semantic_correct_strict_incorrect": 1,
        "adjudication_required": 1,
    }
    assert cases["case-a"]["semantic_correct"] is True
    assert cases["case-a"]["strict_correct"] is False
    assert "does not call a model" in report
