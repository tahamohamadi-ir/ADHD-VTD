from __future__ import annotations

import re
import csv
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from src.config.paths import RESULTS_DIR
from src.evaluation.artifact_analysis import locate_benchmark_artifact
from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl


PROMPT_VERSION = "phase16_sql_business_logic_v0"


@dataclass(frozen=True, slots=True)
class JudgeResult:
    case_id: str
    provider: str
    model: str
    prompt_version: str
    verdict: str
    semantic_business_correct: bool | None
    score: float | None
    reason: str
    authoritative: bool
    redacted: bool
    generated_sql_hash: str | None = None
    gold_sql_hash: str | None = None


class JudgeProvider(Protocol):
    provider_name: str
    model_name: str

    def judge(self, record: dict[str, Any]) -> JudgeResult:
        ...


def normalize_sql(sql: str | None) -> str:
    if not sql:
        return ""
    stripped = re.sub(r"\s*;\s*$", "", sql.strip())
    compact = re.sub(r"\s+", " ", stripped)
    return compact.lower()


def _short_hash(text: str | None) -> str | None:
    if not text:
        return None
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class MockJudgeProvider:
    """Deterministic scaffold provider that avoids inventing semantic labels.

    This provider is intentionally conservative. It marks exact SQL matches as
    correct, invalid/missing SQL as incorrect, and valid result mismatches as
    requiring independent semantic review.
    """

    provider_name = "mock"
    model_name = "deterministic_exact_match_v0"

    def judge(self, record: dict[str, Any]) -> JudgeResult:
        case_id = str(record.get("id") or record.get("case_id") or "")
        generated_sql = record.get("generated_sql")
        gold_sql = record.get("gold_sql")
        valid_sql = bool(record.get("valid_sql"))
        error = str(record.get("error") or "")

        generated_norm = normalize_sql(generated_sql)
        gold_norm = normalize_sql(gold_sql)

        if generated_norm and gold_norm and generated_norm == gold_norm:
            verdict = "exact_sql_match"
            semantic_business_correct: bool | None = True
            score: float | None = 1.0
            reason = "Generated SQL matches the gold SQL after whitespace/case normalization."
        elif not generated_norm:
            verdict = "missing_sql"
            semantic_business_correct = False
            score = 0.0
            reason = "No generated SQL exists, so the query cannot satisfy the requested business logic."
        elif not valid_sql:
            verdict = "invalid_sql"
            semantic_business_correct = False
            score = 0.0
            reason = "Generated SQL did not pass validation/execution, so it cannot be business-correct."
        elif error == "RESULT_MISMATCH":
            verdict = "requires_semantic_review"
            semantic_business_correct = None
            score = None
            reason = "Valid SQL produced a result mismatch. The mock judge does not infer semantic correctness."
        else:
            verdict = "unjudged"
            semantic_business_correct = None
            score = None
            reason = "The mock judge only labels exact matches, missing SQL, invalid SQL, and valid result mismatches."

        return JudgeResult(
            case_id=case_id,
            provider=self.provider_name,
            model=self.model_name,
            prompt_version=PROMPT_VERSION,
            verdict=verdict,
            semantic_business_correct=semantic_business_correct,
            score=score,
            reason=reason,
            authoritative=False,
            redacted=True,
            generated_sql_hash=_short_hash(generated_sql),
            gold_sql_hash=_short_hash(gold_sql),
        )


def select_records_for_judging(
    predictions: list[dict[str, Any]],
    *,
    failures_only: bool = True,
    sample_size: int | None = None,
) -> list[dict[str, Any]]:
    selected = [
        record
        for record in predictions
        if not failures_only
        or not bool(record.get("ok") or record.get("execution_correct") or record.get("result_match"))
    ]
    if sample_size is not None:
        selected = selected[: max(0, sample_size)]
    return selected


def _provider_from_name(name: str) -> JudgeProvider:
    normalized = name.strip().lower()
    if normalized == "mock":
        return MockJudgeProvider()
    raise ValueError(
        f"Unsupported judge provider '{name}'. The current offline scaffold supports only 'mock'."
    )


