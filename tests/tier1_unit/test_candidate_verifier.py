from __future__ import annotations

from src.evaluation.candidate_verifier import verify_sql_candidates


def test_candidate_verifier_selects_highest_runtime_score_without_gold_labels():
    report = verify_sql_candidates(
        [
            {
                "candidate_id": "missing_value",
                "sql": "SELECT COUNT(*) AS n FROM student_depression",
                "valid_sql": True,
                "execution_passed": True,
                "result_hash": "same",
                "gold_sql": "SELECT hidden FROM gold",
                "expected_sql": "SELECT hidden FROM expected",
                "execution_correct": True,
                "ok": True,
                "error": "RESULT_MISMATCH",
                "benchmark_error": "RESULT_MISMATCH",
                "semantic_policy_label": "correct",
                "metadata": {
                    "validation_errors": [],
                    "result_match": True,
                    "case_id": "VTD-hidden",
                    "expected_result_hash": "gold-hash",
                },
            },
            {
                "candidate_id": "with_value",
                "sql": "SELECT COUNT(*) AS n FROM student_depression WHERE depression_flag = 1",
                "valid_sql": True,
                "execution_passed": True,
                "result_hash": "same",
                "metadata": {"validation_errors": []},
            },
        ],
        consistency_report={"passed": True, "issues": []},
        schema_context={"student_depression": {"columns": []}},
        value_links={"depressed [depression_flag]": 1},
    )

    assert report.action == "select"
    assert report.selected_candidate_id == "with_value"
    assert report.latency_ms is not None
    assert report.latency_ms >= 0
    assert report.as_dict()["latency_ms"] == report.latency_ms
    assert report.candidates[1]["metadata"]["candidate_score"]["value_coverage"] == 1.0
    assert "gold_sql" not in report.candidates[0]
    assert "expected_sql" not in report.candidates[0]
    assert "execution_correct" not in report.candidates[0]
    assert "ok" not in report.candidates[0]
    assert "error" not in report.candidates[0]
    assert "semantic_policy_label" not in report.candidates[0]
    assert "result_match" not in report.candidates[0]["metadata"]
    assert "case_id" not in report.candidates[0]["metadata"]
    assert "expected_result_hash" not in report.candidates[0]["metadata"]
    assert "gold_sql" not in report.as_dict()


def test_candidate_verifier_clarifies_when_candidate_disagreement_is_high():
    report = verify_sql_candidates(
        [
            {
                "candidate_id": "a",
                "sql": "SELECT COUNT(*) AS n FROM student_depression",
                "valid_sql": True,
                "execution_passed": True,
                "result_hash": "h1",
                "metadata": {"validation_errors": []},
            },
            {
                "candidate_id": "b",
                "sql": "SELECT COUNT(*) AS n FROM mental_health_general",
                "valid_sql": True,
                "execution_passed": True,
                "result_hash": "h2",
                "metadata": {"validation_errors": []},
            },
        ],
        consistency_report={
            "passed": False,
            "issues": [
                {
                    "code": "CANDIDATE_RESULT_HASH_DISAGREEMENT",
                    "message": "runtime result hashes disagree",
                    "severity": "error",
                }
            ],
        },
    )

    assert report.action == "clarify"
    assert report.reason == "candidate_disagreement"
    assert report.selected_candidate_id is None
    assert report.disagreement_high is True


def test_candidate_verifier_penalizes_unsafe_candidate_and_selects_none():
    report = verify_sql_candidates(
        [
            {
                "candidate_id": "unsafe",
                "sql": "DROP TABLE student_depression",
                "valid_sql": False,
                "execution_passed": False,
                "result_hash": None,
                "metadata": {
                    "shape_ok": False,
                    "validation_errors": [
                        {
                            "code": "FORBIDDEN_KEYWORD",
                            "message": "Forbidden SQL keyword: drop",
                            "severity": "error",
                        }
                    ],
                },
            }
        ],
        consistency_report={"passed": True, "issues": []},
    )

    score = report.candidates[0]["metadata"]["candidate_score"]
    assert report.action == "clarify"
    assert report.reason == "no_viable_candidate"
    assert score["unsafe_penalty"] == 1.0
    assert score["validation_ok"] is False
    assert score["execution_ok"] is False
