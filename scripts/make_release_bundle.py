from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from _bootstrap_path import PROJECT_ROOT  # noqa: F401

BUNDLE_INCLUDED_TOP_LEVEL = [
    "src",
    "scripts",
    "docs",
    "data/schema",
    "experiments",
    "tests",
    "requirements.txt",
    "pyproject.toml",
    "README.md",
    "AGENTS.md",
    "VERSION",
    "LICENSE",
    "CHANGELOG.md",
]

BUNDLE_EXCLUDED_DIR_PARTS = {
    "__pycache__",
    ".venv",
    ".git",
    "node_modules",
}

BUNDLE_MAX_BYTES_PER_FILE = 2_000_000


def select_bundle_files(root: Path) -> list[Path]:
    selected: list[Path] = []
    for entry in BUNDLE_INCLUDED_TOP_LEVEL:
        path = root / entry
        if not path.exists():
            continue
        if path.is_file():
            selected.append(path)
            continue
        for file_path in sorted(path.rglob("*")):
            if not file_path.is_file():
                continue
            if BUNDLE_EXCLUDED_DIR_PARTS & set(file_path.parts):
                continue
            if file_path.suffix.lower() in {".pyc", ".pyo", ".db", ".sqlite"}:
                continue
            if file_path.stat().st_size > BUNDLE_MAX_BYTES_PER_FILE:
                continue
            selected.append(file_path)
    return sorted(set(selected))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(root: Path) -> str | None:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            or None
        )
    except (subprocess.CalledProcessError, OSError):
        return None


def build_bundle(root: Path, output_dir: Path, *, version: str) -> Path:
    files = select_bundle_files(root)
    if not files:
        raise RuntimeError("No bundle files selected; check include list.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"pars-sql-{version}-{stamp}.zip"

    manifest: dict[str, object] = {
        "bundle": zip_path.name,
        "version": version,
        "generated_at_utc": stamp,
        "git_commit": git_commit(root),
        "file_count": len(files),
        "files": [],
    }
    file_entries: list[dict[str, str]] = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            arcname = file_path.relative_to(root).as_posix()
            archive.write(file_path, arcname)
            file_entries.append({"path": arcname, "sha256": sha256_file(file_path)})
    manifest["files"] = file_entries

    checksum_line = f"{sha256_file(zip_path)}  {zip_path.name}\n"
    (output_dir / f"{zip_path.name}.sha256").write_text(checksum_line, encoding="ascii")
    manifest["zip_sha256"] = checksum_line.split()[0]
    (output_dir / f"{zip_path.name}.manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return zip_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a reproducible release bundle (code + docs + configs only)."
    )
    parser.add_argument("--output-dir", default="dist")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    root = Path(PROJECT_ROOT)
    version_file = root / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "0.0.0"

    try:
        zip_path = build_bundle(root, root / args.output_dir, version=version)
    except Exception as exc:
        print(f"Bundle build failed: {type(exc).__name__}: {exc}")
        return 1
    print(f"built {zip_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
