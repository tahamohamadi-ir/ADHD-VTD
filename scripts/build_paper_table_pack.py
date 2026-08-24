from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.paths import DOCS_DIR, RESULTS_DIR  # noqa: E402
from src.evaluation.paper_pack import (  # noqa: E402
    PROMOTION_ALLOWED_STATUSES,
    PromotionRow,
    build_manifest_payload,
    evaluate_promotion_rows,
    parse_promotion_bool,
    parse_promotion_registry,
    render_paper_tables,
    set_promotion_status,
    sha256_text,
)

DEFAULT_PROMOTION_DOC = DOCS_DIR / "PARS_SQL_PAPER1_REPRODUCIBILITY.md"
DEFAULT_OUTPUT_DIR = RESULTS_DIR / "reports"
PAPER_TABLES_NAME = "paper_tables.md"
FINAL_MANIFEST_NAME = "final_artifact_manifest.json"
CURRENT_MANIFEST_NAME = "current_paper1_artifact_manifest.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild the central paper table pack and artifact manifests from the "
            "promotion registry, verifying every paper_final scope."
        )
    )
    parser.add_argument(
        "--promotion-doc",
        type=Path,
        default=DEFAULT_PROMOTION_DOC,
        help="Markdown document holding the promotion registry table.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory receiving paper_tables.md and both manifest JSON files.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: compute everything and print the plan without writing files.",
    )
    parser.add_argument(
        "--include-diagnostic",
        action="store_true",
        help="Append a traceability-only diagnostic section (never paper-final).",
    )
    parser.add_argument(
        "--set-promotion-status",
        metavar="SCOPE",
        default=None,
        help="Rewrite the Status/Paper Metric Allowed cells of this registry scope.",
    )
    parser.add_argument(
        "--new-status",
        choices=sorted(PROMOTION_ALLOWED_STATUSES),
        default=None,
        help="New status for --set-promotion-status.",
    )
    parser.add_argument(
        "--paper-metric-allowed",
        choices=["true", "false", "yes", "no", "1", "0"],
        default=None,
        help="New Paper Metric Allowed cell for --set-promotion-status (required).",
    )
    return parser


def _apply_status_override(
    registry_path: Path,
    text: str,
    args: argparse.Namespace,
) -> tuple[str, int]:
    rows = parse_promotion_registry(text)
    scope = args.set_promotion_status
    targets = [row for row in rows if row.get("scope", "").strip() == scope]
    if len(targets) != 1:
        print(
            f"error: expected exactly one registry row for scope {scope!r}, found {len(targets)}."
        )
        raise SystemExit(2)
    metric_allowed = parse_promotion_bool(args.paper_metric_allowed or "")
    if metric_allowed is None:
        print("error: --paper-metric-allowed is required with --set-promotion-status.")
        raise SystemExit(2)
    try:
        updated = set_promotion_status(
            text,
            artifact_path=targets[0]["artifact_path"],
            new_status=args.new_status,
            paper_metric_allowed=metric_allowed,
        )
    except ValueError as exc:
        print(f"error: {exc}")
        raise SystemExit(2) from exc
    if updated == text:
        print(f"registry: scope {scope!r} already has status={args.new_status}; no edit.")
        return text, 0
    if args.check:
        print(f"[check] would rewrite 1 promotion row for scope {scope!r} (no write).")
    else:
        registry_path.write_text(updated, encoding="utf-8")
        print(f"registry: rewrote Status/Paper Metric Allowed cells for {scope!r}.")
    return updated, 1


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    registry_path = args.promotion_doc
    if not registry_path.is_file():
        print(f"error: promotion doc not found: {registry_path}")
        return 2
    if (args.new_status or args.paper_metric_allowed) and not args.set_promotion_status:
        print("error: --new-status/--paper-metric-allowed require --set-promotion-status.")
        return 2
    text = registry_path.read_text(encoding="utf-8")
    if args.set_promotion_status:
        text, _ = _apply_status_override(registry_path, text, args)

    rows = parse_promotion_registry(text)
    if not rows:
        print(f"error: no promotion registry table found in {registry_path}")
        return 2
    promotions = [PromotionRow.from_cells(row) for row in rows]
    evaluations = evaluate_promotion_rows(
        promotions,
        root=PROJECT_ROOT,
        include_non_final=args.include_diagnostic,
        verify=True,
    )

    generated_date = datetime.now(timezone.utc).date().isoformat()
    try:
        registry_display = registry_path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        registry_display = registry_path.resolve().as_posix()
    tables_md = render_paper_tables(
        evaluations,
        generated_date=generated_date,
        registry_display=registry_display,
        include_diagnostic=args.include_diagnostic,
    )
    manifest_payload = build_manifest_payload(
        evaluations,
        generated_date=generated_date,
        registry_display=registry_display,
        registry_sha256=sha256_text(text),
        include_diagnostic=args.include_diagnostic,
    )
    manifest_text = json.dumps(manifest_payload, indent=2, ensure_ascii=False) + "\n"

    mode = "would be written" if args.check else "written"
    outputs = [
        (args.output_dir / PAPER_TABLES_NAME, tables_md),
        (args.output_dir / FINAL_MANIFEST_NAME, manifest_text),
        (args.output_dir / CURRENT_MANIFEST_NAME, manifest_text),
    ]

    included = [item.scope for item in evaluations if item.included]
    excluded = [item for item in evaluations if not item.included]
    print(f"Registry rows parsed: {len(rows)}")
    print(f"Included paper-final scopes ({len(included)}):")
    for scope in included:
        print(f"  + {scope}")
    if not included:
        print("  (none)")
    print(f"Excluded scopes ({len(excluded)}):")
    for item in excluded:
        print(f"  - {item.scope}: {item.exclusion_reason or 'diagnostic appendix'}")
    print(f"Diagnostic appendix: {'enabled' if args.include_diagnostic else 'disabled'}")
    print(f"Outputs {mode}:")
    for path, content in outputs:
        print(f"  - {path} ({len(content.encode('utf-8'))} bytes)")

    blocking = [item for item in excluded if item.row.is_paper_final]
    for item in blocking:
        print(f"blocking: paper_final scope {item.scope} not includable ({item.exclusion_reason})")
        for issue in item.verification_issues:
            print(f"    {issue}")

    if args.check:
        return 1 if blocking else 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for path, content in outputs:
        path.write_text(content, encoding="utf-8")
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
