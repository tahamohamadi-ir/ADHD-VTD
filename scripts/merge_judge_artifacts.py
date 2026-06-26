from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from _bootstrap_path import PROJECT_ROOT  # noqa: F401


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if not isinstance(data, dict):
                raise ValueError(f"Invalid JSONL row at {path}:{line_no}")
            rows.append(data)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False))
            f.write("\n")
    return path


def _counter_to_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _semantic_label(row: dict[str, Any]) -> str:
    direct = row.get("semantic_business_correct")
    if direct is True:
        return "correct"
    if direct is False:
        return "incorrect"
    verdict = str(row.get("verdict") or "").lower()
    if verdict == "business_correct":
        return "correct"
    if verdict == "business_incorrect":
        return "incorrect"
    if verdict in {"provider_error", "provider_parse_error"}:
        return verdict
    return "unjudged"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge split judge_benchmark_artifact.py output directories into one summary artifact.",
    )
    parser.add_argument("artifact_dirs", nargs="+", help="Input results/judgments/<chunk> directories.")
    parser.add_argument("--output-dir", required=True, help="Merged output directory.")
    parser.add_argument(
        "--duplicate-policy",
        choices=["error", "keep-first", "keep-last"],
        default="error",
        help="How to handle duplicate case IDs across chunks. Use keep-last for retry patch artifacts.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[dict[str, Any]] = []
    judgments_by_case: dict[str, dict[str, Any]] = {}
    judgments_without_case: list[dict[str, Any]] = []
    reasoning_parts: list[str] = []
    seen_cases: set[str] = set()

    for raw_dir in args.artifact_dirs:
        artifact_dir = Path(raw_dir)
        summary_path = artifact_dir / "judge_summary.json"
        if not summary_path.exists():
            raise FileNotFoundError(summary_path)
        summary = _read_json(summary_path)
        summaries.append(summary)
        for row in _iter_jsonl(artifact_dir / "judgments.jsonl"):
            case_id = str(row.get("case_id") or row.get("item_id") or "")
            if case_id:
                if case_id in seen_cases:
                    if args.duplicate_policy == "error":
                        raise ValueError(f"Duplicate judged case_id across chunks: {case_id}")
                    if args.duplicate_policy == "keep-first":
                        continue
                seen_cases.add(case_id)
                judgments_by_case[case_id] = row
            else:
                judgments_without_case.append(row)
        reasoning_path = artifact_dir / "judge_reasoning.md"
        if reasoning_path.exists():
            reasoning_parts.append(f"\n\n## Source: {artifact_dir}\n\n{reasoning_path.read_text(encoding='utf-8')}")

    verdict_counts: Counter[str] = Counter()
    semantic_counts: Counter[str] = Counter()
    judgments = [judgments_by_case[key] for key in sorted(judgments_by_case)] + judgments_without_case

    authoritative_judgments = 0
    non_authoritative_judgments = 0
    reasoning_details_present = 0
    for row in judgments:
        verdict = str(row.get("verdict") or "unknown")
        verdict_counts[verdict] += 1
        semantic_counts[_semantic_label(row)] += 1
        if bool(row.get("authoritative")):
            authoritative_judgments += 1
        else:
            non_authoritative_judgments += 1
        if bool(row.get("reasoning_details_present")):
            reasoning_details_present += 1

    provider = summaries[0].get("provider") if summaries else None
    model = summaries[0].get("model") if summaries else None
    prompt_version = summaries[0].get("prompt_version") if summaries else None
    judge_policy = summaries[0].get("judge_policy") if summaries else None
    total_predictions = summaries[0].get("total_predictions") if summaries else None
    redaction_policy = summaries[0].get("redaction_policy") if summaries else None

    input_tokens = 0
    output_tokens = 0
    reasoning_tokens = 0
    estimated_cost_usd = 0.0
    for raw_dir in args.artifact_dirs:
        costs_path = Path(raw_dir) / "judge_costs.json"
        if not costs_path.exists():
            continue
        costs = _read_json(costs_path)
        input_tokens += int(costs.get("input_tokens") or 0)
        output_tokens += int(costs.get("output_tokens") or 0)
        reasoning_tokens += int(costs.get("reasoning_tokens") or 0)
        estimated_cost_usd += float(costs.get("estimated_cost_usd") or 0.0)

    summary_out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "merged_from": [str(Path(path)) for path in args.artifact_dirs],
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "judge_policy": judge_policy,
        "authoritative": bool(judgments) and non_authoritative_judgments == 0,
        "authoritative_judgments": authoritative_judgments,
        "non_authoritative_judgments": non_authoritative_judgments,
        "failures_only": False,
        "sample_size": None,
        "case_ids": sorted(seen_cases),
        "total_predictions": total_predictions,
        "total_judged": len(judgments),
        "verdict_counts": _counter_to_dict(verdict_counts),
        "semantic_business_counts": {
            "correct": semantic_counts.get("correct", 0),
            "incorrect": semantic_counts.get("incorrect", 0),
            "unjudged": semantic_counts.get("unjudged", 0),
            "provider_error": semantic_counts.get("provider_error", 0),
            "provider_parse_error": semantic_counts.get("provider_parse_error", 0),
        },
        "reasoning_tokens": reasoning_tokens,
        "reasoning_details_present": reasoning_details_present,
        "redaction_policy": redaction_policy,
        "anti_fake_policy": "Merged from live judge artifacts. No judgments are inferred or rewritten.",
    }

    costs_out = {
        "provider": provider,
        "model": model,
        "judge_policy": judge_policy,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "estimated_cost_usd": estimated_cost_usd,
        "cost_authoritative": all(bool(_read_json(Path(path) / "judge_costs.json").get("cost_authoritative")) for path in args.artifact_dirs if (Path(path) / "judge_costs.json").exists()),
        "note": "Merged token counts from chunk-level judge_costs.json files.",
    }

    semantic_csv = output_dir / "semantic_business_summary.csv"
    with semantic_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "provider",
                "model",
                "prompt_version",
                "judge_policy",
                "authoritative",
                "total_predictions",
                "total_judged",
                "semantic_correct",
                "semantic_incorrect",
                "semantic_unjudged",
                "provider_error",
                "provider_parse_error",
                "reasoning_tokens",
                "reasoning_details_present",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "provider": provider,
                "model": model,
                "prompt_version": prompt_version,
                "judge_policy": judge_policy,
                "authoritative": summary_out["authoritative"],
                "total_predictions": total_predictions,
                "total_judged": len(judgments),
                "semantic_correct": semantic_counts.get("correct", 0),
                "semantic_incorrect": semantic_counts.get("incorrect", 0),
                "semantic_unjudged": semantic_counts.get("unjudged", 0),
                "provider_error": semantic_counts.get("provider_error", 0),
                "provider_parse_error": semantic_counts.get("provider_parse_error", 0),
                "reasoning_tokens": reasoning_tokens,
                "reasoning_details_present": summary_out["reasoning_details_present"],
            }
        )

    _write_jsonl(output_dir / "judgments.jsonl", judgments)
    _write_json(output_dir / "judge_summary.json", summary_out)
    _write_json(output_dir / "judge_costs.json", costs_out)
    (output_dir / "judge_reasoning.md").write_text("\n".join(reasoning_parts).strip() + "\n", encoding="utf-8")

    print(f"project_root={PROJECT_ROOT}")
    print(f"chunks={len(args.artifact_dirs)}")
    print(f"total_judged={len(judgments)}")
    print(f"summary={output_dir / 'judge_summary.json'}")
    print(f"semantic_summary={semantic_csv}")


if __name__ == "__main__":
    main()
