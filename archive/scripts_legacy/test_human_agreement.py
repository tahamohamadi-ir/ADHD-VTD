from __future__ import annotations

from pathlib import Path
from _bootstrap_path import PROJECT_ROOT
from src.evaluation.human_agreement import summarize_markdown_review


def main() -> int:
    path = PROJECT_ROOT / "data" / "audit" / "human_agreement_sample_50.md"
    if not path.exists():
        print(f"Human agreement file not found: {path}")
        return 0
    summary = summarize_markdown_review(path)
    print(summary.as_dict())
    print("Human agreement parser check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
