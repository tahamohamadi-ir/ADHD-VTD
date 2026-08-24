from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

YES = {"yes", "y", "true", "1", "✅", "درست", "بله", "ok", "pass"}
NO = {"no", "n", "false", "0", "❌", "غلط", "خیر", "fail"}
TBD = {"tbd", "", "-", "pending", "نامشخص"}


@dataclass(slots=True)
class AgreementSummary:
    reviewed_cases: int
    full_agreement: int
    partial_agreement: int
    disagreement: int
    agreement_percent: float
    cohens_kappa: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "reviewed_cases": self.reviewed_cases,
            "full_agreement": self.full_agreement,
            "partial_agreement": self.partial_agreement,
            "disagreement": self.disagreement,
            "agreement_percent": self.agreement_percent,
            "cohens_kappa": self.cohens_kappa,
        }


def normalize_label(value: Any) -> str | None:
    s = str(value or "").strip().lower()
    if s in YES:
        return "yes"
    if s in NO:
        return "no"
    if s in TBD:
        return None
    return s


def summarize_review_rows(rows: list[dict[str, Any]]) -> AgreementSummary:
    reviewed = []
    for r in rows:
        labels = [
            normalize_label(r.get("Gold SQL Correct?")),
            normalize_label(r.get("Tables Correct?")),
            normalize_label(r.get("Columns Correct?")),
            normalize_label(r.get("Values Correct?")),
            normalize_label(r.get("Needs Clarification?")),
        ]
        if any(x is not None for x in labels):
            reviewed.append(labels)

    full = partial = disagree = 0
    for labels in reviewed:
        scored = [x for x in labels if x is not None]
        if not scored:
            continue
        yes_count = sum(1 for x in scored if x == "yes")
        no_count = sum(1 for x in scored if x == "no")
        if no_count == 0 and yes_count == len(scored):
            full += 1
        elif yes_count > 0 and no_count > 0:
            partial += 1
        elif no_count > 0 and yes_count == 0:
            disagree += 1
        else:
            partial += 1

    total = len(reviewed)
    agreement_percent = round(100.0 * ((full + 0.5 * partial) / total), 2) if total else 0.0
    return AgreementSummary(total, full, partial, disagree, agreement_percent, None)


def parse_markdown_review_table(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    lines = p.read_text(encoding="utf-8").splitlines()
    table_lines = [line.strip() for line in lines if line.strip().startswith("|")]
    # Find the review table header.
    header_idx = None
    for i, line in enumerate(table_lines):
        if "Audit ID" in line and "Gold SQL Correct?" in line:
            header_idx = i
            break
    if header_idx is None:
        return []
    headers = [h.strip() for h in table_lines[header_idx].strip("|").split("|")]
    rows: list[dict[str, Any]] = []
    for line in table_lines[header_idx + 2 :]:
        if "Agreement Summary" in line:
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def summarize_markdown_review(path: str | Path) -> AgreementSummary:
    return summarize_review_rows(parse_markdown_review_table(path))


def cohens_kappa(labels_a: list[str], labels_b: list[str]) -> float | None:
    if len(labels_a) != len(labels_b) or not labels_a:
        return None
    pairs = [(a, b) for a, b in zip(labels_a, labels_b) if a is not None and b is not None]
    if not pairs:
        return None
    total = len(pairs)
    observed = sum(1 for a, b in pairs if a == b) / total
    cats = sorted(set([x for pair in pairs for x in pair]))
    pe = 0.0
    for c in cats:
        pa = sum(1 for a, _ in pairs if a == c) / total
        pb = sum(1 for _, b in pairs if b == c) / total
        pe += pa * pb
    if pe == 1.0:
        return 1.0
    return round((observed - pe) / (1 - pe), 4)
