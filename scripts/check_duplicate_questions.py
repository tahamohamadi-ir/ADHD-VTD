"""Check for duplicate IDs and duplicate questions in datasets.

Checks:
1. Duplicate IDs within each dataset file
2. Duplicate questions (exact match after normalization) within each file
3. Cross-file duplicate IDs
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.nlu.persian_normalizer import PersianNormalizer

DATASET_FILES = [
    Path("data/questions/full/vtd_question_sql_400_merged_validated.json"),
    Path("data/questions/special/vtd_evaluation_special_100.json"),
]


def load_examples(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("examples", data.get("questions", data.get("data", [])))


def main():
    normalizer = PersianNormalizer()
    all_ids: dict[str, list[str]] = {}  # id → [file1, file2, ...]
    issues: list[str] = []

    for fpath in DATASET_FILES:
        if not fpath.exists():
            print(f"⚠️  Skipping {fpath.name} (not found)")
            continue

        examples = load_examples(fpath)
        fname = fpath.name
        print(f"Checking {fname}: {len(examples)} examples")

        # 1. Duplicate IDs within file
        ids = [ex.get("id", "") for ex in examples]
        id_counts = Counter(ids)
        dupes = {k: v for k, v in id_counts.items() if v > 1}
        if dupes:
            for did, cnt in dupes.items():
                issues.append(f"[{fname}] Duplicate ID: '{did}' appears {cnt} times")

        # 2. Duplicate questions (normalized) within file
        norm_questions: dict[str, list[str]] = {}
        for ex in examples:
            q = ex.get("question_fa") or ex.get("user_utterance_fa") or ""
            nq = normalizer.normalize_text(str(q)).strip().lower()
            if nq:
                norm_questions.setdefault(nq, []).append(ex.get("id", "?"))
        q_dupes = {k: v for k, v in norm_questions.items() if len(v) > 1}
        for nq, ids_list in q_dupes.items():
            issues.append(
                f"[{fname}] Duplicate question (normalized): '{nq[:60]}...' → IDs: {ids_list}"
            )

        # Track cross-file IDs
        for eid in ids:
            all_ids.setdefault(eid, []).append(fname)

    # 3. Cross-file duplicate IDs
    cross_dupes = {k: v for k, v in all_ids.items() if len(v) > 1}
    for eid, files in cross_dupes.items():
        issues.append(f"[CROSS-FILE] ID '{eid}' appears in: {files}")

    # Write report
    report_dir = Path("results/data_quality")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "duplicate_check_report.md"

    lines = [
        "# Duplicate Check Report",
        "",
        "## Files Checked",
        "",
    ]
    for f in DATASET_FILES:
        status = "✅" if f.exists() else "⚠️ not found"
        lines.append(f"- `{f.name}` — {status}")
    lines.append("")

    if not issues:
        lines.append("✅ **No duplicates found.**")
        print(f"\n✅ No duplicates found across {len(DATASET_FILES)} files.")
    else:
        lines.append(f"❌ **{len(issues)} issue(s) found:**\n")
        lines.append("| # | Issue |")
        lines.append("|---|---|")
        for i, iss in enumerate(issues, 1):
            lines.append(f"| {i} | {iss} |")
        print(f"\n❌ {len(issues)} duplicate issue(s):")
        for iss in issues[:15]:
            print(f"  - {iss}")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {report_path}")
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
