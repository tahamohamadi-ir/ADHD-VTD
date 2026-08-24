from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

from _bootstrap_path import add_project_root_to_path  # type: ignore

add_project_root_to_path()

from src.config.paths import QUESTIONS_DIR
from src.evaluation.dataset_loader import LoadedDataset, load_positive_400, write_json
from src.evaluation.paraphrase_holdout import (
    PARAPHRASE_RULES,
    build_holdout_dataset,
)

DEFAULT_N = 48
DEFAULT_SEED = 187
SAMPLE_COUNT = 5

SOURCE_LOADERS = {"positive400": load_positive_400}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dataset_filename(n: int) -> str:
    return f"phase18_7_holdout_paraphrase{n}.json"


def build_dataset_payload(
    holdout_cases: list[dict[str, Any]],
    metadata_block: dict[str, Any],
    source_kind: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "dataset": "phase18_7_holdout_paraphrase",
        **metadata_block,
        "source_kind": source_kind,
        "description_fa": (
            "نسخه بازنویسی‌شده پرسش‌ها برای سنجش مقاومت در برابر بیش‌برازش "
            "(holdout paraphrase، فاز 18.7)"
        ),
        "examples": holdout_cases,
    }
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the phase 18.7 holdout paraphrase dataset."
    )
    parser.add_argument("--n", type=int, default=DEFAULT_N, help="number of held-out cases")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="random seed")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=QUESTIONS_DIR / "special",
        help="directory for dataset and manifest files",
    )
    parser.add_argument(
        "--source",
        choices=sorted(SOURCE_LOADERS),
        default="positive400",
        help="source dataset kind",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing outputs")
    return parser.parse_args(argv)


def print_summary(
    source_kind: str,
    dataset: LoadedDataset,
    holdout_cases: list[dict[str, Any]],
    manifest: dict[str, Any],
    dataset_path: Path,
    manifest_path: Path,
    dataset_hash: str,
    source_hash: str,
    question_by_id: dict[str, str],
) -> None:
    print("=== Phase 18.7 Holdout Paraphrase Dataset ===")
    print(f"source       : {source_kind} ({len(dataset.cases)} cases)")
    print(f"source sha256: {source_hash[:16]}")
    print(f"held out     : {manifest['held_out_count']} (seed={manifest['seed']})")
    print(f"method       : {manifest['method']} ({len(PARAPHRASE_RULES)} rules)")
    print(f"dataset      : {dataset_path}")
    print(f"dataset sha  : {dataset_hash[:16]}")
    print(f"manifest     : {manifest_path}")
    difficulty = manifest["difficulty_counts"]
    rendered = " ".join(f"{key}={value}" for key, value in difficulty.items())
    print(f"difficulty   : {rendered}")
    print("samples:")
    for case in holdout_cases[:SAMPLE_COUNT]:
        cid = str(case.get("original_case_id"))
        before = question_by_id.get(cid, "")
        after = case.get("question_fa") or case.get("question") or ""
        print(f"  {case.get('id')} <- {cid} [{case.get('difficulty')}/{case.get('category')}]")
        print(f"    before: {before}")
        print(f"    after : {after}")


def main(argv: list[str] | None = None) -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in {"utf-8", "utf8"}:
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    if args.n <= 0:
        print("[error] --n must be a positive integer.")
        return 1
    loader = SOURCE_LOADERS[args.source]
    dataset: LoadedDataset = loader()

    dataset_path = args.output_dir / dataset_filename(args.n)
    manifest_path = args.output_dir / f"{dataset_filename(args.n)}.manifest.json"
    if not args.force and (dataset_path.exists() or manifest_path.exists()):
        print(f"[refuse] output already exists (use --force to overwrite): {dataset_path}")
        return 1

    holdout_cases, manifest = build_holdout_dataset(dataset.cases, args.n, args.seed)
    metadata_block = {
        "method": manifest["method"],
        "seed": manifest["seed"],
        "source_case_count": manifest["source_count"],
        "held_out_count": manifest["held_out_count"],
    }
    payload = build_dataset_payload(holdout_cases, metadata_block, args.source)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(dataset_path, payload)
    dataset_hash = sha256_file(dataset_path)
    source_hash = sha256_file(Path(dataset.path))

    full_manifest: dict[str, Any] = {
        "dataset_file": dataset_path.name,
        "generated_at_utc": manifest["generated_at_utc"],
        "method": manifest["method"],
        "seed": manifest["seed"],
        "source_kind": args.source,
        "source_path": str(dataset.path),
        "source_sha256": source_hash,
        "dataset_sha256": dataset_hash,
        "rule_count": len(PARAPHRASE_RULES),
        "source_count": manifest["source_count"],
        "held_out_count": manifest["held_out_count"],
        "difficulty_counts": manifest["difficulty_counts"],
    }
    write_json(manifest_path, full_manifest)

    question_by_id: dict[str, str] = {}
    for case in dataset.cases:
        cid = str(case.get("id") or "")
        if cid and cid not in question_by_id:
            question_by_id[cid] = str(case.get("question_fa") or case.get("question") or "")

    print_summary(
        source_kind=args.source,
        dataset=dataset,
        holdout_cases=holdout_cases,
        manifest=manifest,
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        dataset_hash=dataset_hash,
        source_hash=source_hash,
        question_by_id=question_by_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
