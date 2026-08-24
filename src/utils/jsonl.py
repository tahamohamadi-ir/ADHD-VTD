"""JSONL (JSON Lines) utilities for VTD pipeline.

Provides helpers to read, write, and append JSONL files — the standard
format for benchmark predictions, golden examples, and audit logs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read an entire JSONL file and return a list of dicts."""
    p = Path(path)
    if not p.exists():
        return []
    records: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL parse error at {p}:{line_no}: {exc}") from exc
    return records


def iter_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    """Lazily iterate over records in a JSONL file (memory-efficient)."""
    p = Path(path)
    if not p.exists():
        return
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                yield json.loads(stripped)


def write_jsonl(
    path: str | Path, records: list[dict[str, Any]], *, ensure_ascii: bool = False
) -> int:
    """Write a list of dicts as JSONL, overwriting the file. Returns record count."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=ensure_ascii, default=str) + "\n")
    return len(records)


def append_jsonl(path: str | Path, record: dict[str, Any], *, ensure_ascii: bool = False) -> None:
    """Append a single record to a JSONL file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=ensure_ascii, default=str) + "\n")


def append_jsonl_batch(
    path: str | Path, records: list[dict[str, Any]], *, ensure_ascii: bool = False
) -> int:
    """Append multiple records to a JSONL file. Returns count appended."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=ensure_ascii, default=str) + "\n")
    return len(records)
