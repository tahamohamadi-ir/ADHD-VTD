from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.retrieval.retrieval_scorer import RetrievedExample


@dataclass
class RetrievalContext:
    examples: list[dict[str, Any]]
    prompt_context: str
    diagnostics: list[dict[str, Any]]


class ContextBuilder:
    def build(self, retrieved: list[RetrievedExample], *, max_examples: int = 3) -> RetrievalContext:
        selected = retrieved[:max_examples]
        examples: list[dict[str, Any]] = []
        lines: list[str] = []
        diagnostics: list[dict[str, Any]] = []

        for idx, item in enumerate(selected, 1):
            record = item.record
            question = record.get("question_fa") or record.get("question") or ""
            sql = record.get("sql") or ""
            examples.append(
                {
                    "id": record.get("id"),
                    "question": question,
                    "question_fa": question,
                    "sql": sql,
                    "intent": record.get("intent"),
                    "tables": record.get("tables", []),
                    "difficulty": record.get("metadata", {}).get("difficulty") or record.get("difficulty"),
                    "why_relevant": ", ".join(item.reasons) or "ranked by retriever",
                }
            )
            lines.extend(
                [
                    f"Example {idx} ({record.get('id')}):",
                    f"Question: {question}",
                    f"Intent: {record.get('intent', 'unknown')}",
                    f"Tables: {', '.join(str(t) for t in record.get('tables', []))}",
                    f"Why relevant: {', '.join(item.reasons) or 'ranked by retriever'}",
                    "SQL:",
                    sql,
                    "",
                ]
            )
            diagnostics.append(item.to_dict())

        return RetrievalContext(
            examples=examples,
            prompt_context="\n".join(lines).strip(),
            diagnostics=diagnostics,
        )
