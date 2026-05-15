"""Stratified train/dev/test split of the 400-example dataset.

Split: 280 train / 60 dev / 60 test (stratified by difficulty).
Also splits the 100 behavioral examples: 40 dev / 60 test.
"""
from __future__ import annotations
import json, sys, random
from pathlib import Path
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.jsonl import write_jsonl

MAIN_DATASET = Path("data/questions/full/vtd_question_sql_400_merged_validated.json")
SPECIAL_DATASET = Path("data/questions/special/vtd_evaluation_special_100.json")
SEED = 42

def load_examples(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("examples", data) if isinstance(data, dict) else data

def stratified_split(examples: list[dict], key: str, ratios: tuple[float,...], seed: int):
    target_sizes = [round(len(examples) * r) for r in ratios[:-1]]
    target_sizes.append(len(examples) - sum(target_sizes))
    return stratified_split_exact(examples, key, target_sizes, seed)

def stratified_split_exact(examples: list[dict], key: str, target_sizes: list[int], seed: int):
    if sum(target_sizes) != len(examples):
        raise ValueError(f"target_sizes must sum to {len(examples)}, got {sum(target_sizes)}")
    rng = random.Random(seed)
    buckets: dict[str, list[dict]] = defaultdict(list)
    for ex in examples:
        buckets[ex.get(key, "unknown")].append(ex)
    splits: list[list[dict]] = [[] for _ in target_sizes]
    remaining = list(target_sizes)
    for _, items in sorted(buckets.items()):
        rng.shuffle(items)
        for item in items:
            candidates = [i for i, slots in enumerate(remaining) if slots > 0]
            if not candidates:
                raise RuntimeError("No remaining split slots while assigning examples.")
            chosen = max(candidates, key=lambda i: (remaining[i] / target_sizes[i], -i))
            splits[chosen].append(item)
            remaining[chosen] -= 1
    return splits

def save(examples: list[dict], dir_path: Path, name: str):
    dir_path.mkdir(parents=True, exist_ok=True)
    json_path = dir_path / f"{name}.json"
    jsonl_path = dir_path / f"{name}.jsonl"
    json_path.write_text(json.dumps(examples, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(jsonl_path, examples)
    print(f"  ✅ {name}: {len(examples)} → {json_path.name} + {jsonl_path.name}")

def main():
    # Main 400 → 280/60/60
    examples = load_examples(MAIN_DATASET)
    print(f"Main dataset: {len(examples)} examples")
    train, dev, test = stratified_split_exact(examples, "difficulty", [280, 60, 60], SEED)
    save(train, Path("data/questions/train"), "train")
    save(dev, Path("data/questions/dev"), "dev")
    save(test, Path("data/questions/test"), "test")
    print(f"  Split: {len(train)} train / {len(dev)} dev / {len(test)} test\n")

    # Special 100 → 40 dev / 60 test
    if SPECIAL_DATASET.exists():
        special = load_examples(SPECIAL_DATASET)
        print(f"Special dataset: {len(special)} examples")
        s_dev, s_test = stratified_split_exact(special, "evaluation_type", [40, 60], SEED)
        save(s_dev, Path("data/questions/special"), "behavior_dev")
        save(s_test, Path("data/questions/special"), "behavior_test")
        print(f"  Split: {len(s_dev)} dev / {len(s_test)} test")

    # Audit 50
    audit_dir = Path("data/questions/audit")
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / "phase0_50q_audit.csv"
    if not audit_path.exists():
        rng = random.Random(SEED)
        audit_pool = list(examples)
        rng.shuffle(audit_pool)
        audit_50 = audit_pool[:50]
        lines = ["id,question_fa,gold_sql,difficulty,category,manual_pass"]
        for ex in audit_50:
            q = ex.get("question_fa","").replace('"','""')
            s = ex.get("sql","").replace('"','""')
            lines.append(f'"{ex.get("id","")}","{q}","{s}","{ex.get("difficulty","")}","{ex.get("category","")}",""')
        audit_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n✅ Audit CSV: {audit_path} ({len(audit_50)} cases)")

if __name__ == "__main__":
    main()
