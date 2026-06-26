import csv
import pandas as pd
from pathlib import Path
from typing import Any, List, Dict

def export_benchmark_csvs(records: List[Dict[str, Any]], summary: Dict[str, Any], output_dir: Path, *, prefix: str | None = None):
    """Export benchmark results to CSV for external analysis."""
    name_prefix = f"{prefix}_" if prefix else ""
    
    # 1. benchmark_results.csv (Flattened predictions)
    results_path = output_dir / f"{name_prefix}benchmark_results.csv"
    df_results = pd.DataFrame(records)
    # Drop large nested fields for CSV
    cols_to_drop = ["retrieved", "attempts", "schema_context", "qir"]
    df_results = df_results.drop(columns=[c for c in cols_to_drop if c in df_results.columns])
    df_results.to_csv(results_path, index=False, encoding="utf-8-sig")

    # 2. reliability_summary.csv
    rel_path = output_dir / f"{name_prefix}reliability_summary.csv"
    rel_data = summary.get("reliability", {})
    if rel_data:
        pd.DataFrame([rel_data]).to_csv(rel_path, index=False, encoding="utf-8-sig")

    # 3. error_taxonomy.csv
    err_path = output_dir / f"{name_prefix}error_taxonomy.csv"
    err_data = summary.get("error_analysis", {}).get("by_error", {})
    err_rows = [{"error_type": k, "count": v} for k, v in err_data.items()]
    pd.DataFrame(err_rows, columns=["error_type", "count"]).to_csv(err_path, index=False, encoding="utf-8-sig")

def generate_paper_tables(summary: Dict[str, Any], output_path: Path):
    """Generate paper-ready markdown tables."""
    lines = ["# Paper Tables (Auto-generated)", ""]
    config = summary.get("config", {})
    if config:
        lines.append("## Configuration")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|---|---|")
        for key in ("model_name", "model_slug", "ablation_id", "enabled_modules", "disabled_modules", "dataset", "selection_policy"):
            if key in config:
                lines.append(f"| {key} | {config.get(key)} |")
        lines.append("")
    
    # Table 1: Core Performance
    lines.append("## Table 1: End-to-End Performance")
    lines.append("")
    lines.append("| Metric | Value | Description |")
    lines.append("|---|---:|---|")
    metrics = summary.get("metrics", {})
    for m_name, m_val in metrics.items():
        val = m_val.get("value", 0)
        ci = m_val.get("ci95")
        rendered = f"{val:.4f}"
        if ci:
            rendered = f"{rendered} [{ci.get('lower')}, {ci.get('upper')}]"
        lines.append(f"| {m_name} | {rendered} | {m_val.get('description', '')} |")
    lines.append("")

    # Table 2: Reliability & Abstention
    lines.append("## Table 2: Reliability Metrics")
    lines.append("")
    lines.append("| Reliability Metric | Value |")
    lines.append("|---|---:|")
    reliability = summary.get("reliability", {})
    for k, v in reliability.items():
        lines.append(f"| {k} | {v} |")
    lines.append("")

    latency = summary.get("latency", {})
    if latency:
        lines.append("## Table 3: Latency")
        lines.append("")
        lines.append("| Latency Metric | Value |")
        lines.append("|---|---:|")
        for k, v in latency.items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
