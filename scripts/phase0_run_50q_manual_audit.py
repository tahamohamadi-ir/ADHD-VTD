from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from _bootstrap_path import PROJECT_ROOT

CASES_PATH = PROJECT_ROOT / "data" / "questions" / "audit" / "phase0_50q_audit_cases.json"
RESULTS_PATH = PROJECT_ROOT / "data" / "questions" / "audit" / "phase0_50q_audit_results.jsonl"
REPORT_PATH = PROJECT_ROOT / "data" / "questions" / "audit" / "phase0_50q_audit_report.md"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main() -> int:
    package = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = package["cases"]
    results = {r.get("audit_id"): r for r in load_jsonl(RESULTS_PATH)}
    success = [c for c in cases if results.get(c["audit_id"], {}).get("execution_success")]
    failures = [c for c in cases if not results.get(c["audit_id"], {}).get("execution_success")]
    failure_errors = Counter(results.get(c["audit_id"], {}).get("error") or "NOT_RUN" for c in failures)

    lines = []
    lines.append("# Phase 0 - 50 Question Manual Audit Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Total cases | {len(cases)} |")
    lines.append(f"| Gold SQL executed successfully | {len(success)} |")
    lines.append(f"| Failed / not run | {len(failures)} |")
    lines.append("")
    lines.append("## Failure Categories")
    lines.append("")
    lines.append("| Error | Count |")
    lines.append("|---|---:|")
    for err, n in failure_errors.most_common():
        lines.append(f"| `{str(err).replace('|','/')}` | {n} |")
    lines.append("")
    lines.append("## Manual Review Table")
    lines.append("")
    lines.append("| Audit ID | Source ID | Difficulty | Category | Execution | Manual schema OK? | Manual value OK? | Notes |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for c in cases:
        r = results.get(c["audit_id"], {})
        exec_status = "✅" if r.get("execution_success") else f"❌ {r.get('error', 'NOT_RUN')}"
        lines.append(f"| {c['audit_id']} | {c['source_id']} | {c['difficulty']} | {c['category']} | {str(exec_status).replace('|','/')} | TBD | TBD |  |")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
