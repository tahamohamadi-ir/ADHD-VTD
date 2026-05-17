from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, TypeVar

T = TypeVar("T")


def base_record_id(value: Any) -> str:
    """Return a comparable case id, ignoring retrieval-bank prefixes."""
    record_id = str(value or "").strip()
    lowered = record_id.lower()
    for prefix in ("fs_", "idx_"):
        if lowered.startswith(prefix):
            return record_id[len(prefix) :].strip()
    return record_id


def normalize_overlap_question(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    text = text.replace("\u064a", "\u06cc").replace("\u0643", "\u06a9")
    text = re.sub(r"[\u200c\u200f\u202a-\u202e]", " ", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def record_question(record: dict[str, Any]) -> str:
    return str(
        record.get("question")
        or record.get("question_fa")
        or record.get("user_utterance_fa")
        or record.get("normalized_question")
        or ""
    )


def is_self_overlap_record(record: dict[str, Any], *, case_id: Any, question: Any) -> bool:
    candidate_id = base_record_id(record.get("id") or record.get("case_id"))
    current_id = base_record_id(case_id)
    if candidate_id and current_id and candidate_id == current_id:
        return True

    candidate_question = normalize_overlap_question(record_question(record))
    current_question = normalize_overlap_question(question)
    return bool(candidate_question and current_question and candidate_question == current_question)


def filter_self_overlaps(
    retrieved: Iterable[T],
    *,
    case_id: Any,
    question: Any,
) -> tuple[list[T], list[str]]:
    kept: list[T] = []
    removed_ids: list[str] = []
    for item in retrieved:
        record = getattr(item, "record", item)
        if not isinstance(record, dict):
            kept.append(item)
            continue
        if is_self_overlap_record(record, case_id=case_id, question=question):
            removed_ids.append(str(record.get("id") or record.get("case_id") or ""))
            continue
        kept.append(item)
    return kept, removed_ids
