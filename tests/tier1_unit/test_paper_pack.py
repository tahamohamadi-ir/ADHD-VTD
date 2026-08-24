from __future__ import annotations

from pathlib import Path

import pytest

from src.evaluation.paper_pack import (
    PROMOTION_REQUIRED_COLUMNS,
    NA,
    PromotionRow,
    ScopeEvaluation,
    build_manifest_payload,
    evaluate_promotion_rows,
    extract_benchmark_metrics,
    extract_judge_metrics,
    has_forbidden_final_marker,
    parse_promotion_registry,
    render_paper_tables,
    set_promotion_status,
)

NON_PROMOTION_TABLE = "| Run | Value |\n|---|---|\n| alpha | 1 |\n"

PROMOTION_HEADER = (
    "| Scope | Artifact Type | Artifact Path | Evidence Family "
    "| Status | Paper Metric Allowed | Notes |"
)
PROMOTION_SEPARATOR = "|---|---|---|---|---|---|---|"

ROW_FINAL = (
    "| main_ok | benchmark | results/benchmark/main_run_clean | sql_positive "
    "| paper_final | true | clean run |"
)
ROW_DIAGNOSTIC = (
    "| diag_shadow | benchmark | results/benchmark/city_shadow_spl10 | sql_positive "
    "| diagnostic_only | false | shadow only |"
)
ROW_PENDING = (
    "| pending_scope | benchmark | results/benchmark/pending_run | sql_positive "
    "| pending_review | false | keep-note |"
)
PENDING_PROSE = "See results/benchmark/pending_run for the raw run directory."


def _promo_doc(rows: list[str]) -> str:
    body = "\n".join([PROMOTION_HEADER, PROMOTION_SEPARATOR, *rows])
    return f"# Registry\n\n{NON_PROMOTION_TABLE}\n{body}\n\n{PENDING_PROSE}\n"


def _row(
    scope: str,
    artifact_type: str,
    artifact_path: str,
    family: str,
    status: str,
    allowed: str,
) -> PromotionRow:
    return PromotionRow.from_cells(
        {
            "scope": scope,
            "artifact_type": artifact_type,
            "artifact_path": artifact_path,
            "evidence_family": family,
            "status": status,
            "paper_metric_allowed": allowed,
        }
    )


def test_parse_promotion_registry_ignores_non_promotion_tables() -> None:
    assert parse_promotion_registry(f"# Doc\n\n{NON_PROMOTION_TABLE}") == []
    rows = parse_promotion_registry(_promo_doc([ROW_FINAL, ROW_DIAGNOSTIC]))
    assert len(rows) == 2
    assert rows[0]["scope"] == "main_ok"
    assert rows[0]["status"] == "paper_final"
    assert rows[1]["scope"] == "diag_shadow"
    assert rows[1]["status"] == "diagnostic_only"
    for row in rows:
        assert set(row) == set(PROMOTION_REQUIRED_COLUMNS)


def test_forbidden_final_marker_rejects_smoke_spl_and_diagnostic_paths(
    tmp_path: Path,
) -> None:
    assert has_forbidden_final_marker("results/benchmark/20260621_run_smoke")
    assert has_forbidden_final_marker("results/benchmark/phase7_promptdiverse_adopt_spl10")
    assert has_forbidden_final_marker("results/benchmark/spl15/adopt")
    assert has_forbidden_final_marker("results/benchmark/run_diagnostic")
    assert has_forbidden_final_marker("results/benchmark/dry_run/dir")
    assert has_forbidden_final_marker("results/benchmark/provider_error_part")
    assert not has_forbidden_final_marker("results/benchmark/main_local_full_400")

    smoke_row = _row(
        "bad_smoke",
        "benchmark",
        "results/benchmark/x_smoke",
        "sql_positive",
        "paper_final",
        "true",
    )
    evaluations = evaluate_promotion_rows([smoke_row], root=tmp_path, verify=False)
    assert len(evaluations) == 1
    assert evaluations[0].included is False
    assert "forbidden paper_final artifact path" in evaluations[0].exclusion_reason

    clean_row = _row(
        "clean_main",
        "benchmark",
        "results/benchmark/main_clean",
        "sql_positive",
        "paper_final",
        "true",
    )
    evaluations = evaluate_promotion_rows([clean_row], root=tmp_path, verify=False)
    assert evaluations[0].included is True
    assert evaluations[0].metrics["execution_accuracy"] == NA
    assert evaluations[0].metrics["total_evaluated"] == NA


