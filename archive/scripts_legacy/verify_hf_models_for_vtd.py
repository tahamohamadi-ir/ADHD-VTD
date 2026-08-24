#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verify VTD Hugging Face model downloads.

This script is designed to be placed next to download_hf_models_for_vtd.py:

    D:\Project\ADHD-VTD\scripts\verify_hf_models_for_vtd.py

Usage on Windows PowerShell:

    cd D:\Project\ADHD-VTD
    $env:PYTHONIOENCODING = "utf-8"
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

    python .\scripts\verify_hf_models_for_vtd.py --models-root .\models

Strict mode, fail if any expected model is missing/incomplete:

    python .\scripts\verify_hf_models_for_vtd.py --models-root .\models --strict

Only retrieval models:

    python .\scripts\verify_hf_models_for_vtd.py --models-root .\models --only retrieval --strict

What it checks:
  - GGUF files exist.
  - GGUF header starts with b"GGUF".
  - Local file size matches Hugging Face repo metadata when available.
  - Snapshot models have the expected allow-pattern files.
  - Snapshot file sizes match Hugging Face repo metadata when available.
  - Writes a JSON report to models/model_integrity_report.json by default.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

try:
    from huggingface_hub import HfApi
    from huggingface_hub.errors import GatedRepoError, RepositoryNotFoundError, HfHubHTTPError
except Exception as exc:  # pragma: no cover
    print("ERROR: huggingface_hub is not installed.")
    print("Install it with:")
    print("  python -m pip install -U huggingface_hub")
    print(f"Original import error: {exc}")
    raise SystemExit(2)


MIN_GGUF_SIZE_BYTES = 50 * 1024 * 1024  # conservative sanity threshold


