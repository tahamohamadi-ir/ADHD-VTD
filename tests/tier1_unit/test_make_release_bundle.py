from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from scripts.make_release_bundle import (  # noqa: E402
    build_arg_parser,
    build_bundle,
    select_bundle_files,
    sha256_file,
)


def test_select_bundle_files_excludes_caches_and_binaries(tmp_path):
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "src" / "__pycache__").mkdir()
    (tmp_path / "src" / "__pycache__" / "mod.cpython-312.pyc").write_bytes(b"\x00")
    (tmp_path / "data" / "schema").mkdir(parents=True)
    (tmp_path / "data" / "schema" / "frozen.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "db.sqlite").write_bytes(b"\x00")
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")

    selected = select_bundle_files(tmp_path)
    relatives = {p.relative_to(tmp_path).as_posix() for p in selected}

    assert "src/pkg/mod.py" in relatives
    assert "data/schema/frozen.json" in relatives
    assert "VERSION" in relatives
    assert all(not rel.endswith(".pyc") for rel in relatives)
    assert all(not rel.endswith(".sqlite") for rel in relatives)
    assert not any("__pycache__" in rel for rel in relatives)


def test_select_bundle_files_skips_oversized_files(tmp_path):
    big = tmp_path / "docs" / "big.bin"
    big.parent.mkdir(parents=True)
    big.write_bytes(b"0" * 3_000_000)

    selected = select_bundle_files(tmp_path)

    assert all(p.name != "big.bin" for p in selected)


def test_skip_gate_flag_is_rejected():
    with pytest.raises(SystemExit):
        build_arg_parser().parse_args(["--skip-gate"])


def test_build_bundle_writes_zip_manifest_and_checksum(tmp_path):
    root = tmp_path / "project"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text("# guide\n", encoding="utf-8")
    (root / "VERSION").write_text("0.1.0\n", encoding="utf-8")

    output_dir = tmp_path / "out"
    zip_path = build_bundle(root, output_dir, version="9.9.9")

    assert zip_path.exists()
    assert zip_path.parent == output_dir
    assert zip_path.name.startswith("pars-sql-9.9.9-")

    checksum_path = output_dir / f"{zip_path.name}.sha256"
    manifest_path = output_dir / f"{zip_path.name}.manifest.json"
    assert checksum_path.exists()
    assert manifest_path.exists()

    checksum_line = checksum_path.read_text(encoding="ascii")
    expected_hash = sha256_file(zip_path)
    assert checksum_line == f"{expected_hash}  {zip_path.name}\n"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key in (
        "bundle",
        "version",
        "generated_at_utc",
        "git_commit",
        "file_count",
        "files",
        "zip_sha256",
    ):
        assert key in manifest
    assert manifest["bundle"] == zip_path.name
    assert manifest["version"] == "9.9.9"
    assert manifest["zip_sha256"] == expected_hash
    assert manifest["file_count"] == len(manifest["files"])
    assert len(manifest["files"]) > 0

    arcnames = {entry["path"] for entry in manifest["files"]}
    assert {"src/pkg/mod.py", "docs/guide.md", "VERSION"} <= arcnames
    for entry in manifest["files"]:
        assert set(entry) == {"path", "sha256"}
        assert len(entry["sha256"]) == 64


def test_build_bundle_manifest_files_is_real_list_not_or_hack(tmp_path):
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.py").write_text("a = 1\n", encoding="utf-8")

    output_dir = tmp_path / "out"
    zip_path = build_bundle(root, output_dir, version="0.0.1")

    manifest_path = output_dir / f"{zip_path.name}.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(manifest["files"], list)
    assert len(manifest["files"]) == 1