def test_extract_metrics_missing_fields_render_as_na() -> None:
    empty = extract_benchmark_metrics({})
    assert empty["execution_accuracy"] == NA
    assert empty["valid_sql_rate"] == NA
    assert empty["total_evaluated"] == NA
    assert empty["failures"] == NA
    assert empty["deterministic_templates"] == NA

    summary = {
        "dataset": {"total_evaluated": 10},
        "metrics": {
            "execution_accuracy": {"value": 0.7, "numerator": 7, "denominator": 10},
            "valid_sql_rate": "3/4 = 0.75",
            "expected_action_accuracy": 0.5,
        },
        "latency": {"mean_ms": 100.0, "p95_ms": 250.5},
        "reliability": {"score": -1.25, "unsafe_sql": 0},
        "error_analysis": {"total_errors": 3},
        "config": {
            "module_flags": {"deterministic_templates": False},
            "max_retries": 1,
        },
    }
    metrics = extract_benchmark_metrics(summary)
    assert metrics["execution_accuracy"] == "7/10=0.7000"
    assert metrics["valid_sql_rate"] == "3/4=0.7500"
    assert metrics["expected_action_accuracy"] == "0.5000"
    assert metrics["total_evaluated"] == "10"
    assert metrics["failures"] == "3"
    assert metrics["unsafe_sql"] == "0"
    assert metrics["reliability_score"] == "-1.25"
    assert metrics["mean_latency_ms"] == "100"
    assert metrics["p95_latency_ms"] == "250.5"
    assert metrics["deterministic_templates"] == "false"
    assert metrics["max_retries"] == "1"

    judge_empty = extract_judge_metrics({})
    assert judge_empty["provider"] == NA
    assert judge_empty["semantic_business_correct"] == NA
    assert judge_empty["authoritative"] == NA

    judge_summary = {
        "provider": "openrouter",
        "model": "qwen/qwen3.6-plus",
        "prompt_version": "phase16_sql_business_logic_v1",
        "judge_policy": "semantic_user_question",
        "authoritative": True,
        "total_judged": 4,
        "verdict_counts": {"business_correct": 3, "business_incorrect": 1},
        "semantic_business_counts": {
            "correct": 3,
            "incorrect": 1,
            "provider_error": 0,
            "provider_parse_error": 0,
        },
        "redaction_policy": {"redaction_applied": True},
    }
    judge = extract_judge_metrics(judge_summary)
    assert judge["provider"] == "openrouter"
    assert judge["authoritative"] == "true"
    assert judge["total_judged"] == "4"
    assert judge["semantic_business_correct"] == "3/4=0.7500"
    assert judge["semantic_business_incorrect"] == "1/4=0.2500"
    assert judge["provider_error"] == "0"
    assert judge["provider_parse_error"] == "0"
    assert judge["redaction_applied"] == "true"


def test_render_paper_tables_sections_hashes_and_diagnostic_flag() -> None:
    final_row = _row(
        "main_ok",
        "benchmark",
        "results/benchmark/main_run_clean",
        "sql_positive",
        "paper_final",
        "true",
    )
    included = ScopeEvaluation(
        row=final_row,
        included=True,
        verification_ok=True,
        metrics={
            "total_evaluated": "400",
            "execution_accuracy": "102/394=0.2589",
            "valid_sql_rate": "295/394=0.7487",
            "failures": "298",
            "unsafe_sql": "0",
            "mean_latency_ms": "29385.6",
            "p95_latency_ms": "60832",
        },
        provenance={
            "dataset_hash": "a" * 64,
            "selected_cases_hash": "b" * 64,
            "git_commit": "6b5ddfe",
            "started_at": "2026-06-21T19:27:48+00:00",
        },
    )
    diagnostic_row = _row(
        "diag_shadow",
        "benchmark",
        "results/benchmark/city_shadow_spl10",
        "sql_positive",
        "diagnostic_only",
        "false",
    )
    diagnostic = ScopeEvaluation(
        row=diagnostic_row,
        included=False,
        exclusion_reason="status=diagnostic_only",
    )

    plain = render_paper_tables(
        [included, diagnostic],
        generated_date="2026-08-22",
        registry_display="docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md",
    )
    assert "# PARS-SQL Paper Table Pack" in plain
    assert "## Strict SQL-positive benchmark results (sql_positive)" in plain
    assert "## Behavioral expected-action benchmark results (behavioral)" not in plain
    assert "## Semantic/business judge audit (semantic_business)" not in plain
    assert "## Reporting constraints" in plain
    assert "dataset_hash (sha256-16)" in plain
    assert "selected_cases_hash (sha256-16)" in plain
    assert "a" * 16 in plain
    assert "b" * 16 in plain
    assert "main_ok" in plain
    assert "102/394=0.2589" in plain
    assert "diag_shadow" not in plain

    flagged = render_paper_tables(
        [included, diagnostic],
        generated_date="2026-08-22",
        registry_display="docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md",
        include_diagnostic=True,
    )
    assert "## Diagnostic evidence (not paper-final)" in flagged
    assert "diag_shadow" in flagged
    assert "status=diagnostic_only" in flagged