def load_downloader_module() -> Any:
    here = Path(__file__).resolve().parent
    candidate = here / "download_hf_models_for_vtd.py"
    if not candidate.exists():
        raise SystemExit(
            "Cannot find download_hf_models_for_vtd.py next to this verifier. "
            "Put both scripts in the same scripts/ folder."
        )
    spec = importlib.util.spec_from_file_location("download_hf_models_for_vtd", candidate)
    if spec is None or spec.loader is None:
        raise SystemExit("Could not import download_hf_models_for_vtd.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["download_hf_models_for_vtd"] = module
    spec.loader.exec_module(module)
    return module


def get_remote_files(api: HfApi, repo_id: str, token: Optional[str]) -> dict[str, Optional[int]]:
    info = api.model_info(repo_id=repo_id, files_metadata=True, token=token)
    files: dict[str, Optional[int]] = {}
    for sibling in info.siblings:
        rfilename = getattr(sibling, "rfilename", None)
        if not rfilename:
            continue
        size = getattr(sibling, "size", None)
        files[str(rfilename)] = int(size) if size is not None else None
    return files


def match_patterns(path: str, allow_patterns: list[str], ignore_patterns: list[str]) -> bool:
    p = path.replace("\\", "/")
    allowed = any(fnmatch.fnmatch(p, pat) for pat in allow_patterns) if allow_patterns else True
    ignored = any(fnmatch.fnmatch(p, pat) for pat in ignore_patterns) if ignore_patterns else False
    return allowed and not ignored


def check_file_size(local_path: Path, expected_size: Optional[int]) -> tuple[bool, str]:
    if expected_size is None:
        return True, "remote_size_unavailable"
    actual = local_path.stat().st_size
    if actual == expected_size:
        return True, f"size_ok:{actual}"
    return False, f"size_mismatch: local={actual}, remote={expected_size}"


def verify_gguf(spec: Any, root: Path, downloader: Any, api: HfApi, token: Optional[str]) -> dict[str, Any]:
    t0 = time.time()
    result: dict[str, Any] = {
        "label": spec.label,
        "repo_id": spec.repo_id,
        "kind": spec.kind,
        "format": spec.format,
        "checks": [],
        "status": "unknown",
    }

    try:
        selected = downloader.select_gguf_file(
            spec.repo_id,
            preferred_filename=spec.preferred_filename,
            quant_preferences=tuple(dict.fromkeys(["Q4_K_M", *downloader.DEFAULT_QUANT_PREFERENCES])),
            exclude_name_contains=spec.exclude_name_contains,
            token=token,
        )
        result["selected_file"] = selected
    except Exception as exc:
        result["status"] = "failed_remote_selection"
        result["error"] = repr(exc)
        result["seconds"] = round(time.time() - t0, 2)
        return result

    local = downloader.has_existing_gguf(root, spec, selected_filename=Path(selected).name)
    if not local:
        result["status"] = "missing"
        result["checks"].append({"name": "local_file_exists", "ok": False, "detail": "No matching .gguf found."})
        result["seconds"] = round(time.time() - t0, 2)
        return result

    local = Path(local)
    result["local_path"] = str(local)
    result["checks"].append({"name": "local_file_exists", "ok": True, "detail": str(local)})

    size = local.stat().st_size
    size_ok = size >= MIN_GGUF_SIZE_BYTES
    result["checks"].append({"name": "minimum_size", "ok": size_ok, "detail": f"{size} bytes"})

    try:
        with local.open("rb") as f:
            header = f.read(4)
        header_ok = header == b"GGUF"
        result["checks"].append({"name": "gguf_header", "ok": header_ok, "detail": repr(header)})
    except Exception as exc:
        result["checks"].append({"name": "gguf_header", "ok": False, "detail": repr(exc)})

    try:
        remote_files = get_remote_files(api, spec.repo_id, token)
        expected_size = remote_files.get(selected)
        ok, detail = check_file_size(local, expected_size)
        result["checks"].append({"name": "remote_size_match", "ok": ok, "detail": detail})
    except Exception as exc:
        result["checks"].append({"name": "remote_size_match", "ok": None, "detail": f"not_checked:{repr(exc)}"})

    hard_checks = [c for c in result["checks"] if c["ok"] is not None]
    result["status"] = "ok" if all(c["ok"] for c in hard_checks) else "bad"
    result["seconds"] = round(time.time() - t0, 2)
    return result


def verify_snapshot(spec: Any, root: Path, downloader: Any, api: HfApi, token: Optional[str]) -> dict[str, Any]:
    t0 = time.time()
    result: dict[str, Any] = {
        "label": spec.label,
        "repo_id": spec.repo_id,
        "kind": spec.kind,
        "format": spec.format,
        "checks": [],
        "missing_files": [],
        "size_mismatches": [],
        "status": "unknown",
    }

    local_dir = downloader.has_existing_snapshot(root, spec)
    if not local_dir:
        result["status"] = "missing"
        result["checks"].append({"name": "local_snapshot_exists", "ok": False, "detail": "No matching snapshot folder found."})
        result["seconds"] = round(time.time() - t0, 2)
        return result

    local_dir = Path(local_dir)
    result["local_path"] = str(local_dir)
    result["checks"].append({"name": "local_snapshot_exists", "ok": True, "detail": str(local_dir)})

    try:
        remote_files = get_remote_files(api, spec.repo_id, token)
        expected = {
            name: size for name, size in remote_files.items()
            if match_patterns(name, downloader.SNAPSHOT_ALLOW_PATTERNS, downloader.SNAPSHOT_IGNORE_PATTERNS)
        }
        result["expected_file_count"] = len(expected)

        has_model_weight = False
        for rel, expected_size in sorted(expected.items()):
            p = local_dir / rel
            if not p.exists():
                result["missing_files"].append(rel)
                continue
            if rel.endswith((".safetensors", ".bin")):
                has_model_weight = True
            ok, detail = check_file_size(p, expected_size)
            if not ok:
                result["size_mismatches"].append({"file": rel, "detail": detail})

        # Local sanity checks even if remote metadata is incomplete.
        config_ok = (local_dir / "config.json").exists() or (local_dir / "modules.json").exists()
        result["checks"].append({"name": "config_or_modules", "ok": config_ok, "detail": "config.json or modules.json"})

        local_has_weight = any(local_dir.rglob("*.safetensors")) or any(local_dir.rglob("*.bin"))
        result["checks"].append({"name": "model_weight_exists", "ok": local_has_weight or has_model_weight, "detail": "*.safetensors or *.bin"})

        missing_ok = len(result["missing_files"]) == 0
        mismatch_ok = len(result["size_mismatches"]) == 0
        result["checks"].append({"name": "all_expected_files_present", "ok": missing_ok, "detail": f"missing={len(result['missing_files'])}"})
        result["checks"].append({"name": "all_sizes_match", "ok": mismatch_ok, "detail": f"mismatches={len(result['size_mismatches'])}"})

    except Exception as exc:
        result["checks"].append({"name": "remote_snapshot_metadata", "ok": None, "detail": f"not_checked:{repr(exc)}"})
        config_ok = (local_dir / "config.json").exists() or (local_dir / "modules.json").exists()
        local_has_weight = any(local_dir.rglob("*.safetensors")) or any(local_dir.rglob("*.bin"))
        result["checks"].append({"name": "config_or_modules", "ok": config_ok, "detail": "config.json or modules.json"})
        result["checks"].append({"name": "model_weight_exists", "ok": local_has_weight, "detail": "*.safetensors or *.bin"})

    hard_checks = [c for c in result["checks"] if c["ok"] is not None]
    result["status"] = "ok" if hard_checks and all(c["ok"] for c in hard_checks) else "bad"
    result["seconds"] = round(time.time() - t0, 2)
    return result


def main() -> int:
    downloader = load_downloader_module()

    parser = argparse.ArgumentParser(description="Verify VTD Hugging Face model downloads.")
    parser.add_argument("--models-root", type=Path, default=Path("models"), help="Root folder where models are stored. Default: ./models")
    parser.add_argument("--only", choices=["all", "generation", "small-generation", "medium-generation", "large-generation", "retrieval", "embeddings", "rerankers"], default="all", help="Which model group to verify.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero if any selected model is missing/bad.")
    parser.add_argument("--report", type=Path, default=None, help="Report JSON path. Default: models/model_integrity_report.json")
    args = parser.parse_args()

    root = args.models_root.resolve()
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    selected = downloader.select_models(args.only)
    api = HfApi()

    print("=" * 80)
    print("VTD Model Integrity Verifier")
    print(f"models_root: {root}")
    print(f"mode:        {args.only}")
    print(f"strict:      {args.strict}")
    print(f"hf_token:    {'set' if token else 'not set'}")
    print(f"models:      {len(selected)}")
    print("=" * 80)

    report: list[dict[str, Any]] = []
    for i, spec in enumerate(selected, start=1):
        print(f"\n[{i}/{len(selected)}] {spec.label}")
        print(f"repo: {spec.repo_id}")
        try:
            if spec.format == "gguf":
                result = verify_gguf(spec, root, downloader, api, token)
            else:
                result = verify_snapshot(spec, root, downloader, api, token)
        except GatedRepoError as exc:
            result = {"label": spec.label, "repo_id": spec.repo_id, "status": "failed_gated_repo", "error": str(exc)}
        except RepositoryNotFoundError as exc:
            result = {"label": spec.label, "repo_id": spec.repo_id, "status": "failed_repo_not_found_or_private", "error": str(exc)}
        except HfHubHTTPError as exc:
            result = {"label": spec.label, "repo_id": spec.repo_id, "status": "failed_hf_http_error", "error": str(exc)}
        except Exception as exc:
            result = {"label": spec.label, "repo_id": spec.repo_id, "status": "failed", "error": repr(exc)}

        report.append(result)
        print(f"status: {result.get('status')}")
        if result.get("local_path"):
            print(f"path:   {result['local_path']}")
        if result.get("selected_file"):
            print(f"file:   {result['selected_file']}")
        bad_checks = [c for c in result.get("checks", []) if c.get("ok") is False]
        for c in bad_checks[:5]:
            print(f"  [BAD] {c['name']}: {c['detail']}")
        if len(bad_checks) > 5:
            print(f"  ... {len(bad_checks) - 5} more bad checks")
        if result.get("missing_files"):
            print(f"  missing files: {len(result['missing_files'])}")
        if result.get("size_mismatches"):
            print(f"  size mismatches: {len(result['size_mismatches'])}")

    out = args.report or (root / "model_integrity_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    counts: dict[str, int] = {}
    for item in report:
        status = str(item.get("status"))
        counts[status] = counts.get(status, 0) + 1

    print("\n" + "=" * 80)
    print(f"Integrity report written to: {out}")
    print("Summary:")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")
    print("=" * 80)

    bad = [x for x in report if x.get("status") not in {"ok"}]
    if args.strict and bad:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
