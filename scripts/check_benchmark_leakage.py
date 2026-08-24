from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from _bootstrap_path import PROJECT_ROOT  # type: ignore


QUESTION_SOURCES = {
    "train": PROJECT_ROOT / "data" / "questions" / "train" / "train.json",
    "dev": PROJECT_ROOT / "data" / "questions" / "dev" / "dev.json",
    "test": PROJECT_ROOT / "data" / "questions" / "test" / "test.json",
    "behavior_dev": PROJECT_ROOT / "data" / "questions" / "special" / "behavior_dev.json",
    "behavior_test": PROJECT_ROOT / "data" / "questions" / "special" / "behavior_test.json",
}

REFERENCE_SOURCES = {
    "golden_examples": PROJECT_ROOT / "data" / "golden_sql" / "golden_examples.jsonl",
    "few_shot_bank": PROJECT_ROOT / "data" / "golden_sql" / "few_shot_bank.jsonl",
    "rag_indexed_examples": PROJECT_ROOT / "data" / "rag" / "indexed_examples.jsonl",
}

REPORT_PATH = PROJECT_ROOT / "results" / "data_quality" / "benchmark_leakage_report.md"
CASES_PATH = PROJECT_ROOT / "results" / "data_quality" / "benchmark_leakage_cases.jsonl"


@dataclass(slots=True)
class AuditRecord:
    source: str
    id: str
    base_id: str
    question: str
    normalized_question: str
    sql: str
    sql_skeleton: str


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def extract_cases(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in (
            "cases",
            "examples",
            "positive_examples",
            "behavioral_evaluation_examples",
            "items",
        ):
            value = raw.get(key)
            if isinstance(value, list):
                return value
    return []


def normalize_text(value: str) -> str:
    text = str(value or "").lower()
    text = text.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه")
    text = re.sub(r"[^\w\u0600-\u06ff]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def base_id(value: str) -> str:
    text = str(value or "")
    return re.sub(r"^(fs_|idx_)", "", text)


def sql_skeleton(sql: str) -> str:
    text = str(sql or "").lower()
    text = re.sub(r"'[^']*'", "?", text)
    text = re.sub(r'"[^"]*"', "?", text)
    text = re.sub(r"\b\d+(\.\d+)?\b", "?", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def record_from_case(source: str, case: dict[str, Any]) -> AuditRecord:
    record_id = str(case.get("id") or case.get("case_id") or case.get("audit_id") or "")
    question = str(
        case.get("question_fa") or case.get("question") or case.get("user_utterance_fa") or ""
    )
    sql = str(case.get("sql") or case.get("gold_sql") or case.get("expected_sql") or "")
    return AuditRecord(
        source=source,
        id=record_id,
        base_id=base_id(record_id),
        question=question,
        normalized_question=normalize_text(question),
        sql=sql,
        sql_skeleton=sql_skeleton(sql),
    )


def load_records() -> list[AuditRecord]:
    records: list[AuditRecord] = []
    for source, path in QUESTION_SOURCES.items():
        for case in extract_cases(read_json(path)):
            records.append(record_from_case(source, case))
    for source, path in REFERENCE_SOURCES.items():
        for case in read_jsonl(path):
            records.append(record_from_case(source, case))
    return records


def add_case(
    cases: list[dict[str, Any]],
    issue_type: str,
    left: AuditRecord,
    right: AuditRecord,
    **extra: Any,
) -> None:
    cases.append(
        {
            "issue_type": issue_type,
            "left_source": left.source,
            "left_id": left.id,
            "left_base_id": left.base_id,
            "left_question": left.question,
            "right_source": right.source,
            "right_id": right.id,
            "right_base_id": right.base_id,
            "right_question": right.question,
            **extra,
        }
    )


def is_cross_source(left: AuditRecord, right: AuditRecord) -> bool:
    return left.source != right.source


def run_audit(records: list[AuditRecord]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cases: list[dict[str, Any]] = []
    benchmark_sources = {"dev", "test", "behavior_dev", "behavior_test"}
    reference_sources = set(REFERENCE_SOURCES)

    for i, left in enumerate(records):
        for right in records[i + 1 :]:
            if not is_cross_source(left, right):
                continue
            if left.id and left.id == right.id:
                add_case(cases, "exact_id_duplicate", left, right)
            if left.base_id and left.base_id == right.base_id:
                add_case(cases, "base_id_overlap", left, right)
            if left.normalized_question and left.normalized_question == right.normalized_question:
                add_case(cases, "exact_normalized_question_duplicate", left, right)
            if (
                left.normalized_question
                and right.normalized_question
                and (left.source in benchmark_sources or right.source in benchmark_sources)
            ):
                score = SequenceMatcher(
                    None, left.normalized_question, right.normalized_question
                ).ratio()
                if score >= 0.92 and left.normalized_question != right.normalized_question:
                    add_case(
                        cases, "near_duplicate_question", left, right, similarity=round(score, 4)
                    )
            if (
                left.sql_skeleton
                and right.sql_skeleton
                and {left.source, right.source} & benchmark_sources
                and {left.source, right.source} & reference_sources
                and left.sql_skeleton == right.sql_skeleton
            ):
                add_case(cases, "sql_skeleton_overlap", left, right)

    counts: dict[str, int] = {}
    for case in cases:
        counts[case["issue_type"]] = counts.get(case["issue_type"], 0) + 1

    source_counts: dict[str, int] = {}
    for record in records:
        source_counts[record.source] = source_counts.get(record.source, 0) + 1

    summary = {
        "source_counts": dict(sorted(source_counts.items())),
        "issue_counts": dict(sorted(counts.items())),
        "total_issues": len(cases),
    }
    return summary, cases


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_report(path: Path, summary: dict[str, Any], cases: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Benchmark Leakage Audit",
        "",
        "This audit detects observable dataset overlap. It cannot prove that prompts or models are not overfit.",
        "",
        "## Source Counts",
        "",
    ]
    for source, count in summary["source_counts"].items():
        lines.append(f"- `{source}`: {count}")
    lines.extend(["", "## Issue Counts", ""])
    if summary["issue_counts"]:
        for issue, count in summary["issue_counts"].items():
            lines.append(f"- `{issue}`: {count}")
    else:
        lines.append("- no observable overlap detected")
    lines.extend(
        [
            "",
            "## High-Risk Examples",
            "",
        ]
    )
    for case in cases[:30]:
        lines.append(
            f"- `{case['issue_type']}`: `{case['left_source']}:{case['left_id']}` "
            f"<-> `{case['right_source']}:{case['right_id']}`"
        )
    lines.extend(
        [
            "",
            "## Required Follow-Up",
            "",
            "- Treat `base_id_overlap`, exact question duplicate, and SQL skeleton overlap involving dev/test as benchmark leakage risk.",
            "- If RAG or few-shot examples overlap with dev/test, add an exclude-self policy before final paper benchmarks.",
            "- Keep paper claims conservative: this audit is evidence, not proof of no overfit.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    records = load_records()
    summary, cases = run_audit(records)
    write_jsonl(CASES_PATH, cases)
    write_report(REPORT_PATH, summary, cases)
    print(f"records={len(records)} issues={len(cases)}")
    print(f"report={REPORT_PATH}")
    print(f"cases={CASES_PATH}")


if __name__ == "__main__":
    main()
