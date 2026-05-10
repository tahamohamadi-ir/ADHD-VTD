from __future__ import annotations

import subprocess
import sys

# Windows PowerShell/cp1252 safety: allow Persian output without UnicodeEncodeError.
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from pathlib import Path

try:
    from _bootstrap_path import PROJECT_ROOT
except Exception:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    script = PROJECT_ROOT / "scripts" / "phase0_validate_semantic_metadata.py"
    if not script.exists():
        print(f"Missing validation script: {script}")
        return 1

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        print("❌ Semantic metadata alignment test failed.")
        return result.returncode

    report = PROJECT_ROOT / "data" / "audit" / "semantic_metadata_alignment_report.md"
    if not report.exists():
        print(f"❌ Expected report not found: {report}")
        return 1

    text = report.read_text(encoding="utf-8")
    if "❌ FAIL" in text:
        print("❌ Report contains failed checks.")
        return 1

    print("✅ Semantic metadata alignment test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
