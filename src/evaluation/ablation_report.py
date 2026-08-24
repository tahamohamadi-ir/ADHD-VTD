from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import read_json, write_json


def _first_file(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"Missing required file {pattern!r} under {root}")
    return matches[0]


def _metric(summary: dict[str, Any], name: str) -> Any:
    value = summary.get("metrics", {}).get(name)
    if isinstance(value, dict):
        return value.get("value")
    return None


def _row_from_job(job: dict[str, Any]) -> dict[str, Any]:
    if job.get("result_status") != "completed" or not job.get("artifact_dir"):
        return {
            "config_id": job.get("config_id"),
            "result_status": job.get("result_status"),
            "artifact_dir": job.get("artifact_dir"),
            "complete": False,
        }

    artifact_dir = Path(job["artifact_dir"])
    summary_path = _first_file(artifact_dir, "*_summary.json")
    summary = read_json(summary_path)
    config = summary.get("config", {})
    runtime_contract = config.get("ablation_runtime_contract") or job.get("runtime_contract", {})
    if config.get("mode") == "retrieval":
        runtime_contract = job.get("runtime_contract") or runtime_contract
    return {
        "config_id": job.get("config_id"),
        "ablation_id": job.get("ablation_id"),
        "result_status": job.get("result_status"),
        "artifact_dir": str(artifact_dir),
        "summary_path": str(summary_path),
        "complete": True,
        "evaluated": summary.get("dataset", {}).get("total_evaluated"),
        "execution_accuracy": _metric(summary, "execution_accuracy"),
        "valid_sql_rate": _metric(summary, "valid_sql_rate"),
        "reliability_score": summary.get("reliability", {}).get("score"),
        "unsafe_sql": summary.get("reliability", {}).get("unsafe_sql"),
        "retrieval_hit_rate": _metric(summary, "retrieval_hit_rate"),
        "retrieval_miss_rate": _metric(summary, "retrieval_miss_rate"),
        "latency_mean_ms": summary.get("latency", {}).get("mean_ms"),
        "latency_p95_ms": summary.get("latency", {}).get("p95_ms"),
        "benchmark_mode": config.get("mode"),
        "retrieval_backend": config.get("retrieval_backend"),
        "retrieval_reranker": config.get("retrieval_reranker"),
        "dataset_hash": summary.get("config", {}).get("dataset_hash"),
        "selected_cases_hash": summary.get("config", {}).get("selected_cases_hash"),
        "module_flags": summary.get("config", {}).get("module_flags", {}),
        "runtime_contract": runtime_contract,
    }


def build_ablation_comparison(manifest_path: str | Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    manifest = read_json(manifest_path)
    rows = [_row_from_job(job) for job in manifest.get("jobs", [])]
    complete_rows = [row for row in rows if row.get("complete")]
    selected_hashes = sorted({str(row.get("selected_cases_hash")) for row in complete_rows})
    dataset_hashes = sorted({str(row.get("dataset_hash")) for row in complete_rows})
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "manifest_path": str(manifest_path),
        "jobs_total": len(rows),
        "jobs_completed": len(complete_rows),
        "same_selected_cases_hash": len(selected_hashes) == 1,
        "same_dataset_hash": len(dataset_hashes) == 1,
        "selected_cases_hashes": selected_hashes,
        "dataset_hashes": dataset_hashes,
        "rows": rows,
        "limitations": [
            "This is a smoke ablation unless the source run size says otherwise.",
            "Metrics are copied from real benchmark summary artifacts only.",
            "No semantic/business correctness is inferred without Phase 16 judgment artifacts.",
            "Paired significance is not reported here; use paired tests only when case IDs match.",
        ],
    }


def render_ablation_comparison(report: dict[str, Any]) -> str:
    complete_rows = [row for row in report["rows"] if row.get("complete")]
    all_retrieval = bool(complete_rows) and all(
        row.get("benchmark_mode") == "retrieval" for row in complete_rows
    )
    title = (
        "Phase 11 Retrieval Ablation Comparison"
        if all_retrieval
        else "Phase 11 A0-A7 Ablation Comparison"
    )
    lines = [
        f"# {title}",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        "## Source",
        "",
        f"- manifest: `{report['manifest_path']}`",
        f"- jobs_total: `{report['jobs_total']}`",
        f"- jobs_completed: `{report['jobs_completed']}`",
        f"- same_dataset_hash: `{report['same_dataset_hash']}`",
        f"- same_selected_cases_hash: `{report['same_selected_cases_hash']}`",
        "",
        "## Anti-Fake / Anti-Overfit Statement",
        "",
        "This comparison reads only existing benchmark artifacts listed in the manifest. It does not run a model, edit predictions, fill missing metrics, or infer semantic judge labels.",
        "",
        "## Metrics",
        "",
    ]
    if all_retrieval:
        lines.extend(
            [
                "| Config | Backend | Reranker | Evaluated | Retrieval Hit Rate | Retrieval Miss Rate | Mean Latency ms | P95 Latency ms |",
                "|---|---|---|---:|---:|---:|---:|---:|",
            ]
        )
    else:
        lines.extend(
            [
                "| Config | Evaluated | EX | Valid SQL | Reliability | Unsafe SQL | Mean Latency ms | P95 Latency ms |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
    for row in report["rows"]:
        if not row.get("complete"):
            lines.append(f"| {row.get('config_id')} | incomplete |  |  |  |  |  |  |")
            continue
        if all_retrieval:
            lines.append(
                "| {config_id} | {retrieval_backend} | {retrieval_reranker} | {evaluated} | "
                "{retrieval_hit_rate} | {retrieval_miss_rate} | {latency_mean_ms} | {latency_p95_ms} |".format(
                    **{**row, "retrieval_reranker": row.get("retrieval_reranker") or "none"}
                )
            )
        else:
            lines.append(
                "| {config_id} | {evaluated} | {execution_accuracy} | {valid_sql_rate} | "
                "{reliability_score} | {unsafe_sql} | {latency_mean_ms} | {latency_p95_ms} |".format(
                    **row
                )
            )
    lines.extend(
        [
            "",
            "## Runtime Contract",
            "",
            "| Config | Runtime Enforced | Runtime Locked | Runtime Parameters | Metadata Only | Warnings |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        contract = row.get("runtime_contract") or {}
        enforced = ", ".join(
            f"{k}={v}" for k, v in (contract.get("runtime_enforced") or {}).items()
        )
        locked = ", ".join(f"{k}={v}" for k, v in (contract.get("runtime_locked") or {}).items())
        runtime_parameters = (
            ", ".join(f"{k}={v}" for k, v in (contract.get("runtime_parameters") or {}).items())
            or "none"
        )
        metadata_only = (
            ", ".join(f"{k}={v}" for k, v in (contract.get("metadata_only") or {}).items())
            or "none"
        )
        warnings = "; ".join(contract.get("warnings") or []) or "none"
        lines.append(
            f"| {row.get('config_id')} | {enforced} | {locked} | {runtime_parameters} | {metadata_only} | {warnings} |"
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def write_ablation_comparison(
    manifest_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Path]:
    manifest_path = Path(manifest_path)
    output_root = Path(output_dir) if output_dir else manifest_path.parent
    output_root.mkdir(parents=True, exist_ok=True)
    report = build_ablation_comparison(manifest_path)
    summary_path = write_json(output_root / "ablation_comparison.json", report)
    markdown_path = output_root / "ablation_comparison.md"
    markdown_path.write_text(render_ablation_comparison(report), encoding="utf-8")
    return {"summary": summary_path, "report": markdown_path}
