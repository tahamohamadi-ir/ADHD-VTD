from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _bootstrap_path import PROJECT_ROOT  # noqa: F401

from src.graph.workflow import create_workflow


def render_mermaid() -> str:
    compiled = create_workflow()
    graph = compiled.get_graph()
    mermaid = graph.draw_mermaid()
    if not isinstance(mermaid, str) or not mermaid.strip():
        raise RuntimeError("draw_mermaid returned an empty diagram")
    return mermaid.rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export the compiled LangGraph workflow as a Mermaid diagram."
    )
    parser.add_argument(
        "--output",
        default=str(Path(PROJECT_ROOT) / "docs" / "graph_workflow.mmd"),
        help="Output .mmd path (default: docs/graph_workflow.mmd).",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing file.")
    args = parser.parse_args()

    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        print(f"Refusing to overwrite existing file: {output_path} (use --force)")
        return 1

    try:
        mermaid = render_mermaid()
    except Exception as exc:
        print(f"Failed to export graph diagram: {type(exc).__name__}: {exc}")
        return 3

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(mermaid, encoding="utf-8")
    preview = "\n".join(mermaid.splitlines()[:5])
    print(preview)
    print(f"wrote {output_path} ({len(mermaid.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
