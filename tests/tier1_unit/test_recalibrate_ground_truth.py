"""Tests for the ground-truth recalibration CLI."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from scripts.recalibrate_ground_truth import _next_version_path, recalibrate


DATASET = [
    {"id": "T1", "question_fa": "تعداد کل", "sql": "SELECT COUNT(*) AS n FROM student_depression"},
    {
        "id": "T2",
        "question_fa": "میانگین سن به تفکیک جنسیت",
        "sql": "SELECT gender, AVG(age) FROM student_depression GROUP BY gender",
    },
    {"id": "T3", "question_fa": "ستون ناموجود", "sql": "SELECT nope FROM student_depression"},
]


@pytest.fixture()
def dataset_file(tmp_path: Path) -> Path:
    p = tmp_path / "dev.json"
    p.write_text(json.dumps(DATASET, ensure_ascii=False), encoding="utf-8")
    return p


def test_version_bump_uses_family_base(tmp_path: Path) -> None:
    base = tmp_path / "dev.json"
    assert _next_version_path(base).name == "dev_v2.json"
    v2 = tmp_path / "dev_v2.json"
    v2.write_text("[]", encoding="utf-8")
    assert _next_version_path(v2).name == "dev_v3.json"
    v3 = tmp_path / "dev_v3.json"
    v3.write_text("[]", encoding="utf-8")
    assert _next_version_path(v3).name == "dev_v4.json"


def test_recalibrate_writes_new_file_and_report(dataset_file: Path) -> None:
    out_path, report = recalibrate(dataset_file)
    assert out_path != dataset_file
    assert out_path.exists()
    assert report["total_cases"] == 3
    assert report["failure_count"] == 1
    assert report["failures"][0]["id"] == "T3"
    assert len(report["input_sha256"]) == 64
    assert len(report["output_sha256"]) == 64
    recal_report = out_path.with_suffix(".recalibration.json")
    assert recal_report.exists()
    payload = json.loads(recal_report.read_text(encoding="utf-8"))
    assert payload["failure_count"] == 1


def test_original_input_untouched(dataset_file: Path) -> None:
    before = dataset_file.read_bytes()
    recalibrate(dataset_file)
    assert dataset_file.read_bytes() == before


def test_cli_module_importable() -> None:
    spec = importlib.util.find_spec("scripts.recalibrate_ground_truth")
    assert spec is not None and sys.modules.get("scripts.recalibrate_ground_truth") is not None or spec is not None
