from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl
from src.evaluation.llm_judge import validate_judge_artifact


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _write_judge_dir(root: Path, rows: list[dict[str, object]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    write_jsonl(root / "judgments.jsonl", rows)
    write_json(
        root / "judge_summary.json",
        {
            "generated_at": "2026-07-05T00:00:00",
            "provider": "openrouter",
            "model": "deepseek/deepseek-v4-flash",
            "prompt_version": "phase16_sql_business_logic_v1",
            "judge_policy": "semantic_user_question",
            "authoritative": all(row.get("authoritative") is True for row in rows),
            "authoritative_judgments": sum(1 for row in rows if row.get("authoritative") is True),
            "non_authoritative_judgments": sum(
                1 for row in rows if row.get("authoritative") is not True
            ),
            "total_predictions": 2,
            "total_judged": len(rows),
            "verdict_counts": {},
            "semantic_business_counts": {},
            "redaction_policy": {
                "redaction_applied": True,
                "raw_rows_sent": False,
                "result_previews_sent": False,
                "prompt_response_trace_sent": False,
            },
            "anti_fake_policy": "Live retry artifact.",
        },
    )
    write_json(
        root / "judge_costs.json",
        {
            "provider": "openrouter",
            "model": "deepseek/deepseek-v4-flash",
            "judge_policy": "semantic_user_question",
            "input_tokens": 10,
            "output_tokens": 5,
            "reasoning_tokens": 0,
            "estimated_cost_usd": 0.0,
            "cost_authoritative": True,
        },
    )
    (root / "semantic_business_summary.csv").write_text("provider,model\n", encoding="utf-8")
    (root / "judge_reasoning.md").write_text("# Reasoning\n", encoding="utf-8")


def test_merge_judge_artifacts_prefers_authoritative_retry_rows(tmp_path):
    original = tmp_path / "original"
    rerun = tmp_path / "rerun"
    output = tmp_path / "merged"
    _write_judge_dir(
        original,
        [
            {
                "case_id": "case-a",
                "provider": "openrouter",
                "model": "deepseek/deepseek-v4-flash",
                "prompt_version": "phase16_sql_business_logic_v1",
                "judge_policy": "semantic_user_question",
                "verdict": "provider_parse_error",
                "semantic_business_correct": None,
                "authoritative": False,
                "redacted": True,
            },
            {
                "case_id": "case-b",
                "provider": "openrouter",
                "model": "deepseek/deepseek-v4-flash",
                "prompt_version": "phase16_sql_business_logic_v1",
                "judge_policy": "semantic_user_question",
                "verdict": "business_incorrect",
                "semantic_business_correct": False,
                "authoritative": True,
                "redacted": True,
            },
        ],
    )
    _write_judge_dir(
        rerun,
        [
            {
                "case_id": "case-a",
                "provider": "openrouter",
                "model": "deepseek/deepseek-v4-flash",
                "prompt_version": "phase16_sql_business_logic_v1",
                "judge_policy": "semantic_user_question",
                "verdict": "business_correct",
                "semantic_business_correct": True,
                "authoritative": True,
                "redacted": True,
            },
            {
                "case_id": "case-b",
                "provider": "openrouter",
                "model": "deepseek/deepseek-v4-flash",
                "prompt_version": "phase16_sql_business_logic_v1",
                "judge_policy": "semantic_user_question",
                "verdict": "provider_parse_error",
                "semantic_business_correct": None,
                "authoritative": False,
                "redacted": True,
            },
        ],
    )

    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "merge_judge_artifacts.py"),
            str(original),
            str(rerun),
            "--output-dir",
            str(output),
            "--duplicate-policy",
            "prefer-authoritative",
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )

    summary = read_json(output / "judge_summary.json")
    rows = {row["case_id"]: row for row in read_jsonl(output / "judgments.jsonl")}
    report = validate_judge_artifact(output, require_authoritative=True)

    assert report.ok
    assert summary["authoritative"] is True
    assert summary["duplicate_resolution_counts"] == {
        "duplicates": 2,
        "kept_existing_authoritative": 1,
        "replaced_with_authoritative": 1,
    }
    assert rows["case-a"]["verdict"] == "business_correct"
    assert rows["case-b"]["verdict"] == "business_incorrect"
