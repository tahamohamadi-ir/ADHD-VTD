from __future__ import annotations

from src.evaluation.candidate_consistency import SqlCandidate, analyze_candidate_consistency


def test_candidate_consistency_passes_when_candidates_share_shape_and_hash():
    report = analyze_candidate_consistency(
        [
            SqlCandidate(
                candidate_id="a",
                sql="SELECT sleep_duration_category, COUNT(*) AS n FROM student_depression GROUP BY sleep_duration_category",
                valid_sql=True,
                execution_passed=True,
                result_hash="same-hash",
            ),
            SqlCandidate(
                candidate_id="b",
                sql="SELECT sleep_duration_category, COUNT(*) AS n FROM student_depression GROUP BY sleep_duration_category",
                valid_sql=True,
                execution_passed=True,
                result_hash="same-hash",
            ),
        ]
    )

    assert report.passed is True
    assert report.selected_candidate_id == "a"
    assert report.issues == []


def test_candidate_consistency_flags_table_disagreement_without_gold_labels():
    report = analyze_candidate_consistency(
        [
            {
                "candidate_id": "student",
                "sql": "SELECT COUNT(*) AS n FROM student_depression",
                "valid_sql": True,
                "execution_passed": True,
                "result_hash": "h1",
                "gold_sql": "SELECT hidden FROM gold",
                "case_id": "VTD-hidden",
            },
            {
                "candidate_id": "general",
                "sql": "SELECT COUNT(*) AS n FROM mental_health_general",
                "valid_sql": True,
                "execution_passed": True,
                "result_hash": "h1",
                "execution_correct": False,
            },
        ]
    )

    assert report.passed is False
    assert {issue.code for issue in report.issues} == {"CANDIDATE_TABLE_DISAGREEMENT"}
    assert "case_id" not in report.signatures["student"]
    assert "gold_sql" not in report.signatures["student"]


def test_candidate_consistency_flags_result_hash_disagreement():
    report = analyze_candidate_consistency(
        [
            SqlCandidate(
                candidate_id="a",
                sql="SELECT mental_health_risk, COUNT(*) AS n FROM mental_health_general GROUP BY mental_health_risk",
                valid_sql=True,
                execution_passed=True,
                result_hash="hash-a",
            ),
            SqlCandidate(
                candidate_id="b",
                sql="SELECT mental_health_risk, COUNT(*) AS n FROM mental_health_general GROUP BY mental_health_risk",
                valid_sql=True,
                execution_passed=True,
                result_hash="hash-b",
            ),
        ]
    )

    assert report.passed is False
    assert "CANDIDATE_RESULT_HASH_DISAGREEMENT" in {issue.code for issue in report.issues}


def test_candidate_consistency_warns_on_single_viable_candidate():
    report = analyze_candidate_consistency(
        [
            SqlCandidate(
                candidate_id="a",
                sql="SELECT COUNT(*) AS n FROM student_depression",
                valid_sql=True,
                execution_passed=True,
                result_hash="hash-a",
            )
        ]
    )

    assert report.passed is True
    assert report.selected_candidate_id == "a"
    assert [issue.code for issue in report.issues] == ["SINGLE_VIABLE_CANDIDATE"]
    assert [issue.severity for issue in report.issues] == ["warning"]


def test_candidate_consistency_fails_without_viable_candidates():
    report = analyze_candidate_consistency(
        [
            SqlCandidate(
                candidate_id="bad",
                sql="SELECT bad_column FROM student_depression",
                valid_sql=False,
                execution_passed=False,
            )
        ]
    )

    assert report.passed is False
    assert report.selected_candidate_id is None
    assert [issue.code for issue in report.issues] == ["NO_VIABLE_CANDIDATES"]