def test_set_promotion_status_updates_exactly_one_row_cell_pair() -> None:
    doc = _promo_doc([ROW_PENDING, ROW_FINAL])
    updated = set_promotion_status(
        doc,
        artifact_path="results\\benchmark\\pending_run",
        new_status="paper_final",
        paper_metric_allowed=True,
    )
    old_lines = doc.splitlines()
    new_lines = updated.splitlines()
    assert len(old_lines) == len(new_lines)
    changed = [index for index in range(len(old_lines)) if old_lines[index] != new_lines[index]]
    assert changed == [old_lines.index(ROW_PENDING)]
    rewritten = new_lines[changed[0]]
    assert "| paper_final | true |" in rewritten
    assert "keep-note" in rewritten
    assert ROW_FINAL in new_lines
    assert PENDING_PROSE in new_lines

    ambiguous_doc = _promo_doc([ROW_PENDING, ROW_PENDING.replace("pending_scope", "twin")])
    with pytest.raises(ValueError, match="Ambiguous"):
        set_promotion_status(
            ambiguous_doc,
            artifact_path="results/benchmark/pending_run",
            new_status="paper_final",
            paper_metric_allowed=True,
        )
    with pytest.raises(ValueError, match="No promotion registry row"):
        set_promotion_status(
            doc,
            artifact_path="results/benchmark/unknown_dir",
            new_status="diagnostic_only",
            paper_metric_allowed=False,
        )
    with pytest.raises(ValueError, match="cannot allow paper metrics"):
        set_promotion_status(
            doc,
            artifact_path="results/benchmark/pending_run",
            new_status="pending_review",
            paper_metric_allowed=True,
        )


def test_build_manifest_payload_records_scopes_and_constraints() -> None:
    final_row = _row(
        "main_ok",
        "benchmark",
        "results/benchmark/main_run_clean",
        "sql_positive",
        "paper_final",
        "true",
    )
    included = ScopeEvaluation(
        row=final_row,
        included=True,
        verification_ok=True,
        metrics={"execution_accuracy": "102/394=0.2589"},
        provenance={"dataset_hash": "a" * 64, "selected_cases_hash": "b" * 64},
    )
    diagnostic_row = _row(
        "diag_shadow",
        "benchmark",
        "results/benchmark/city_shadow_spl10",
        "sql_positive",
        "diagnostic_only",
        "false",
    )
    diagnostic = ScopeEvaluation(
        row=diagnostic_row,
        included=False,
        exclusion_reason="status=diagnostic_only",
    )
    payload = build_manifest_payload(
        [included, diagnostic],
        generated_date="2026-08-22",
        registry_display="docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md",
        registry_sha256="deadbeef",
        include_diagnostic=False,
    )
    assert payload["status"] == "artifact_backed_paper_pack"
    assert payload["included_scopes"] == ["main_ok"]
    assert payload["excluded_scopes"] == [
        {"scope": "diag_shadow", "reason": "status=diagnostic_only"}
    ]
    assert payload["source_registry_sha256"] == "deadbeef"
    scope_entry = payload["scopes"]["main_ok"]
    assert scope_entry["included"] is True
    assert scope_entry["verification_ok"] is True
    assert scope_entry["provenance"]["dataset_hash"] == "a" * 64
    assert scope_entry["metrics"]["execution_accuracy"] == "102/394=0.2589"
    assert payload["reporting_constraints"]
