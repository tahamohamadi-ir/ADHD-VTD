"""Wrapper: run all Phase 2 validation scripts in sequence."""
from __future__ import annotations
import subprocess, sys, time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PYTHON = str(Path(".venv/Scripts/python.exe").resolve())
SCRIPTS = [
    "scripts/compare_schema_snapshots.py",
    "scripts/check_schema_column_references.py",
    "scripts/check_duplicate_questions.py",
    "scripts/validate_dataset_sql.py",
    "scripts/convert_dataset_to_jsonl.py",
    "scripts/split_dataset.py",
    "scripts/export_schema_markdown.py",
]

def main():
    results: list[tuple[str, int, float]] = []
    all_ok = True
    for script in SCRIPTS:
        name = Path(script).stem
        print(f"\n{'='*60}\n> Running: {name}\n{'='*60}")
        start = time.perf_counter()
        r = subprocess.run([PYTHON, script], cwd=str(Path(__file__).resolve().parent.parent))
        elapsed = (time.perf_counter() - start) * 1000
        results.append((name, r.returncode, elapsed))
        if r.returncode != 0:
            all_ok = False
            print(f"⚠️  {name} exited with code {r.returncode}")

    # Summary
    report_dir = Path("results/data_quality")
    report_dir.mkdir(parents=True, exist_ok=True)
    lines = ["# Full Validation Summary", ""]
    lines += ["| Script | Status | Time |", "|---|---|---|"]
    for name, rc, ms in results:
        st = "✅ PASS" if rc == 0 else f"❌ FAIL (exit {rc})"
        lines.append(f"| {name} | {st} | {ms:.0f}ms |")
    lines.append(f"\n**Overall: {'✅ ALL PASSED' if all_ok else '❌ SOME FAILED'}**")
    (report_dir / "full_validation_summary.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    for name, rc, ms in results:
        st = "✅" if rc == 0 else "❌"
        print(f"  {st} {name} ({ms:.0f}ms)")
    print(f"\n{'✅ ALL PASSED' if all_ok else '❌ SOME FAILED'}")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
