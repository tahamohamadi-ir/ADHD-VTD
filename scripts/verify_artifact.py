from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.metrics import (
    has_generated_sql,
    is_execution_correct,
    is_sql_positive,
    is_unsafe_sql,
    is_valid_sql,
)


@dataclass(frozen=True)
class ArtifactIssue:
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class ArtifactVerificationReport:
    artifact_dir: str
    ok: bool
    issues: list[ArtifactIssue] = field(default_factory=list)
    checked: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_dir": self.artifact_dir,
            "ok": self.ok,
            "issues": [issue.as_dict() for issue in self.issues],
            "checked": self.checked,
        }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            rows.append(row)
    return rows


def _write_issue(issues: list[ArtifactIssue], code: str, message: str) -> None:
    issues.append(ArtifactIssue(code=code, message=message))


def _path_from_summary(run_dir: Path, summary: dict[str, Any], key: str) -> Path | None:
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts.get(key):
        return None
    raw_path = Path(str(artifacts[key]))
    return raw_path if raw_path.is_absolute() else run_dir / raw_path


def _find_one(run_dir: Path, pattern: str) -> Path | None:
    matches = sorted(path for path in run_dir.glob(pattern) if path.is_file())
    return matches[0] if matches else None


def _artifact_path(
    run_dir: Path,
    summary: dict[str, Any],
    key: str,
    fallback_pattern: str,
) -> Path | None:
    return _path_from_summary(run_dir, summary, key) or _find_one(run_dir, fallback_pattern)


def _metric(summary: dict[str, Any], name: str) -> dict[str, Any] | None:
    metric = summary.get("metrics", {}).get(name)
    return metric if isinstance(metric, dict) else None


def _metric_pair(summary: dict[str, Any], name: str) -> tuple[int | None, int | None]:
    metric = _metric(summary, name)
    if metric is None:
        return None, None
    numerator = metric.get("numerator")
    denominator = metric.get("denominator")
    return (
        int(numerator) if numerator is not None else None,
        int(denominator) if denominator is not None else None,
    )


def _prediction_is_failure(record: dict[str, Any]) -> bool:
    return not bool(
        record.get("ok") or record.get("execution_correct") or record.get("result_match")
    )


def _prediction_is_valid_sql(record: dict[str, Any]) -> bool:
    return is_valid_sql(record)


def _prediction_is_execution_correct(record: dict[str, Any]) -> bool:
    return is_execution_correct(record)


def _prediction_is_unsafe(record: dict[str, Any]) -> bool:
    return is_unsafe_sql(record)


def _summary_total(summary: dict[str, Any]) -> int | None:
    candidates = [
        summary.get("total_evaluated"),
        (
            summary.get("dataset", {}).get("total_evaluated")
            if isinstance(summary.get("dataset"), dict)
            else None
        ),
    ]
    for value in candidates:
        if value is not None:
            return int(value)
    return None


def _summary_failures(summary: dict[str, Any]) -> int | None:
    candidates = [
        summary.get("failures"),
        summary.get("failure_count"),
        (
            summary.get("dataset", {}).get("failures")
            if isinstance(summary.get("dataset"), dict)
            else None
        ),
        (
            summary.get("dataset", {}).get("failure_count")
            if isinstance(summary.get("dataset"), dict)
            else None
        ),
    ]
    for value in candidates:
        if value is not None:
            return int(value)
    return None


def _summary_unsafe_sql(summary: dict[str, Any]) -> int | None:
    reliability = summary.get("reliability")
    candidates = [
        summary.get("unsafe_sql"),
        reliability.get("unsafe_sql") if isinstance(reliability, dict) else None,
    ]
    for value in candidates:
        if value is not None:
            return int(value)
    return None


def _config(summary: dict[str, Any], config_file: dict[str, Any] | None) -> dict[str, Any]:
    summary_config = summary.get("config")
    if isinstance(summary_config, dict):
        return summary_config
    return config_file or {}


def _module_flags(config: dict[str, Any]) -> dict[str, Any]:
    flags = config.get("module_flags")
    return flags if isinstance(flags, dict) else {}


def _deterministic_templates_value(config: dict[str, Any]) -> bool | None:
    flags = _module_flags(config)
    if "deterministic_templates" in flags:
        return bool(flags["deterministic_templates"])
    if "deterministic_templates" in config:
        return bool(config["deterministic_templates"])
    return None


def _run_identity(run_dir: Path, summary: dict[str, Any], config: dict[str, Any]) -> list[str]:
    values = [run_dir.name, str(run_dir)]
    for key in ("run_id", "config_id", "ablation_id"):
        value = summary.get(key) or config.get(key)
        if value:
            values.append(str(value))
    return values


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for child in value.values():
            strings.extend(_walk_strings(child))
        return strings
    if isinstance(value, list):
        strings = []
        for child in value:
            strings.extend(_walk_strings(child))
        return strings
    return []


