import csv
import pandas as pd
from pathlib import Path
from typing import Any, List, Dict

def export_benchmark_csvs(records: List[Dict[str, Any]], summary: Dict[str, Any], output_dir: Path):
    """Export benchmark results to CSV for external analysis."""
    
    # 1. benchmark_results.csv (Flattened predictions)
    results_path = output_dir / "benchmark_results.csv"
    df_results = pd.DataFrame(records)
    # Drop large nested fields for CSV
    cols_to_drop = ["retrieved", "attempts", "schema_context", "qir"]
    df_results = df_results.drop(columns=[c for c in cols_to_drop if c in df_results.columns])
    df_results.to_csv(results_path, index=False, encoding="utf-8-sig")

    # 2. reliability_summary.csv
    rel_path = output_dir / "reliability_summary.csv"
    rel_data = summary.get("reliability", {})
    if rel_data:
        pd.DataFrame([rel_data]).to_csv(rel_path, index=False, encoding="utf-8-sig")

    # 3. error_taxonomy.csv
    err_path = output_dir / "error_taxonomy.csv"
    err_data = summary.get("error_analysis", {}).get("by_error", {})
    if err_data:
        pd.DataFrame([{"error_type": k, "count": v} for k, v in err_data.items()]).to_csv(err_path, index=False, encoding="utf-8-sig")

def generate_paper_tables(summary: Dict[str, Any], output_path: Path):
    """Generate paper-ready markdown tables."""
    lines = ["# Paper Tables (Auto-generated)", ""]
    
    # Table 1: Core Performance
    lines.append("## Table 1: End-to-End Performance")
    lines.append("")
    lines.append("| Metric | Value | Description |")
    lines.append("|---|---:|---|")
    metrics = summary.get("metrics", {})
    for m_name, m_val in metrics.items():
        val = m_val.get("value", 0)
        lines.append(f"| {m_name} | {val:.4f} | {m_val.get('description', '')} |")
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

    output_path.write_text("\n".join(lines), encoding="utf-8")
