from __future__ import annotations

from _bootstrap_path import PROJECT_ROOT
from src.evaluation.phase0_audit import write_phase0_summary_json
from src.evaluation.report_generator import write_phase0_markdown_report


def main() -> int:
    json_out = write_phase0_summary_json()
    md_out = write_phase0_markdown_report()
    print(f"PROJECT_ROOT={PROJECT_ROOT}")
    print(f"Phase 0 evaluation summary JSON written to: {json_out}")
    print(f"Phase 0 evaluation summary MD written to: {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