def _manifest_contains_entry(
    manifest: dict[str, Any],
    run_dir: Path,
    summary: dict[str, Any],
    config: dict[str, Any],
) -> bool:
    identities = [
        value.lower().replace("\\", "/") for value in _run_identity(run_dir, summary, config)
    ]
    strings = [value.lower().replace("\\", "/") for value in _walk_strings(manifest)]
    return any(identity and any(identity in item for item in strings) for identity in identities)


def _find_manifest(run_dir: Path, manifest_path: str | Path | None) -> Path | None:
    if manifest_path:
        return Path(manifest_path)
    for pattern in ("manifest.json", "artifact_manifest.json", "*_manifest.json"):
        found = _find_one(run_dir, pattern)
        if found:
            return found
    return None


def _is_smoke_run(run_dir: Path, summary: dict[str, Any], config: dict[str, Any]) -> bool:
    values = [
        run_dir.name,
        str(summary.get("run_type") or ""),
        str(summary.get("status") or ""),
        str(config.get("config_id") or ""),
        str(config.get("ablation_id") or ""),
        str(config.get("run_type") or ""),
    ]
    return any("smoke" in value.lower() for value in values)


def _check_required_file(
    issues: list[ArtifactIssue],
    checked: dict[str, Any],
    key: str,
    path: Path | None,
) -> None:
    checked[key] = str(path) if path else None
    if path is None or not path.exists():
        _write_issue(issues, f"{key.upper()}_MISSING", f"Required artifact file is missing: {key}")


