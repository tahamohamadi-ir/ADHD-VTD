#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
VTD / ADHD-VTD Hugging Face Model Downloader + Verifier + Repairer v1.0.5
===================================================================

This script combines model downloading, integrity verification, and automatic repair.

Registry policy in v1.0.5:
    - Prefer official Qwen GGUF repos where available.
    - Prefer ggml-org GGUF repos for Qwen3 laptop/llama.cpp execution.
    - Use Unsloth for Qwen3.5-4B GGUF because it provides explicit Q4_K_M files.
    - Use Google official Gemma QAT GGUF for Gemma-3-1B.

Windows PowerShell usage:

    cd D:\Project\ADHD-VTD
    .\.venv\Scripts\python.exe -m pip install -U huggingface_hub hf_transfer

    $env:HF_TOKEN = "hf_xxx"                 # optional; needed for gated models
    $env:HF_HUB_ENABLE_HF_TRANSFER = "1"     # optional; faster downloads
    $env:PYTHONIOENCODING = "utf-8"
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Verify + download missing + repair corrupted:

    python .\scripts\download_and_repair_hf_models_for_vtd.py --models-root .\models

Group downloads:

    python .\scripts\download_and_repair_hf_models_for_vtd.py --models-root .\models --only small-generation
    python .\scripts\download_and_repair_hf_models_for_vtd.py --models-root .\models --only medium-generation
    python .\scripts\download_and_repair_hf_models_for_vtd.py --models-root .\models --only retrieval

Recommended first baseline group:

    python .\scripts\download_and_repair_hf_models_for_vtd.py --models-root .\models --only baseline

Only verify, do not download/repair:

    python .\scripts\download_and_repair_hf_models_for_vtd.py --models-root .\models --verify-only

Only one or more labels:

    python .\scripts\download_and_repair_hf_models_for_vtd.py --models-root .\models --labels Qwen2.5-Coder-3B-Instruct-GGUF,Qwen3-4B-Instruct-2507-GGUF

Strict CI mode: exit 1 if any selected model is not OK after processing:

    python .\scripts\download_and_repair_hf_models_for_vtd.py --models-root .\models --only baseline --strict
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import sys
import time

# Stable defaults for Windows / unstable networks.
# hf_transfer can be faster, but on some networks it stalls at 0%.
# Enable it explicitly with: $env:VTD_USE_HF_TRANSFER = "1"
if os.environ.get("VTD_USE_HF_TRANSFER", "0").strip().lower() not in {"1", "true", "yes", "on"}:
    os.environ.pop("HF_HUB_ENABLE_HF_TRANSFER", None)
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "30")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Optional

try:
    from huggingface_hub import (
        HfApi,
        hf_hub_download,
        hf_hub_url,
        list_repo_files,
        snapshot_download,
    )
    try:
        from huggingface_hub import get_hf_file_metadata
    except Exception:  # pragma: no cover
        get_hf_file_metadata = None  # type: ignore[assignment]
    from huggingface_hub.errors import GatedRepoError, HfHubHTTPError, RepositoryNotFoundError
except Exception as exc:  # pragma: no cover
    print("ERROR: huggingface_hub is not installed.")
    print("Install it with:")
    print("  python -m pip install -U huggingface_hub hf_transfer")
    print(f"Original import error: {exc}")
    raise SystemExit(2)


SCRIPT_VERSION = "1.0.5"

Kind = Literal["generation", "embedding", "reranker"]
Format = Literal["gguf", "snapshot"]
Tier = Literal["tiny", "small", "medium", "large", "retrieval"]


@dataclass(frozen=True)
class ModelSpec:
    label: str
    repo_id: str
    kind: Kind
    format: Format
    tier: Tier
    enabled: bool = True
    local_name_hints: tuple[str, ...] = ()
    preferred_filename: Optional[str] = None
    exclude_name_contains: tuple[str, ...] = ("mmproj", "vision", "projector")
    min_size_mb: int = 10


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class ModelResult:
    label: str
    repo_id: str
    kind: Kind
    format: Format
    tier: Tier
    status: str
    selected_file: Optional[str] = None
    local_path: Optional[str] = None
    canonical_path: Optional[str] = None
    repaired_from: Optional[str] = None
    backup_path: Optional[str] = None
    checks: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None
    seconds: float = 0.0


# --------------------------------------------------------------------------------------
# Model registry
# --------------------------------------------------------------------------------------