def judge_benchmark_artifact(
    artifact_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    provider_name: str = "mock",
    failures_only: bool = True,
    sample_size: int | None = None,
) -> dict[str, Path]:
    artifact = locate_benchmark_artifact(artifact_dir)
    predictions = read_jsonl(artifact.predictions_path)
    summary = read_json(artifact.summary_path)
    provider = _provider_from_name(provider_name)

    records = select_records_for_judging(
        predictions,
        failures_only=failures_only,
        sample_size=sample_size,
    )
    judgments = [asdict(provider.judge(record)) for record in records]

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_root = RESULTS_DIR / "judgments" / timestamp
    else:
        output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    verdict_counts = Counter(row["verdict"] for row in judgments)
    correctness_counts = Counter(
        "correct"
        if row["semantic_business_correct"] is True
        else "incorrect"
        if row["semantic_business_correct"] is False
        else "unjudged"
        for row in judgments
    )
    judge_summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_artifact": str(artifact.root),
        "summary_path": str(artifact.summary_path),
        "predictions_path": str(artifact.predictions_path),
        "provider": provider.provider_name,
        "model": provider.model_name,
        "prompt_version": PROMPT_VERSION,
        "authoritative": False,
        "failures_only": failures_only,
        "sample_size": sample_size,
        "total_predictions": len(predictions),
        "total_judged": len(judgments),
        "verdict_counts": dict(verdict_counts),
        "semantic_business_counts": dict(correctness_counts),
        "config": summary.get("config", {}),
        "anti_fake_policy": (
            "Mock judgments are deterministic scaffold labels only. Valid SQL "
            "result mismatches remain unjudged until an independent semantic judge or human review runs."
        ),
    }
    cost_summary = {
        "provider": provider.provider_name,
        "model": provider.model_name,
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_usd": 0.0,
        "cost_authoritative": provider.provider_name != "mock",
        "note": "Mock provider does not call an external model and has zero token/cost accounting.",
    }

    judgments_path = write_jsonl(output_root / "judgments.jsonl", judgments)
    summary_path = write_json(output_root / "judge_summary.json", judge_summary)
    costs_path = write_json(output_root / "judge_costs.json", cost_summary)
    semantic_summary_path = _write_semantic_summary_csv(
        output_root / "semantic_business_summary.csv",
        judge_summary,
    )
    reasoning_path = output_root / "judge_reasoning.md"
    reasoning_path.write_text(_render_reasoning(judge_summary, judgments), encoding="utf-8")

    return {
        "judgments": judgments_path,
        "summary": summary_path,
        "costs": costs_path,
        "semantic_summary": semantic_summary_path,
        "reasoning": reasoning_path,
    }


def _write_semantic_summary_csv(path: Path, summary: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = summary.get("semantic_business_counts", {})
    verdict_counts = summary.get("verdict_counts", {})
    row = {
        "provider": summary.get("provider"),
        "model": summary.get("model"),
        "prompt_version": summary.get("prompt_version"),
        "authoritative": summary.get("authoritative"),
        "total_predictions": summary.get("total_predictions"),
        "total_judged": summary.get("total_judged"),
        "semantic_correct": counts.get("correct", 0),
        "semantic_incorrect": counts.get("incorrect", 0),
        "semantic_unjudged": counts.get("unjudged", 0),
        "exact_sql_match": verdict_counts.get("exact_sql_match", 0),
        "invalid_sql": verdict_counts.get("invalid_sql", 0),
        "missing_sql": verdict_counts.get("missing_sql", 0),
        "requires_semantic_review": verdict_counts.get("requires_semantic_review", 0),
    }
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return path


def _render_reasoning(summary: dict[str, Any], judgments: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase 16 Mock Judge Report",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Source",
        "",
        f"- artifact: `{summary['source_artifact']}`",
        f"- provider: `{summary['provider']}`",
        f"- model: `{summary['model']}`",
        f"- prompt_version: `{summary['prompt_version']}`",
        f"- authoritative: `{summary['authoritative']}`",
        "",
        "## Anti-Fake Statement",
        "",
        summary["anti_fake_policy"],
        "",
        "## Summary",
        "",
        f"- total_predictions: `{summary['total_predictions']}`",
        f"- total_judged: `{summary['total_judged']}`",
        f"- verdict_counts: `{summary['verdict_counts']}`",
        f"- semantic_business_counts: `{summary['semantic_business_counts']}`",
        "",
        "## Judgment Rows",
        "",
        "| Case | Verdict | Semantic Correct | Reason |",
        "|---|---|---|---|",
    ]
    for row in judgments:
        reason = str(row.get("reason") or "").replace("|", "/")
        lines.append(
            f"| {row.get('case_id')} | {row.get('verdict')} | {row.get('semantic_business_correct')} | {reason} |"
        )
    lines.append("")
    return "\n".join(lines)