def verify_artifact(
    artifact_dir: str | Path,
    *,
    manifest_path: str | Path | None = None,
    allow_smoke: bool = False,
) -> ArtifactVerificationReport:
    run_dir = Path(artifact_dir)
    issues: list[ArtifactIssue] = []
    checked: dict[str, Any] = {}

    if not run_dir.exists() or not run_dir.is_dir():
        return ArtifactVerificationReport(
            artifact_dir=str(run_dir),
            ok=False,
            issues=[
                ArtifactIssue("ARTIFACT_DIR_MISSING", f"Artifact directory not found: {run_dir}")
            ],
            checked={},
        )

    summary_path = _find_one(run_dir, "*_summary.json") or _find_one(run_dir, "summary.json")
    _check_required_file(issues, checked, "summary_json", summary_path)
    if summary_path is None or not summary_path.exists():
        return ArtifactVerificationReport(str(run_dir), False, issues, checked)

    try:
        summary = _load_json(summary_path)
    except Exception as exc:
        _write_issue(issues, "SUMMARY_JSON_INVALID", f"Cannot parse summary JSON: {exc}")
        return ArtifactVerificationReport(str(run_dir), False, issues, checked)

    config_path = _artifact_path(run_dir, summary, "config", "*_config.json")
    predictions_path = _artifact_path(run_dir, summary, "predictions", "*_predictions.jsonl")
    failures_path = _artifact_path(run_dir, summary, "failures", "*_failures.jsonl")
    summary_md_path = _artifact_path(run_dir, summary, "summary_md", "*_summary.md")
    benchmark_csv_path = _artifact_path(
        run_dir, summary, "benchmark_results_csv", "*_benchmark_results.csv"
    )

    for key, path in (
        ("config", config_path),
        ("predictions", predictions_path),
        ("failures", failures_path),
        ("summary_md", summary_md_path),
        ("benchmark_results_csv", benchmark_csv_path),
    ):
        _check_required_file(issues, checked, key, path)

    config_file: dict[str, Any] | None = None
    if config_path is not None and config_path.exists():
        try:
            config_file = _load_json(config_path)
        except Exception as exc:
            _write_issue(issues, "CONFIG_INVALID", f"Cannot parse config JSON: {exc}")

    config = _config(summary, config_file)
    manifest_file = _find_manifest(run_dir, manifest_path)
    checked["manifest"] = str(manifest_file) if manifest_file else None
    if manifest_file is None or not manifest_file.exists():
        _write_issue(issues, "MANIFEST_MISSING", "A manifest file or --manifest path is required.")
    else:
        try:
            manifest = _load_json(manifest_file)
            if not _manifest_contains_entry(manifest, run_dir, summary, config):
                _write_issue(
                    issues,
                    "MANIFEST_ENTRY_MISSING",
                    "Manifest does not contain an entry for this artifact run.",
                )
        except Exception as exc:
            _write_issue(issues, "MANIFEST_INVALID", f"Cannot parse manifest JSON: {exc}")

    predictions: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    if predictions_path is not None and predictions_path.exists():
        try:
            predictions = _load_jsonl(predictions_path)
        except Exception as exc:
            _write_issue(issues, "PREDICTIONS_INVALID", f"Cannot parse predictions JSONL: {exc}")
    if failures_path is not None and failures_path.exists():
        try:
            failures = _load_jsonl(failures_path)
        except Exception as exc:
            _write_issue(issues, "FAILURES_INVALID", f"Cannot parse failures JSONL: {exc}")

    summary_total = _summary_total(summary)
    if summary_total is None:
        _write_issue(issues, "SUMMARY_TOTAL_MISSING", "Summary must record total_evaluated.")
    elif predictions and len(predictions) != summary_total:
        _write_issue(
            issues,
            "PREDICTION_COUNT_MISMATCH",
            f"Predictions count {len(predictions)} does not match summary total {summary_total}.",
        )

    derived_failures = [record for record in predictions if _prediction_is_failure(record)]
    if predictions and len(failures) != len(derived_failures):
        _write_issue(
            issues,
            "FAILURE_FILE_COUNT_MISMATCH",
            f"Failures file count {len(failures)} does not match derived failures {len(derived_failures)}.",
        )
    summary_failures = _summary_failures(summary)
    if summary_failures is not None and predictions and summary_failures != len(derived_failures):
        _write_issue(
            issues,
            "SUMMARY_FAILURE_COUNT_MISMATCH",
            f"Summary failures {summary_failures} does not match derived failures {len(derived_failures)}.",
        )

    mode = str(config.get("mode") or "").lower()
    if mode != "retrieval" and predictions:
        sql_positive = [record for record in predictions if is_sql_positive(record)]
        attempted = [record for record in sql_positive if has_generated_sql(record)]
        missing_count = len(sql_positive) - len(attempted)
        ex_numerator = sum(1 for record in attempted if _prediction_is_execution_correct(record))
        conservative_ex_numerator = sum(
            1 for record in sql_positive if _prediction_is_execution_correct(record)
        )
        valid_numerator = sum(1 for record in attempted if _prediction_is_valid_sql(record))
        invalid_count = len(attempted) - valid_numerator
        result_mismatch_count = sum(
            1
            for record in attempted
            if str(record.get("error") or "").upper() == "RESULT_MISMATCH"
            or (_prediction_is_valid_sql(record) and not _prediction_is_execution_correct(record))
        )
        uses_attempted_metric_contract = any(
            _metric(summary, name) is not None
            for name in (
                "attempted_sql_count",
                "missing_sql_count",
                "conservative_execution_accuracy",
            )
        )
        denominator = len(attempted) if uses_attempted_metric_contract else len(sql_positive)

        metric_num, metric_den = _metric_pair(summary, "execution_accuracy")
        if metric_num is None or metric_den is None:
            _write_issue(
                issues,
                "EXECUTION_ACCURACY_METRIC_MISSING",
                "Summary metrics must include execution_accuracy numerator and denominator.",
            )
        elif (metric_num, metric_den) != (ex_numerator, denominator):
            _write_issue(
                issues,
                "EXECUTION_ACCURACY_MISMATCH",
                f"execution_accuracy is {metric_num}/{metric_den}, expected {ex_numerator}/{denominator}.",
            )

        metric_num, metric_den = _metric_pair(summary, "conservative_execution_accuracy")
        if (
            metric_num is not None
            and metric_den is not None
            and (metric_num, metric_den)
            != (
                conservative_ex_numerator,
                len(sql_positive),
            )
        ):
            _write_issue(
                issues,
                "CONSERVATIVE_EXECUTION_ACCURACY_MISMATCH",
                "conservative_execution_accuracy is "
                f"{metric_num}/{metric_den}, expected {conservative_ex_numerator}/{len(sql_positive)}.",
            )

        metric_num, metric_den = _metric_pair(summary, "valid_sql_rate")
        if metric_num is None or metric_den is None:
            _write_issue(
                issues,
                "VALID_SQL_RATE_METRIC_MISSING",
                "Summary metrics must include valid_sql_rate numerator and denominator.",
            )
        elif (metric_num, metric_den) != (valid_numerator, denominator):
            _write_issue(
                issues,
                "VALID_SQL_RATE_MISMATCH",
                f"valid_sql_rate is {metric_num}/{metric_den}, expected {valid_numerator}/{denominator}.",
            )

        metric_num, metric_den = _metric_pair(summary, "missing_sql_count")
        if (
            metric_num is not None
            and metric_den is not None
            and (metric_num, metric_den)
            != (
                missing_count,
                len(sql_positive),
            )
        ):
            _write_issue(
                issues,
                "MISSING_SQL_COUNT_MISMATCH",
                f"missing_sql_count is {metric_num}/{metric_den}, expected {missing_count}/{len(sql_positive)}.",
            )

        metric_num, metric_den = _metric_pair(summary, "invalid_sql_count")
        if (
            metric_num is not None
            and metric_den is not None
            and (metric_num, metric_den)
            != (
                invalid_count,
                len(attempted),
            )
        ):
            _write_issue(
                issues,
                "INVALID_SQL_COUNT_MISMATCH",
                f"invalid_sql_count is {metric_num}/{metric_den}, expected {invalid_count}/{len(attempted)}.",
            )

        metric_num, metric_den = _metric_pair(summary, "result_mismatch_count")
        if (
            metric_num is not None
            and metric_den is not None
            and (metric_num, metric_den)
            != (
                result_mismatch_count,
                len(attempted),
            )
        ):
            _write_issue(
                issues,
                "RESULT_MISMATCH_COUNT_MISMATCH",
                "result_mismatch_count is "
                f"{metric_num}/{metric_den}, expected {result_mismatch_count}/{len(attempted)}.",
            )

        unsafe_count = sum(1 for record in predictions if _prediction_is_unsafe(record))
        summary_unsafe = _summary_unsafe_sql(summary)
        unsafe_metric_num, unsafe_metric_den = _metric_pair(summary, "unsafe_sql_count")
        if unsafe_metric_num is not None and unsafe_metric_den is not None:
            if (unsafe_metric_num, unsafe_metric_den) != (unsafe_count, len(predictions)):
                _write_issue(
                    issues,
                    "UNSAFE_SQL_METRIC_MISMATCH",
                    f"unsafe_sql_count is {unsafe_metric_num}/{unsafe_metric_den}, expected {unsafe_count}/{len(predictions)}.",
                )
        if summary_unsafe is None:
            _write_issue(issues, "UNSAFE_SQL_COUNT_MISSING", "Summary must record unsafe_sql.")
        elif summary_unsafe != unsafe_count:
            _write_issue(
                issues,
                "UNSAFE_SQL_COUNT_MISMATCH",
                f"Summary unsafe_sql {summary_unsafe} does not match predictions {unsafe_count}.",
            )

    deterministic_templates = _deterministic_templates_value(config)
    if deterministic_templates is None:
        _write_issue(
            issues,
            "DETERMINISTIC_TEMPLATES_MISSING",
            "deterministic_templates must be explicit in config/module_flags.",
        )

    for key in ("dataset_hash", "selected_cases_hash"):
        if not config.get(key):
            _write_issue(issues, f"{key.upper()}_MISSING", f"Config must include {key}.")

    if _is_smoke_run(run_dir, summary, config) and not allow_smoke:
        _write_issue(
            issues,
            "SMOKE_RUN_NOT_FINAL",
            "Smoke runs must not be verified as final artifacts unless --allow-smoke is set.",
        )

    judge = summary.get("judge")
    config_judge = config.get("judge")
    judge_data = (
        judge if isinstance(judge, dict) else config_judge if isinstance(config_judge, dict) else {}
    )
    if (
        judge_data.get("enabled") is True
        and str(judge_data.get("provider") or "").lower() == "mock"
        and judge_data.get("authoritative") is True
    ):
        _write_issue(
            issues,
            "MOCK_JUDGE_AUTHORITATIVE",
            "Mock judge outputs must not be cited as authoritative.",
        )

    reranker_backend = str(config.get("retrieval_reranker_backend") or "").lower()
    reranker_name = str(config.get("retrieval_reranker") or "").lower()
    if reranker_backend == "identity" and reranker_name not in {"", "none", "identity"}:
        _write_issue(
            issues,
            "PLACEHOLDER_RERANKER_FINAL",
            "Identity placeholder reranker must not be cited as a real reranker.",
        )

    checked.update(
        {
            "prediction_count": len(predictions),
            "failure_count": len(failures),
            "deterministic_templates": deterministic_templates,
            "dataset_hash_present": bool(config.get("dataset_hash")),
            "selected_cases_hash_present": bool(config.get("selected_cases_hash")),
        }
    )
    return ArtifactVerificationReport(str(run_dir), not issues, issues, checked)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify benchmark artifact consistency.")
    parser.add_argument("artifact_dir", help="Benchmark artifact directory.")
    parser.add_argument("--manifest", help="Manifest JSON path containing this run.")
    parser.add_argument(
        "--allow-smoke",
        action="store_true",
        help="Allow smoke artifacts to pass smoke-run checks.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON report.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = verify_artifact(
        args.artifact_dir,
        manifest_path=args.manifest,
        allow_smoke=args.allow_smoke,
    )
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"artifact_dir={report.artifact_dir}")
        print(f"ok={report.ok}")
        for issue in report.issues:
            print(f"{issue.code}: {issue.message}")
    raise SystemExit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