MODELS: list[ModelSpec] = [
    # Tiny/small generation baselines
    ModelSpec("Qwen2.5-Coder-0.5B-Instruct-GGUF", "Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF", "generation", "gguf", "tiny", local_name_hints=("qwen2.5-coder-0.5b", "qwen25-coder-05b"), min_size_mb=200),
    ModelSpec("Qwen3-0.6B-GGUF", "ggml-org/Qwen3-0.6B-GGUF", "generation", "gguf", "tiny", local_name_hints=("qwen3-0.6b", "qwen3-06b"), preferred_filename="Qwen3-0.6B-Q4_0.gguf", min_size_mb=300),
    ModelSpec("Llama-3.2-1B-Instruct-GGUF", "bartowski/Llama-3.2-1B-Instruct-GGUF", "generation", "gguf", "small", local_name_hints=("llama-3.2-1b", "llama32-1b"), min_size_mb=500),
    ModelSpec("Gemma-3-1B-Instruct-GGUF", "google/gemma-3-1b-it-qat-q4_0-gguf", "generation", "gguf", "small", local_name_hints=("gemma-3-1b", "gemma3-1b"), preferred_filename="gemma-3-1b-it-q4_0.gguf", min_size_mb=500),

    # 1.5B - 2B generation baselines
    ModelSpec("Qwen2.5-Coder-1.5B-Instruct-GGUF", "Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF", "generation", "gguf", "small", local_name_hints=("qwen2.5-coder-1.5b", "qwen25-coder-15b"), min_size_mb=700),
    ModelSpec("Qwen3-1.7B-GGUF", "ggml-org/Qwen3-1.7B-GGUF", "generation", "gguf", "small", local_name_hints=("qwen3-1.7b", "qwen3-17b"), preferred_filename="Qwen3-1.7B-Q4_K_M.gguf", min_size_mb=800),
    ModelSpec("SmolLM2-1.7B-Instruct-GGUF", "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF", "generation", "gguf", "small", local_name_hints=("smollm2-1.7b", "smollm2-17b"), min_size_mb=800),
    ModelSpec("Granite-3.3-2B-Instruct-GGUF", "ibm-granite/granite-3.3-2b-instruct-GGUF", "generation", "gguf", "small", local_name_hints=("granite-3.3-2b", "granite-2b"), min_size_mb=900),

    # 3B - 4B generation baselines
    ModelSpec("Qwen2.5-Coder-3B-Instruct-GGUF", "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF", "generation", "gguf", "medium", local_name_hints=("qwen2.5-coder-3b", "qwen25-coder-3b"), min_size_mb=1400),
    ModelSpec("Phi-4-mini-instruct-GGUF", "unsloth/Phi-4-mini-instruct-GGUF", "generation", "gguf", "medium", local_name_hints=("phi-4-mini", "phi4-mini"), min_size_mb=1800),
    # Disabled: this repo has repeatedly returned 404; keep the spec only for legacy local-file awareness.
    ModelSpec("Qwen3-4B-Instruct-2507-GGUF", "Qwen/Qwen3-4B-Instruct-2507-GGUF", "generation", "gguf", "medium", enabled=False, local_name_hints=("qwen3-4b-instruct-2507", "qwen3-4b"), preferred_filename="Qwen3-4B-Instruct-2507-Q4_K_M.gguf", min_size_mb=1800),
    ModelSpec("Qwen3-4B-GGUF", "ggml-org/Qwen3-4B-GGUF", "generation", "gguf", "medium", local_name_hints=("qwen3-4b",), preferred_filename="Qwen3-4B-Q4_K_M.gguf", min_size_mb=1800),
    ModelSpec("Qwen3.5-4B-GGUF", "unsloth/Qwen3.5-4B-GGUF", "generation", "gguf", "medium", local_name_hints=("qwen3.5-4b", "qwen35-4b"), preferred_filename="Qwen3.5-4B-Q4_K_M.gguf", min_size_mb=1800),
    ModelSpec("Llama-3.2-3B-Instruct-GGUF", "bartowski/Llama-3.2-3B-Instruct-GGUF", "generation", "gguf", "medium", local_name_hints=("llama-3.2-3b", "llama32-3b"), min_size_mb=1400),

    # 7B generation / Text-to-SQL baselines
    ModelSpec("Qwen2.5-Coder-7B-Instruct-GGUF", "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", "generation", "gguf", "large", local_name_hints=("qwen2.5-coder-7b", "qwen25-coder-7b"), min_size_mb=3000),
    ModelSpec("SQLCoder-7B-GGUF", "TheBloke/sqlcoder-7B-GGUF", "generation", "gguf", "large", local_name_hints=("sqlcoder-7b",), min_size_mb=3000),
    ModelSpec("NSQL-Llama-2-7B-GGUF", "TheBloke/nsql-llama-2-7B-GGUF", "generation", "gguf", "large", local_name_hints=("nsql-llama-2-7b", "nsql-7b"), min_size_mb=3000),
    ModelSpec("Mistral-7B-Instruct-v0.3-GGUF", "bartowski/Mistral-7B-Instruct-v0.3-GGUF", "generation", "gguf", "large", local_name_hints=("mistral-7b-instruct-v0.3", "mistral-7b"), min_size_mb=3000),

    # Embeddings
    ModelSpec("multilingual-e5-small", "intfloat/multilingual-e5-small", "embedding", "snapshot", "retrieval", local_name_hints=("multilingual-e5-small",), min_size_mb=30),
    ModelSpec("paraphrase-multilingual-mpnet-base-v2", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2", "embedding", "snapshot", "retrieval", local_name_hints=("paraphrase-multilingual-mpnet-base-v2",), min_size_mb=300),
    ModelSpec("bge-m3", "BAAI/bge-m3", "embedding", "snapshot", "retrieval", local_name_hints=("bge-m3",), min_size_mb=1000),
    ModelSpec("Qwen3-Embedding-0.6B", "Qwen/Qwen3-Embedding-0.6B", "embedding", "snapshot", "retrieval", local_name_hints=("qwen3-embedding-0.6b", "qwen3-embedding-06b"), min_size_mb=300),

    # Rerankers
    ModelSpec("bge-reranker-base", "BAAI/bge-reranker-base", "reranker", "snapshot", "retrieval", local_name_hints=("bge-reranker-base",), min_size_mb=300),
    ModelSpec("bge-reranker-v2-m3", "BAAI/bge-reranker-v2-m3", "reranker", "snapshot", "retrieval", local_name_hints=("bge-reranker-v2-m3",), min_size_mb=1000),
]

DEFAULT_QUANT_PREFERENCES = ("Q4_K_M", "Q4_K_S", "Q4_0", "IQ4_XS", "IQ4_NL", "Q5_K_M", "Q5_K_S", "Q8_0")

SNAPSHOT_ALLOW_PATTERNS = [
    "*.json", "*.txt", "*.md", "*.py", "*.safetensors", "*.bin", "*.model",
    "tokenizer*", "vocab*", "merges.txt", "sentencepiece.bpe.model", "spiece.model",
    "sentence_bert_config.json", "modules.json", "config_sentence_transformers.json",
    "1_Pooling/*", "2_Normalize/*",
]

SNAPSHOT_IGNORE_PATTERNS = [
    "*.h5", "*.ot", "*.msgpack", "*.onnx", "onnx/*", "openvino/*", ".git/*",
    "*.tflite", "tf_model*", "flax_model*",
]

# Some local folders from older scripts used singular names. We still detect them, but repair
# downloads go to canonical plural folders.
LEGACY_SUBDIRS = {
    "generation": ("generation",),
    "embedding": ("embeddings", "embedding"),
    "reranker": ("rerankers", "reranker"),
}


# --------------------------------------------------------------------------------------
# Utility functions
# --------------------------------------------------------------------------------------

def safe_repo_name(repo_id: str) -> str:
    return repo_id.replace("/", "__").replace(":", "_")


def normalize_for_search(text: str) -> str:
    text = text.lower().replace("_", "-")
    text = re.sub(r"[^a-z0-9.\-]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def now_stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (p for p in root.rglob("*") if p.is_file())


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return -1


def size_mb(size_bytes: int) -> float:
    return round(size_bytes / (1024 * 1024), 2)


def check(name: str, ok: bool, detail: str = "") -> Check:
    return Check(name=name, ok=ok, detail=detail)


def checks_to_dicts(checks: list[Check]) -> list[dict[str, Any]]:
    return [asdict(c) for c in checks]


def all_ok(checks: list[Check]) -> bool:
    return all(c.ok for c in checks)


def backup_path_for(path: Path, suffix: str = "bad") -> Path:
    stamp = now_stamp()
    candidate = path.with_name(f"{path.name}.{suffix}_{stamp}")
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.{suffix}_{stamp}_{counter}")
        counter += 1
    return candidate


def backup_or_delete(path: Path, *, delete_bad: bool) -> Optional[Path]:
    if not path.exists():
        return None
    if delete_bad:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        return None
    target = backup_path_for(path)
    path.rename(target)
    return target


def canonical_dir(root: Path, spec: ModelSpec) -> Path:
    if spec.kind == "generation":
        return root / "generation" / safe_repo_name(spec.repo_id)
    if spec.kind == "embedding":
        return root / "embeddings" / safe_repo_name(spec.repo_id)
    if spec.kind == "reranker":
        return root / "rerankers" / safe_repo_name(spec.repo_id)
    raise ValueError(spec.kind)


def canonical_gguf_path(root: Path, spec: ModelSpec, filename: str) -> Path:
    return canonical_dir(root, spec) / Path(filename).name


def pattern_allowed(filename: str, allow_patterns: list[str], ignore_patterns: list[str]) -> bool:
    normalized = filename.replace("\\", "/")
    if any(fnmatch.fnmatch(normalized, p) for p in ignore_patterns):
        return False
    return any(fnmatch.fnmatch(normalized, p) for p in allow_patterns)


def get_token() -> Optional[str]:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")


def try_get_remote_size(repo_id: str, filename: str, token: Optional[str]) -> Optional[int]:
    # Preferred path: exact file metadata HEAD request.
    if get_hf_file_metadata is not None:
        try:
            url = hf_hub_url(repo_id=repo_id, filename=filename, repo_type="model")
            meta = get_hf_file_metadata(url, token=token)  # type: ignore[misc]
            size = getattr(meta, "size", None)
            if isinstance(size, int):
                return size
        except Exception:
            pass

    # Fallback: model_info siblings sometimes contain size.
    try:
        api = HfApi(token=token)
        info = api.model_info(repo_id=repo_id, files_metadata=True)
        for s in getattr(info, "siblings", []) or []:
            if getattr(s, "rfilename", None) == filename:
                size = getattr(s, "size", None)
                if isinstance(size, int):
                    return size
    except Exception:
        pass
    return None


def remote_files_with_sizes(repo_id: str, token: Optional[str]) -> dict[str, Optional[int]]:
    result: dict[str, Optional[int]] = {}
    try:
        api = HfApi(token=token)
        info = api.model_info(repo_id=repo_id, files_metadata=True)
        for s in getattr(info, "siblings", []) or []:
            name = getattr(s, "rfilename", None)
            if not name:
                continue
            result[name] = getattr(s, "size", None)
        return result
    except Exception:
        pass

    # Fallback without sizes.
    try:
        for f in list_repo_files(repo_id=repo_id, repo_type="model", token=token):
            result[f] = None
    except Exception:
        pass
    return result


# --------------------------------------------------------------------------------------
# Remote file selection
# --------------------------------------------------------------------------------------

def select_gguf_file(
    repo_id: str,
    *,
    preferred_filename: Optional[str],
    quant_preferences: tuple[str, ...],
    exclude_name_contains: tuple[str, ...],
    token: Optional[str],
) -> str:
    files = list_repo_files(repo_id=repo_id, repo_type="model", token=token)
    ggufs = [f for f in files if f.lower().endswith(".gguf")]
    if not ggufs:
        raise RuntimeError(f"No .gguf files found in repo: {repo_id}")

    def allowed(name: str) -> bool:
        lower = name.lower()
        return not any(bad.lower() in lower for bad in exclude_name_contains)

    ggufs = [f for f in ggufs if allowed(f)]
    if not ggufs:
        raise RuntimeError(f"No allowed .gguf files found after exclusions in repo: {repo_id}")

    if preferred_filename:
        preferred_base = Path(preferred_filename).name.lower()
        for f in ggufs:
            if Path(f).name.lower() == preferred_base:
                return f

    for quant in quant_preferences:
        q = quant.lower()
        candidates = [f for f in ggufs if q in Path(f).name.lower()]
        if candidates:
            return sorted(candidates, key=lambda x: (len(x), x.lower()))[0]

    fallback_order = ("q3", "q4", "iq4", "q5", "q8", "f16", "bf16")
    for marker in fallback_order:
        candidates = [f for f in ggufs if marker in Path(f).name.lower()]
        if candidates:
            return sorted(candidates, key=lambda x: (len(x), x.lower()))[0]

    return sorted(ggufs, key=lambda x: (len(x), x.lower()))[0]


# --------------------------------------------------------------------------------------
# Local detection
# --------------------------------------------------------------------------------------

def find_exact_gguf(root: Path, filename: str) -> Optional[Path]:
    target = Path(filename).name.lower()
    if not root.exists():
        return None
    for p in iter_files(root):
        if p.suffix.lower() == ".gguf" and p.name.lower() == target:
            return p
    return None


def find_similar_gguf(root: Path, spec: ModelSpec) -> list[Path]:
    if not root.exists():
        return []
    hints = [normalize_for_search(spec.label), normalize_for_search(spec.repo_id.split("/")[-1])]
    hints += [normalize_for_search(h) for h in spec.local_name_hints]
    found: list[Path] = []
    for p in iter_files(root):
        if p.suffix.lower() != ".gguf":
            continue
        haystack = normalize_for_search(str(p.relative_to(root)))
        if any(h and h in haystack for h in hints):
            found.append(p)
    return found


def find_snapshot_dir(root: Path, spec: ModelSpec) -> Optional[Path]:
    expected_names = {
        safe_repo_name(spec.repo_id).lower(),
        spec.repo_id.split("/")[-1].lower(),
        spec.label.lower(),
        *[h.lower() for h in spec.local_name_hints],
    }

    candidates: list[Path] = []
    for sub in LEGACY_SUBDIRS.get(spec.kind, ()):  # canonical and legacy roots
        base = root / sub
        if base.exists():
            candidates.extend([base, *[p for p in base.rglob("*") if p.is_dir()]])

    # Include all dirs as a fallback for manually placed models.
    if root.exists():
        candidates.extend([p for p in root.rglob("*") if p.is_dir()])

    seen: set[Path] = set()
    for d in candidates:
        if d in seen:
            continue
        seen.add(d)
        name = d.name.lower()
        normalized_rel = normalize_for_search(str(d.relative_to(root))) if d.is_relative_to(root) else normalize_for_search(str(d))
        name_match = name in expected_names or any(h and h in name for h in expected_names) or any(normalize_for_search(h) in normalized_rel for h in expected_names if h)
        if not name_match:
            continue
        if (d / "config.json").exists() or (d / "modules.json").exists() or any(d.glob("*.safetensors")) or any(d.glob("*.bin")):
            return d
    return None


# --------------------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------------------

def verify_gguf_file(path: Optional[Path], spec: ModelSpec, selected_file: str, token: Optional[str]) -> tuple[bool, list[Check]]:
    checks: list[Check] = []
    if path is None:
        checks.append(check("local_file_exists", False, "No exact matching .gguf found."))
        return False, checks

    checks.append(check("local_file_exists", path.exists(), str(path)))
    if not path.exists():
        return False, checks

    checks.append(check("suffix_is_gguf", path.suffix.lower() == ".gguf", path.name))

    size = file_size(path)
    min_bytes = spec.min_size_mb * 1024 * 1024
    checks.append(check("local_size_reasonable", size >= min_bytes, f"local={size_mb(size)} MB, min={spec.min_size_mb} MB"))

    try:
        with path.open("rb") as f:
            magic = f.read(4)
        checks.append(check("gguf_magic_header", magic == b"GGUF", f"magic={magic!r}"))
    except Exception as exc:
        checks.append(check("gguf_magic_header", False, repr(exc)))

    remote_size = try_get_remote_size(spec.repo_id, selected_file, token)
    if remote_size is None:
        checks.append(check("remote_size_available", False, "Could not read remote file size; cannot compare."))
    else:
        checks.append(check("remote_size_match", size == remote_size, f"local={size}, remote={remote_size}"))

    return all_ok(checks), checks


def expected_snapshot_files(spec: ModelSpec, token: Optional[str]) -> dict[str, Optional[int]]:
    remote = remote_files_with_sizes(spec.repo_id, token)
    return {
        name: size
        for name, size in remote.items()
        if pattern_allowed(name, SNAPSHOT_ALLOW_PATTERNS, SNAPSHOT_IGNORE_PATTERNS)
    }


def verify_snapshot_dir(path: Optional[Path], spec: ModelSpec, token: Optional[str], *, max_size_mismatches_to_report: int = 20) -> tuple[bool, list[Check], dict[str, Any]]:
    checks: list[Check] = []
    details: dict[str, Any] = {"missing_files": [], "size_mismatches": []}

    if path is None:
        checks.append(check("local_snapshot_exists", False, "No matching snapshot folder found."))
        return False, checks, details

    checks.append(check("local_snapshot_exists", path.exists() and path.is_dir(), str(path)))
    if not path.exists() or not path.is_dir():
        return False, checks, details

    has_config = (path / "config.json").exists()
    has_modules = (path / "modules.json").exists()
    checks.append(check("config_or_modules_exists", has_config or has_modules, f"config.json={has_config}, modules.json={has_modules}"))

    weight_files = list(path.rglob("*.safetensors")) + list(path.rglob("*.bin"))
    checks.append(check("model_weight_exists", bool(weight_files), f"weights={len(weight_files)}"))

    expected = expected_snapshot_files(spec, token)
    if not expected:
        checks.append(check("remote_file_list_available", False, "Could not list expected remote files."))
        return all_ok(checks), checks, details
    checks.append(check("remote_file_list_available", True, f"expected={len(expected)} files"))

    missing: list[str] = []
    mismatches: list[dict[str, Any]] = []
    for rel, remote_size in expected.items():
        local = path / rel
        if not local.exists():
            missing.append(rel)
            continue
        if remote_size is not None:
            ls = file_size(local)
            if ls != remote_size:
                mismatches.append({"file": rel, "local": ls, "remote": remote_size})

    details["missing_files"] = missing[:max_size_mismatches_to_report]
    details["size_mismatches"] = mismatches[:max_size_mismatches_to_report]
    details["missing_count"] = len(missing)
    details["size_mismatch_count"] = len(mismatches)

    checks.append(check("all_expected_files_present", not missing, f"missing={len(missing)}"))
    checks.append(check("all_sizes_match", not mismatches, f"mismatches={len(mismatches)}"))

    return all_ok(checks), checks, details


# --------------------------------------------------------------------------------------
# Download and repair
# --------------------------------------------------------------------------------------

def download_gguf_to_canonical(spec: ModelSpec, root: Path, selected_file: str, token: Optional[str], *, force_download: bool) -> Path:
    local_dir = canonical_dir(root, spec)
    local_dir.mkdir(parents=True, exist_ok=True)
    downloaded = hf_hub_download(
        repo_id=spec.repo_id,
        filename=selected_file,
        repo_type="model",
        local_dir=str(local_dir),
        token=token,
        force_download=force_download,
    )
    return Path(downloaded)


def download_snapshot_to_canonical(spec: ModelSpec, root: Path, token: Optional[str], *, force_download: bool) -> Path:
    local_dir = canonical_dir(root, spec)
    local_dir.mkdir(parents=True, exist_ok=True)
    downloaded = snapshot_download(
        repo_id=spec.repo_id,
        repo_type="model",
        local_dir=str(local_dir),
        token=token,
        force_download=force_download,
        allow_patterns=SNAPSHOT_ALLOW_PATTERNS,
        ignore_patterns=SNAPSHOT_IGNORE_PATTERNS,
    )
    return Path(downloaded)


def process_gguf(
    spec: ModelSpec,
    root: Path,
    *,
    token: Optional[str],
    quant_preferences: tuple[str, ...],
    verify_only: bool,
    dry_run: bool,
    repair: bool,
    delete_bad: bool,
    force: bool,
) -> ModelResult:
    t0 = time.time()
    selected_file = select_gguf_file(
        spec.repo_id,
        preferred_filename=spec.preferred_filename,
        quant_preferences=quant_preferences,
        exclude_name_contains=spec.exclude_name_contains,
        token=token,
    )
    selected_base = Path(selected_file).name
    canonical = canonical_gguf_path(root, spec, selected_file)

    exact = canonical if canonical.exists() else find_exact_gguf(root, selected_base)
    ok, checks = verify_gguf_file(exact, spec, selected_file, token)

    warnings: list[str] = []
    similar = [p for p in find_similar_gguf(root, spec) if not exact or p.resolve() != exact.resolve()]
    if similar:
        warnings.append("similar_local_files_found_not_used: " + "; ".join(str(p) for p in similar[:5]))

    if ok and not force:
        return ModelResult(
            label=spec.label,
            repo_id=spec.repo_id,
            kind=spec.kind,
            format=spec.format,
            tier=spec.tier,
            status="ok_existing",
            selected_file=selected_file,
            local_path=str(exact),
            canonical_path=str(canonical),
            checks=checks_to_dicts(checks),
            warnings=warnings,
            seconds=round(time.time() - t0, 2),
        )

    if verify_only or dry_run:
        status = "bad_existing" if exact is not None else "missing_local"
        if dry_run:
            status = f"dry_run_{status}_would_download_or_repair"
        return ModelResult(
            label=spec.label,
            repo_id=spec.repo_id,
            kind=spec.kind,
            format=spec.format,
            tier=spec.tier,
            status=status,
            selected_file=selected_file,
            local_path=str(exact) if exact else None,
            canonical_path=str(canonical),
            checks=checks_to_dicts(checks),
            warnings=warnings,
            seconds=round(time.time() - t0, 2),
        )

    if not repair and exact is not None and not ok:
        return ModelResult(
            label=spec.label,
            repo_id=spec.repo_id,
            kind=spec.kind,
            format=spec.format,
            tier=spec.tier,
            status="bad_existing_no_repair",
            selected_file=selected_file,
            local_path=str(exact),
            canonical_path=str(canonical),
            checks=checks_to_dicts(checks),
            warnings=warnings,
            seconds=round(time.time() - t0, 2),
        )

    backup = None
    repaired_from = None
    if exact is not None and (force or not ok):
        repaired_from = str(exact)
        backup = backup_or_delete(exact, delete_bad=delete_bad)

    path = download_gguf_to_canonical(spec, root, selected_file, token, force_download=force)
    ok2, checks2 = verify_gguf_file(path, spec, selected_file, token)
    return ModelResult(
        label=spec.label,
        repo_id=spec.repo_id,
        kind=spec.kind,
        format=spec.format,
        tier=spec.tier,
        status="downloaded_missing" if exact is None else ("repaired_downloaded" if ok2 else "bad_after_repair"),
        selected_file=selected_file,
        local_path=str(path),
        canonical_path=str(canonical),
        repaired_from=repaired_from,
        backup_path=str(backup) if backup else None,
        checks=checks_to_dicts(checks2),
        warnings=warnings,
        seconds=round(time.time() - t0, 2),
    )


def process_snapshot(
    spec: ModelSpec,
    root: Path,
    *,
    token: Optional[str],
    verify_only: bool,
    dry_run: bool,
    repair: bool,
    delete_bad: bool,
    force: bool,
) -> ModelResult:
    t0 = time.time()
    canonical = canonical_dir(root, spec)
    local = canonical if canonical.exists() else find_snapshot_dir(root, spec)
    ok, checks, details = verify_snapshot_dir(local, spec, token)
    warnings: list[str] = []
    if details.get("missing_files"):
        warnings.append("missing_files_sample: " + "; ".join(details["missing_files"][:5]))
    if details.get("size_mismatches"):
        warnings.append("size_mismatches_sample: " + json.dumps(details["size_mismatches"][:3], ensure_ascii=False))

    if ok and not force:
        return ModelResult(
            label=spec.label,
            repo_id=spec.repo_id,
            kind=spec.kind,
            format=spec.format,
            tier=spec.tier,
            status="ok_existing",
            local_path=str(local),
            canonical_path=str(canonical),
            checks=checks_to_dicts(checks),
            warnings=warnings,
            seconds=round(time.time() - t0, 2),
        )

    if verify_only or dry_run:
        status = "bad_existing" if local is not None else "missing_local"
        if dry_run:
            status = f"dry_run_{status}_would_download_or_repair"
        return ModelResult(
            label=spec.label,
            repo_id=spec.repo_id,
            kind=spec.kind,
            format=spec.format,
            tier=spec.tier,
            status=status,
            local_path=str(local) if local else None,
            canonical_path=str(canonical),
            checks=checks_to_dicts(checks),
            warnings=warnings,
            seconds=round(time.time() - t0, 2),
        )

    if not repair and local is not None and not ok:
        return ModelResult(
            label=spec.label,
            repo_id=spec.repo_id,
            kind=spec.kind,
            format=spec.format,
            tier=spec.tier,
            status="bad_existing_no_repair",
            local_path=str(local),
            canonical_path=str(canonical),
            checks=checks_to_dicts(checks),
            warnings=warnings,
            seconds=round(time.time() - t0, 2),
        )

    backup = None
    repaired_from = None
    if local is not None and (force or not ok):
        repaired_from = str(local)
        backup = backup_or_delete(local, delete_bad=delete_bad)

    path = download_snapshot_to_canonical(spec, root, token, force_download=force)
    ok2, checks2, details2 = verify_snapshot_dir(path, spec, token)
    warnings2 = list(warnings)
    if details2.get("missing_files"):
        warnings2.append("post_repair_missing_files_sample: " + "; ".join(details2["missing_files"][:5]))
    if details2.get("size_mismatches"):
        warnings2.append("post_repair_size_mismatches_sample: " + json.dumps(details2["size_mismatches"][:3], ensure_ascii=False))

    return ModelResult(
        label=spec.label,
        repo_id=spec.repo_id,
        kind=spec.kind,
        format=spec.format,
        tier=spec.tier,
        status="downloaded_missing" if local is None else ("repaired_downloaded" if ok2 else "bad_after_repair"),
        local_path=str(path),
        canonical_path=str(canonical),
        repaired_from=repaired_from,
        backup_path=str(backup) if backup else None,
        checks=checks_to_dicts(checks2),
        warnings=warnings2,
        seconds=round(time.time() - t0, 2),
    )


# --------------------------------------------------------------------------------------
# Selection and CLI
# --------------------------------------------------------------------------------------

def select_models(mode: str) -> list[ModelSpec]:
    enabled = [m for m in MODELS if m.enabled]
    if mode == "all":
        return enabled
    if mode == "baseline":
        labels = {
            "Qwen2.5-Coder-3B-Instruct-GGUF",
            "Qwen2.5-Coder-7B-Instruct-GGUF",
            "Qwen3-4B-GGUF",
            "Qwen3.5-4B-GGUF",
            "multilingual-e5-small",
            "bge-m3",
            "bge-reranker-v2-m3",
        }
        return [m for m in enabled if m.label in labels]
    if mode == "generation":
        return [m for m in enabled if m.kind == "generation"]
    if mode == "small-generation":
        return [m for m in enabled if m.kind == "generation" and m.tier in {"tiny", "small"}]
    if mode == "medium-generation":
        return [m for m in enabled if m.kind == "generation" and m.tier in {"tiny", "small", "medium"}]
    if mode == "large-generation":
        return [m for m in enabled if m.kind == "generation" and m.tier == "large"]
    if mode == "edge":
        return [m for m in enabled if m.kind == "generation" and m.tier in {"tiny", "small"}]
    if mode == "retrieval":
        return [m for m in enabled if m.kind in {"embedding", "reranker"}]
    if mode == "embeddings":
        return [m for m in enabled if m.kind == "embedding"]
    if mode == "rerankers":
        return [m for m in enabled if m.kind == "reranker"]
    raise ValueError(f"Unknown --only mode: {mode}")


def filter_by_labels(models: list[ModelSpec], labels_csv: Optional[str]) -> list[ModelSpec]:
    if not labels_csv:
        return models
    requested = {x.strip().lower() for x in labels_csv.split(",") if x.strip()}
    selected = [m for m in models if m.label.lower() in requested or m.repo_id.lower() in requested]
    missing = requested - {m.label.lower() for m in selected} - {m.repo_id.lower() for m in selected}
    if missing:
        print("WARNING: unknown labels/repo_ids ignored:", ", ".join(sorted(missing)))
    return selected


def exclude_labels(models: list[ModelSpec], labels_csv: Optional[str]) -> list[ModelSpec]:
    if not labels_csv:
        return models
    excluded = {x.strip().lower() for x in labels_csv.split(",") if x.strip()}
    return [m for m in models if m.label.lower() not in excluded and m.repo_id.lower() not in excluded]


def start_from_label(models: list[ModelSpec], start_label: Optional[str]) -> list[ModelSpec]:
    if not start_label:
        return models
    needle = start_label.strip().lower()
    for idx, m in enumerate(models):
        if m.label.lower() == needle or m.repo_id.lower() == needle:
            return models[idx:]
    print(f"WARNING: --start-from-label not found: {start_label}; processing from beginning.")
    return models


def print_result(result: ModelResult) -> None:
    print(f"status: {result.status}")
    if result.selected_file:
        print(f"file:   {result.selected_file}")
    if result.local_path:
        print(f"path:   {result.local_path}")
    if result.repaired_from:
        print(f"repair: {result.repaired_from}")
    if result.backup_path:
        print(f"backup: {result.backup_path}")
    if result.error:
        print(f"error:  {result.error[:1200]}")
    bad_checks = [c for c in result.checks if not c.get("ok")]
    for c in bad_checks[:8]:
        print(f"  [BAD] {c.get('name')}: {c.get('detail')}")
    for w in result.warnings[:5]:
        print(f"  [WARN] {w[:1200]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download, verify, and repair VTD local models from Hugging Face. v1.0.5")
    parser.add_argument("--models-root", type=Path, default=Path("models"), help="Root folder to store models. Default: ./models")
    parser.add_argument(
        "--only",
        choices=["all", "baseline", "generation", "small-generation", "medium-generation", "large-generation", "edge", "retrieval", "embeddings", "rerankers"],
        default="all",
        help="Which model group to process.",
    )
    parser.add_argument("--labels", default=None, help="Comma-separated labels or repo_ids to process only selected models.")
    parser.add_argument("--exclude-labels", default=None, help="Comma-separated labels or repo_ids to skip after group selection.")
    parser.add_argument("--start-from-label", default=None, help="Skip selected models until this label/repo_id is reached, then continue.")
    parser.add_argument("--retries", type=int, default=2, help="Retries per model after transient Hugging Face/network failures. Default: 2")
    parser.add_argument("--retry-sleep", type=float, default=5.0, help="Seconds to sleep between retries. Default: 5")
    parser.add_argument("--quant", default=os.environ.get("GGUF_QUANT", "Q4_K_M"), help="Preferred GGUF quantization. Default: Q4_K_M. Fallbacks are automatic.")
    parser.add_argument("--verify-only", action="store_true", help="Only verify local files/folders. Do not download or repair.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded/repaired without changing files.")
    parser.add_argument("--no-repair", action="store_true", help="Do not repair bad existing local files; only download missing ones.")
    parser.add_argument("--force", action="store_true", help="Re-download selected models even if they verify OK.")
    parser.add_argument("--delete-bad", action="store_true", help="Delete bad files/folders instead of renaming them to *.bad_TIMESTAMP backup.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any selected model is not OK after processing.")
    parser.add_argument("--manifest", type=Path, default=None, help="Optional output JSON path. Default: models/download_repair_manifest.json")
    args = parser.parse_args()

    root = args.models_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    token = get_token()
    quant_preferences = tuple(dict.fromkeys([args.quant, *DEFAULT_QUANT_PREFERENCES]))
    selected = start_from_label(exclude_labels(filter_by_labels(select_models(args.only), args.labels), args.exclude_labels), args.start_from_label)
    repair = not args.no_repair
    manifest: list[dict[str, Any]] = []

    print("=" * 80)
    print("VTD Hugging Face Model Downloader + Verifier + Repairer v1.0.5")
    print(f"models_root: {root}")
    print(f"mode:        {args.only}")
    print(f"labels:      {args.labels or '-'}")
    print(f"exclude:     {args.exclude_labels or '-'}")
    print(f"start_from:  {args.start_from_label or '-'}")
    print(f"verify_only: {args.verify_only}")
    print(f"dry_run:     {args.dry_run}")
    print(f"repair:      {repair}")
    print(f"force:       {args.force}")
    print(f"strict:      {args.strict}")
    print(f"hf_token:    {'set' if token else 'not set'}")
    print(f"hf_transfer: {'enabled' if os.environ.get('HF_HUB_ENABLE_HF_TRANSFER') else 'disabled'}")
    print(f"etag_timeout: {os.environ.get('HF_HUB_ETAG_TIMEOUT')}")
    print(f"download_timeout: {os.environ.get('HF_HUB_DOWNLOAD_TIMEOUT')}")
    print(f"retries:     {args.retries}")
    print(f"models:      {len(selected)}")
    print("=" * 80)

    for i, spec in enumerate(selected, start=1):
        print(f"\n[{i}/{len(selected)}] {spec.label}")
        print(f"repo: {spec.repo_id}")
        print(f"kind: {spec.kind} | format: {spec.format} | tier: {spec.tier}")

        result: Optional[ModelResult] = None
        attempts = max(1, args.retries + 1)
        for attempt in range(1, attempts + 1):
            t0 = time.time()
            try:
                if attempt > 1:
                    print(f"retry attempt {attempt}/{attempts}...")
                if spec.format == "gguf":
                    result = process_gguf(
                        spec,
                        root,
                        token=token,
                        quant_preferences=quant_preferences,
                        verify_only=args.verify_only,
                        dry_run=args.dry_run,
                        repair=repair,
                        delete_bad=args.delete_bad,
                        force=args.force,
                    )
                else:
                    result = process_snapshot(
                        spec,
                        root,
                        token=token,
                        verify_only=args.verify_only,
                        dry_run=args.dry_run,
                        repair=repair,
                        delete_bad=args.delete_bad,
                        force=args.force,
                    )
                break
            except GatedRepoError as exc:
                result = ModelResult(spec.label, spec.repo_id, spec.kind, spec.format, spec.tier, "skipped_gated_repo", error=str(exc), seconds=round(time.time() - t0, 2))
                break
            except RepositoryNotFoundError as exc:
                result = ModelResult(spec.label, spec.repo_id, spec.kind, spec.format, spec.tier, "skipped_repo_not_found_or_private", error=str(exc), seconds=round(time.time() - t0, 2))
                break
            except HfHubHTTPError as exc:
                result = ModelResult(spec.label, spec.repo_id, spec.kind, spec.format, spec.tier, "skipped_hf_http_error", error=str(exc), seconds=round(time.time() - t0, 2))
                # HTTP 5xx / timeout-like errors may recover; retry those.
                if attempt < attempts:
                    print(f"temporary HF HTTP error; sleeping {args.retry_sleep}s before retry...")
                    time.sleep(args.retry_sleep)
                    continue
                break
            except KeyboardInterrupt:
                print("Interrupted by user. Writing partial manifest...")
                result = ModelResult(spec.label, spec.repo_id, spec.kind, spec.format, spec.tier, "interrupted", error="KeyboardInterrupt", seconds=round(time.time() - t0, 2))
                manifest.append(asdict(result))
                out_path = args.manifest or (root / "download_repair_manifest.json")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"Partial manifest written to: {out_path}")
                raise SystemExit(130)
            except Exception as exc:
                result = ModelResult(spec.label, spec.repo_id, spec.kind, spec.format, spec.tier, "failed", error=repr(exc), seconds=round(time.time() - t0, 2))
                if attempt < attempts:
                    print(f"error: {repr(exc)[:500]}")
                    print(f"sleeping {args.retry_sleep}s before retry...")
                    time.sleep(args.retry_sleep)
                    continue
                break

        if result is None:
            result = ModelResult(spec.label, spec.repo_id, spec.kind, spec.format, spec.tier, "failed", error="No result produced")
        print_result(result)
        manifest.append(asdict(result))

    out_path = args.manifest or (root / "download_repair_manifest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    counts: dict[str, int] = {}
    for item in manifest:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    print("\n" + "=" * 80)
    print(f"Manifest written to: {out_path}")
    print("Summary:")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")
    print("=" * 80)

    bad_statuses = {
        "bad_existing", "bad_existing_no_repair", "bad_after_repair", "missing_local", "failed",
        "skipped_hf_http_error", "skipped_repo_not_found_or_private", "skipped_gated_repo",
    }
    if args.strict and any(item["status"] in bad_statuses for item in manifest):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
