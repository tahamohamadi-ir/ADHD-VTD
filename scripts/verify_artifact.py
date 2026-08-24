from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
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

_POLICY_BLOCKING_LABELS = {
    "adjudication_required",
    "partial_business_match",
    "partial_or_mixed",
    "unjudged",
}
_SEMANTIC_POLICY_LABELS = {
    "correct",
    "incorrect",
    "partial_business_match",
    "adjudication_required",
}
_STRICT_POLICY_LABELS = _SEMANTIC_POLICY_LABELS
_COMBINED_POLICY_LABELS = {
    "both_correct",
    "both_incorrect",
    "semantic_correct_strict_incorrect",
    "semantic_incorrect_strict_correct",
    "partial_or_mixed",
    "adjudication_required",
}


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
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_dataset_path(raw_path: Any, run_dir: Path) -> Path:
    path = Path(str(raw_path))
    if path.is_absolute():
        return path
    candidates = (PROJECT_ROOT / path, run_dir / path)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _write_issue(issues: list[ArtifactIssue], code: str, message: str) -> None:
    issues.append(ArtifactIssue(code=code, message=message))


def _path_from_summary(run_dir: Path, summary: dict[str, Any], key: str) -> Path | None:
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts.get(key):
        return None
    raw_path = Path(str(artifacts[key]))
    if raw_path.is_absolute():
        return raw_path

    candidates = (
        run_dir / raw_path,
        PROJECT_ROOT / raw_path,
        run_dir / raw_path.name,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


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


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _positive_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    counts: dict[str, int] = {}
    for label, count in value.items():
        coerced = _coerce_int(count)
        if coerced is not None and coerced > 0:
            counts[str(label)] = coerced
    return counts


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {label: count for label, count in sorted(counter.items()) if count > 0}


def _policy_label(value: Any) -> str:
    return str(value or "").strip()


def _pending_import_status(root: Path) -> str | None:
    import_summary_path = root / "candidate_adoption_review_import_summary.json"
    if not import_summary_path.exists():
        return None
    try:
        summary = _load_json(import_summary_path)
    except Exception:
        return "invalid_import_summary"
    return str(summary.get("status") or "unknown")


def _verify_dual_policy_artifact(
    issues: list[ArtifactIssue],
    checked: dict[str, Any],
    dual_policy_dir: str | Path | None,
) -> None:
    if not dual_policy_dir:
        return

    root = Path(dual_policy_dir)
    summary_path = root / "dual_policy_summary.json"
    cases_path = root / "dual_policy_cases.jsonl"
    checked["dual_policy"] = {
        "dir": str(root),
        "summary": str(summary_path),
        "cases": str(cases_path),
    }

    if not root.exists() or not root.is_dir():
        _write_issue(
            issues,
            "DUAL_POLICY_DIR_MISSING",
            f"Dual-policy artifact directory not found: {root}",
        )
        return

    pending_status = _pending_import_status(root)
    if pending_status and pending_status != "complete":
        _write_issue(
            issues,
            "DUAL_POLICY_PENDING_REVIEW",
            f"Candidate review import is not complete: status={pending_status}.",
        )

    if not summary_path.exists():
        _write_issue(
            issues,
            "DUAL_POLICY_SUMMARY_MISSING",
            f"dual_policy_summary.json is required in {root}.",
        )
        return
    if not cases_path.exists():
        _write_issue(
            issues,
            "DUAL_POLICY_CASES_MISSING",
            f"dual_policy_cases.jsonl is required in {root}.",
        )
        return

    try:
        summary = _load_json(summary_path)
    except Exception as exc:
        _write_issue(
            issues, "DUAL_POLICY_SUMMARY_INVALID", f"Cannot parse dual policy summary: {exc}"
        )
        return
    try:
        cases = _load_jsonl(cases_path)
    except Exception as exc:
        _write_issue(issues, "DUAL_POLICY_CASES_INVALID", f"Cannot parse dual policy cases: {exc}")
        return

    common_cases = _coerce_int(summary.get("common_cases"))
    authoritative = summary.get("authoritative") is True
    checked["dual_policy"].update(
        {
            "authoritative": authoritative,
            "common_cases": common_cases,
            "case_count": len(cases),
        }
    )

    if not authoritative:
        _write_issue(
            issues,
            "DUAL_POLICY_NOT_AUTHORITATIVE",
            "Dual-policy evidence must be marked authoritative before final verification.",
        )
    if common_cases is None or common_cases <= 0:
        _write_issue(
            issues,
            "DUAL_POLICY_COMMON_CASES_MISSING",
            "Dual-policy summary must record a positive common_cases count.",
        )
    elif common_cases != len(cases):
        _write_issue(
            issues,
            "DUAL_POLICY_CASE_COUNT_MISMATCH",
            f"dual_policy_cases count {len(cases)} does not match common_cases {common_cases}.",
        )

    expected_fields = {
        "semantic_policy_label": _SEMANTIC_POLICY_LABELS,
        "strict_policy_label": _STRICT_POLICY_LABELS,
        "combined_label": _COMBINED_POLICY_LABELS,
    }
    invalid_labels: dict[str, set[str]] = {field: set() for field in expected_fields}
    missing_fields: dict[str, int] = {field: 0 for field in expected_fields}
    derived_counts: dict[str, Counter[str]] = {
        "semantic_counts": Counter(),
        "strict_counts": Counter(),
        "combined_counts": Counter(),
    }

    for row in cases:
        for field_name, allowed in expected_fields.items():
            label = _policy_label(row.get(field_name))
            if not label:
                missing_fields[field_name] += 1
                continue
            if label not in allowed:
                invalid_labels[field_name].add(label)
            if field_name == "semantic_policy_label":
                derived_counts["semantic_counts"][label] += 1
            elif field_name == "strict_policy_label":
                derived_counts["strict_counts"][label] += 1
            else:
                derived_counts["combined_counts"][label] += 1

    missing = {field: count for field, count in missing_fields.items() if count}
    if missing:
        _write_issue(
            issues,
            "DUAL_POLICY_LABEL_MISSING",
            f"Dual-policy case labels are missing: {missing}.",
        )
    invalid = {field: sorted(labels) for field, labels in invalid_labels.items() if labels}
    if invalid:
        _write_issue(
            issues,
            "DUAL_POLICY_LABEL_INVALID",
            f"Dual-policy case labels contain unsupported values: {invalid}.",
        )

    blocking_counts: dict[str, int] = {}
    for group_name, counter in derived_counts.items():
        for label, count in counter.items():
            if label in _POLICY_BLOCKING_LABELS and count > 0:
                blocking_counts[f"{group_name}.{label}"] = count

    for group_name, counter in derived_counts.items():
        summary_counts = _positive_counts(summary.get(group_name))
        if not summary_counts:
            _write_issue(
                issues,
                "DUAL_POLICY_COUNTS_MISSING",
                f"Dual-policy summary must include positive {group_name}.",
            )
            continue
        if summary_counts != _counter_dict(counter):
            _write_issue(
                issues,
                "DUAL_POLICY_COUNTS_MISMATCH",
                f"{group_name} {summary_counts} does not match derived counts {_counter_dict(counter)}.",
            )
        for label, count in summary_counts.items():
            if label in _POLICY_BLOCKING_LABELS and count > 0:
                blocking_counts[f"{group_name}.{label}"] = count

    checked["dual_policy"]["blocking_counts"] = blocking_counts
    if blocking_counts:
        _write_issue(
            issues,
            "DUAL_POLICY_INCOMPLETE_LABELS",
            f"Dual-policy evidence still contains unresolved labels: {blocking_counts}.",
        )


def verify_artifact(
    artifact_dir: str | Path,
    *,
    manifest_path: str | Path | None = None,
    dual_policy_dir: str | Path | None = None,
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

    dataset_path_raw = config.get("dataset_path")
    expected_dataset_hash = config.get("dataset_hash")
    if dataset_path_raw and expected_dataset_hash:
        dataset_path = _resolve_dataset_path(dataset_path_raw, run_dir)
        checked["dataset_path"] = str(dataset_path)
        checked["dataset_path_exists"] = dataset_path.exists() and dataset_path.is_file()
        if not checked["dataset_path_exists"]:
            _write_issue(
                issues,
                "DATASET_PATH_MISSING",
                f"Config dataset_path cannot be verified: {dataset_path}",
            )
        else:
            current_dataset_hash = _sha256_file(dataset_path)
            checked["current_dataset_hash"] = current_dataset_hash
            if current_dataset_hash != expected_dataset_hash:
                _write_issue(
                    issues,
                    "DATASET_HASH_DRIFT",
                    "Current dataset file hash does not match artifact config dataset_hash.",
                )

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

    _verify_dual_policy_artifact(issues, checked, dual_policy_dir)

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
        "--dual-policy-dir",
        help=(
            "Optional dual-policy evidence directory. When provided, it must contain "
            "authoritative and complete dual_policy_summary/cases artifacts."
        ),
    )
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
        dual_policy_dir=args.dual_policy_dir,
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
