from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from _bootstrap_path import PROJECT_ROOT

SRC = PROJECT_ROOT / "data" / "questions" / "full" / "vtd_question_sql_400_merged_validated.json"
OUT = PROJECT_ROOT / "data" / "questions" / "audit" / "phase0_50q_audit_cases.json"
RESULTS = PROJECT_ROOT / "data" / "questions" / "audit" / "phase0_50q_audit_results.jsonl"
TARGETS = {"easy": 12, "medium": 13, "hard": 13, "complex": 12}


def select_cases(examples: list[dict]) -> list[dict]:
    by_diff_cat: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for e in examples:
        by_diff_cat[(e.get("difficulty"), e.get("category"))].append(e)
    selected: list[dict] = []
    for diff, target in TARGETS.items():
        cats = sorted({e.get("category") for e in examples if e.get("difficulty") == diff})
        idx_by_cat = {cat: 0 for cat in cats}
        while len([x for x in selected if x.get("difficulty") == diff]) < target:
            progressed = False
            selected_counter = Counter(x.get("category") for x in selected if x.get("difficulty") == diff)
            for cat in sorted(cats, key=lambda c: (selected_counter[c], c)):
                bucket = by_diff_cat[(diff, cat)]
                i = idx_by_cat[cat]
                if i < len(bucket):
                    selected.append(bucket[i])
                    idx_by_cat[cat] += 1
                    progressed = True
                    break
            if not progressed:
                break
    return selected


def main() -> int:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    selected = select_cases(data["examples"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    package = {
        "project": "ADHD-VTD / VTD-Edge / PARS-SQL",
        "artifact": "Phase 0 - 50 Question Audit Cases",
        "version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(SRC.relative_to(PROJECT_ROOT)),
        "selection_policy": {
            "total_cases": len(selected),
            "difficulty_targets": TARGETS,
            "method": "Balanced by difficulty and round-robin over categories.",
        },
        "difficulty_counts": dict(Counter(e.get("difficulty") for e in selected)),
        "category_counts": dict(Counter(e.get("category") for e in selected)),
        "cases": [],
    }
    for i, e in enumerate(selected, 1):
        package["cases"].append({
            "audit_id": f"PHASE0-50Q-{i:03d}",
            "source_id": e.get("id"),
            "difficulty": e.get("difficulty"),
            "category": e.get("category"),
            "pattern": e.get("pattern"),
            "question_fa": e.get("question_fa"),
            "gold_sql": e.get("sql"),
            "recommended_visual": e.get("recommended_visual"),
            "storytelling_hint_fa": e.get("storytelling_hint_fa", ""),
            "safe_sql": e.get("safe_sql", True),
            "dialect": e.get("dialect", "sqlite"),
            "audit_status": "pending_execution",
            "manual_review_required": True,
        })
    OUT.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    with RESULTS.open("w", encoding="utf-8") as f:
        for c in package["cases"]:
            f.write(json.dumps({"audit_id": c["audit_id"], "source_id": c["source_id"], "status": "not_run"}, ensure_ascii=False) + "\n")
    print(f"✅ Wrote {OUT}")
    print(f"✅ Wrote {RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
