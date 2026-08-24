from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.evaluation.dataset_loader import write_json, write_jsonl
from src.evaluation.judge_spot_check import (
    REVIEWER_LABELS,
    SPOT_CHECK_CSV_COLUMNS,
    build_spot_check_package,
    import_spot_check_labels,
    select_spot_check,
)


def _write_authoritative_dir(root: Path, rows: list[dict], *, authoritative: bool = True) -> Path:
    root.mkdir()
    write_json(
        root / "judge_summary.json",
        {
            "provider": "openrouter",
            "model": "qwen/qwen3.6-plus",
            "authoritative": authoritative,
            "total_judged": len(rows),
        },
    )
    write_jsonl(root / "judgments.jsonl", rows)
    return root


def _row(case_id: str, semantic_business_correct: bool | None, verdict: str = "") -> dict:
    return {
        "case_id": case_id,
        "authoritative": True,
        "semantic_business_correct": semantic_business_correct,
        "verdict": verdict
        or ("business_correct" if semantic_business_correct else "business_incorrect"),
        "generated_sql": "SELECT COUNT(*) FROM t",
        "reason": f"reason {case_id}",
    }


def test_select_spot_check_is_deterministic_stratified_with_min_class():
    rows = (
        [_row(f"c{index:03d}", True) for index in range(90)]
        + [_row(f"i{index:03d}", False) for index in range(10)]
        + [_row(f"u{index:03d}", None) for index in range(3)]
    )
    first = select_spot_check(rows, 40, 187)
    second = select_spot_check(rows, 40, 187)

    assert first == second
    assert len(first) == len({row["case_id"] for row in first}) == 40

    def stratum_count(selected: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in selected:
            key = (
                "unjudged"
                if row["semantic_business_correct"] is None
                else ("correct" if row["semantic_business_correct"] else "incorrect")
            )
            counts[key] = counts.get(key, 0) + 1
        return counts

    assert stratum_count(first) == {"correct": 27, "incorrect": 10, "unjudged": 3}

    skewed = [_row(f"c{index:03d}", True) for index in range(95)] + [
        _row(f"i{index:03d}", False) for index in range(15)
    ]
    selected = select_spot_check(skewed, 30, 7)
    counts = stratum_count(selected)
    assert counts["incorrect"] >= 10
    assert counts["correct"] == 30 - counts["incorrect"]

    balanced = [_row(f"c{index:03d}", True) for index in range(20)] + [
        _row(f"i{index:03d}", False) for index in range(20)
    ]
    assert stratum_count(select_spot_check(balanced, 20, 1)) == {"correct": 10, "incorrect": 10}


def test_build_spot_check_package_redacts_sql_and_records_summary(tmp_path):
    source = _write_authoritative_dir(
        tmp_path / "judge",
        [_row(f"vtd-{index:03d}", index % 2 == 0) for index in range(12)],
    )

    paths = build_spot_check_package(source, n=8, seed=5, output_dir=tmp_path / "package")

    with paths["csv"].open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        rows = list(reader)

    assert tuple(header) == SPOT_CHECK_CSV_COLUMNS
    assert all("sql" not in column.lower() for column in header)
    assert len(rows) == 8
    assert all(row["reviewer_semantic_business_label"] == "" for row in rows)
    assert all(len(row["judge_reason_truncated"]) <= 500 for row in rows)

    summary = _read_json(paths["summary"])
    assert summary["source_authoritative"] is True
    assert summary["redacted"] is True
    assert summary["paper_metric_allowed"] is False
    assert summary["sampled"] == 8
    assert summary["requested_sample_size"] == 8
    assert summary["seed"] == 5
    assert sum(summary["strata_counts"].values()) == 12
    assert sum(summary["sampled_strata_counts"].values()) == 8


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_spot_check_package_rejects_non_authoritative(tmp_path):
    source = _write_authoritative_dir(tmp_path / "judge", [_row("a", True)], authoritative=False)
    with pytest.raises(ValueError, match="not authoritative"):
        build_spot_check_package(source, n=1, seed=1, output_dir=tmp_path / "package")


def _fill_labels(csv_path: Path, labels: list[str]) -> Path:
    filled = csv_path.with_name("filled.csv")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row, label in zip(rows, labels, strict=True):
        row["reviewer_semantic_business_label"] = label
    fieldnames = list(SPOT_CHECK_CSV_COLUMNS)
    with filled.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return filled


def test_import_rejects_invalid_or_blank_labels_before_authoritative_output(tmp_path):
    package = build_spot_check_package(
        _write_authoritative_dir(
            tmp_path / "judge", [_row(f"vtd-{i:03d}", i % 2 == 0) for i in range(4)]
        ),
        n=4,
        seed=3,
        output_dir=tmp_path / "package",
    )
    filled = _fill_labels(package["csv"], ["correct", "", "banana", "incorrect"])

    paths = import_spot_check_labels(
        filled,
        package["summary"],
        output_dir=tmp_path / "import",
        authoritative=True,
    )

    summary = _read_json(paths["summary"])
    report = paths["report"].read_text(encoding="utf-8")
    assert summary["status"] == "invalid_labels"
    assert summary["authoritative"] is False
    assert summary["paper_metric_allowed"] is False
    assert summary["agreement_rate"] is None
    assert summary["cohens_kappa"] is None
    assert summary["reason"]
    assert not (tmp_path / "import" / "judge_spot_check_cases.jsonl").exists()
    assert "invalid_labels" in report


def test_import_agreement_rate_and_kappa_on_fixed_labels(tmp_path):
    judge_rows = [
        _row("agree-1", True),
        _row("agree-2", True),
        _row("agree-3", False),
        _row("agree-4", False),
    ]
    package = build_spot_check_package(
        _write_authoritative_dir(tmp_path / "judge", judge_rows),
        n=4,
        seed=11,
        output_dir=tmp_path / "package",
    )

    partial = _fill_labels(package["csv"], ["correct", "incorrect", "incorrect", "incorrect"])
    paths_partial = import_spot_check_labels(
        partial,
        package["summary"],
        output_dir=tmp_path / "import_partial",
    )
    summary_partial = _read_json(paths_partial["summary"])
    assert summary_partial["status"] == "complete"
    assert summary_partial["authoritative"] is False
    assert summary_partial["paper_metric_allowed"] is False
    assert summary_partial["agreement_rate"] == 0.75
    assert summary_partial["cohens_kappa"] == 0.5
    assert summary_partial["agreement_denominator"] == 4

    perfect = _fill_labels(package["csv"], ["correct", "correct", "incorrect", "incorrect"])
    paths_perfect = import_spot_check_labels(
        perfect,
        package["summary"],
        output_dir=tmp_path / "import_perfect",
        authoritative=True,
    )
    summary_perfect = _read_json(paths_perfect["summary"])
    assert summary_perfect["agreement_rate"] == 1.0
    assert summary_perfect["cohens_kappa"] == 1.0
    assert summary_perfect["authoritative"] is True
    assert summary_perfect["paper_metric_allowed"] is True

    cases = [
        json.loads(line)
        for line in (tmp_path / "import_perfect" / "judge_spot_check_cases.jsonl")
        .open(encoding="utf-8")
        .readlines()
    ]
    assert len(cases) == 4
    assert all(case["agree"] for case in cases)


def test_build_spot_check_package_enriches_questions_from_predictions(tmp_path):
    source = _write_authoritative_dir(
        tmp_path / "judge",
        [
            _row("vtd-match-1", True),
            _row("vtd-match-2", False),
            _row("vtd-missing", True),
        ],
    )
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(
        "\n".join(
            [
                json.dumps({"case_id": "vtd-match-1", "question": "تعداد کل دانشجوها؟"}),
                json.dumps({"case_id": "vtd-unmatched", "question": "سوال بی‌همتا"}),
                json.dumps({"case_id": "vtd-match-2", "question_fa": "میانگین معدل چقدر است؟"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    paths = build_spot_check_package(
        source,
        n=3,
        seed=1,
        output_dir=tmp_path / "package",
        predictions_file=predictions,
    )

    with paths["csv"].open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_case = {row["case_id"]: row for row in rows}

    assert by_case["vtd-match-1"]["question"] == "تعداد کل دانشجوها؟"
    assert by_case["vtd-match-2"]["question"] == "میانگین معدل چقدر است؟"
    assert by_case["vtd-missing"]["question"] == ""

    summary = _read_json(paths["summary"])
    assert summary["questions_enriched"] == 2
    assert summary["redacted"] is True
    header = list(by_case.values())[0].keys()
    assert all("sql" not in column.lower() and "gold" not in column.lower() for column in header)


def test_reviewer_label_vocabulary_is_shared_between_build_and_import():
    assert set(REVIEWER_LABELS) == {"correct", "incorrect", "partial_business_match"}
