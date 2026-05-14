"""Convert all JSON dataset files to JSONL format.

Converts the examples array from each JSON file into a JSONL file
stored alongside the original.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.jsonl import write_jsonl

DATASET_FILES = [
    Path("data/questions/full/vtd_question_sql_400_merged_validated.json"),
    Path("data/questions/special/vtd_evaluation_special_100.json"),
]


def load_examples(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("examples", data.get("questions", data.get("data", [])))


def main():
    total_converted = 0

    for fpath in DATASET_FILES:
        if not fpath.exists():
            print(f"⚠️  Skipping {fpath.name} (not found)")
            continue

        examples = load_examples(fpath)
        if not examples:
            print(f"⚠️  {fpath.name}: no examples found")
            continue

        # Validate each has id and question_fa
        valid = []
        for ex in examples:
            eid = ex.get("id", "")
            q = ex.get("question_fa", ex.get("user_utterance_fa", ""))
            if not eid:
                print(f"  ⚠️  Skipping example without ID in {fpath.name}")
                continue
            if not q:
                print(f"  ⚠️  [{eid}] Missing question_fa")
            valid.append(ex)

        out_path = fpath.with_suffix(".jsonl")
        count = write_jsonl(out_path, valid)
        print(f"✅ {fpath.name} → {out_path.name} ({count} records)")
        total_converted += count

    print(f"\nTotal: {total_converted} records converted to JSONL.")


if __name__ == "__main__":
    main()
