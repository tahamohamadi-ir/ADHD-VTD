#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Download local laptop-friendly VTD models from Hugging Face.

Usage on Windows PowerShell:

    cd D:\Project\ADHD-VTD
    .\.venv\Scripts\python.exe -m pip install -U huggingface_hub hf_transfer

    $env:HF_TOKEN = "hf_xxx"                 # optional, needed for gated models
    $env:HF_HUB_ENABLE_HF_TRANSFER = "1"     # optional, faster downloads

    python .\scripts\download_hf_models_for_vtd.py --models-root .\models

Dry run:

    python .\scripts\download_hf_models_for_vtd.py --models-root .\models --dry-run

Only small generation models:

    python .\scripts\download_hf_models_for_vtd.py --only small-generation

Only embedding/reranker models:

    python .\scripts\download_hf_models_for_vtd.py --only retrieval
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Optional

try:
    from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download
    from huggingface_hub.errors import GatedRepoError, RepositoryNotFoundError, HfHubHTTPError
except Exception as exc:  # pragma: no cover
    print("ERROR: huggingface_hub is not installed.")
    print("Install it with:")
    print("  python -m pip install -U huggingface_hub hf_transfer")
    print(f"Original import error: {exc}")
    raise SystemExit(2)


Kind = Literal["generation", "embedding", "reranker"]


@dataclass(frozen=True)
class ModelSpec:
    label: str
    repo_id: str
    kind: Kind
    format: Literal["gguf", "snapshot"]
    tier: Literal["small", "medium", "large", "retrieval"]
    enabled: bool = True
    local_name_hints: tuple[str, ...] = ()
    preferred_filename: Optional[str] = None
    exclude_name_contains: tuple[str, ...] = ("mmproj", "vision", "projector")


MODELS: list[ModelSpec] = [
    # Tiny/small generation baselines
    ModelSpec("Qwen2.5-Coder-0.5B-Instruct-GGUF", "Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF", "generation", "gguf", "small", local_name_hints=("qwen2.5-coder-0.5b", "qwen25-coder-05b")),
    ModelSpec("Qwen3-0.6B-GGUF", "Qwen/Qwen3-0.6B-GGUF", "generation", "gguf", "small", local_name_hints=("qwen3-0.6b", "qwen3-06b")),
    ModelSpec("Llama-3.2-1B-Instruct-GGUF", "bartowski/Llama-3.2-1B-Instruct-GGUF", "generation", "gguf", "small", local_name_hints=("llama-3.2-1b", "llama32-1b")),
    ModelSpec("Gemma-3-1B-Instruct-GGUF", "lm-kit/gemma-3-1b-instruct-gguf", "generation", "gguf", "small", local_name_hints=("gemma-3-1b", "gemma3-1b")),

    # 1.5B - 2B generation baselines
    ModelSpec("Qwen2.5-Coder-1.5B-Instruct-GGUF", "Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF", "generation", "gguf", "medium", local_name_hints=("qwen2.5-coder-1.5b", "qwen25-coder-15b")),
    ModelSpec("Qwen3-1.7B-GGUF", "ggml-org/Qwen3-1.7B-GGUF", "generation", "gguf", "medium", local_name_hints=("qwen3-1.7b", "qwen3-17b"), preferred_filename="Qwen3-1.7B-Q4_K_M.gguf"),
    ModelSpec("SmolLM2-1.7B-Instruct-GGUF", "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF", "generation", "gguf", "medium", local_name_hints=("smollm2-1.7b", "smollm2-17b")),
    ModelSpec("Granite-3.3-2B-Instruct-GGUF", "ibm-granite/granite-3.3-2b-instruct-GGUF", "generation", "gguf", "medium", local_name_hints=("granite-3.3-2b", "granite-2b")),

    # 3B - 4B generation baselines
    ModelSpec("Qwen2.5-Coder-3B-Instruct-GGUF", "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF", "generation", "gguf", "medium", local_name_hints=("qwen2.5-coder-3b", "qwen25-coder-3b")),
    ModelSpec("Phi-4-mini-instruct-GGUF", "unsloth/Phi-4-mini-instruct-GGUF", "generation", "gguf", "medium", local_name_hints=("phi-4-mini", "phi4-mini")),
    ModelSpec("Qwen3-4B-GGUF", "Qwen/Qwen3-4B-GGUF", "generation", "gguf", "medium", local_name_hints=("qwen3-4b",)),
    ModelSpec("Qwen3.5-4B-GGUF", "lmstudio-community/Qwen3.5-4B-GGUF", "generation", "gguf", "medium", local_name_hints=("qwen3.5-4b", "qwen35-4b"), preferred_filename="../models/generation/Qwen3.5-4B-Q4_K_M.gguf"),
    ModelSpec("Llama-3.2-3B-Instruct-GGUF", "bartowski/Llama-3.2-3B-Instruct-GGUF", "generation", "gguf", "medium", local_name_hints=("llama-3.2-3b", "llama32-3b")),

    # 7B generation / Text-to-SQL baselines
    ModelSpec("Qwen2.5-Coder-7B-Instruct-GGUF", "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", "generation", "gguf", "large", local_name_hints=("qwen2.5-coder-7b", "qwen25-coder-7b")),
    ModelSpec("SQLCoder-7B-GGUF", "TheBloke/sqlcoder-7B-GGUF", "generation", "gguf", "large", local_name_hints=("sqlcoder-7b",)),
    ModelSpec("NSQL-Llama-2-7B-GGUF", "TheBloke/nsql-llama-2-7B-GGUF", "generation", "gguf", "large", local_name_hints=("nsql-llama-2-7b", "nsql-7b")),
    ModelSpec("Mistral-7B-Instruct-v0.3-GGUF", "bartowski/Mistral-7B-Instruct-v0.3-GGUF", "generation", "gguf", "large", local_name_hints=("mistral-7b-instruct-v0.3", "mistral-7b")),

    # Embeddings
    ModelSpec("multilingual-e5-small", "intfloat/multilingual-e5-small", "embedding", "snapshot", "retrieval", local_name_hints=("multilingual-e5-small",)),
    ModelSpec("paraphrase-multilingual-mpnet-base-v2", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2", "embedding", "snapshot", "retrieval", local_name_hints=("paraphrase-multilingual-mpnet-base-v2",)),
    ModelSpec("bge-m3", "BAAI/bge-m3", "embedding", "snapshot", "retrieval", local_name_hints=("bge-m3",)),
    ModelSpec("Qwen3-Embedding-0.6B", "Qwen/Qwen3-Embedding-0.6B", "embedding", "snapshot", "retrieval", local_name_hints=("qwen3-embedding-0.6b", "qwen3-embedding-06b")),

    # Rerankers
    ModelSpec("bge-reranker-base", "BAAI/bge-reranker-base", "reranker", "snapshot", "retrieval", local_name_hints=("bge-reranker-base",)),
    ModelSpec("bge-reranker-v2-m3", "BAAI/bge-reranker-v2-m3", "reranker", "snapshot", "retrieval", local_name_hints=("bge-reranker-v2-m3",)),
]


DEFAULT_QUANT_PREFERENCES = ("Q4_K_M", "Q4_K_S", "Q4_0", "IQ4_XS", "IQ4_NL", "Q5_K_M", "Q5_K_S", "Q8_0")

SNAPSHOT_ALLOW_PATTERNS = [
    "*.json", "*.txt", "*.md", "*.py", "*.safetensors", "*.bin",
    "sentence_bert_config.json", "modules.json", "1_Pooling/*", "2_Normalize/*",
]

SNAPSHOT_IGNORE_PATTERNS = ["*.h5", "*.ot", "*.msgpack", "*.onnx", "onnx/*", "openvino/*", ".git/*"]


def safe_repo_name(repo_id: str) -> str:
    return repo_id.replace("/", "__").replace(":", "_")


def normalize_for_search(text: str) -> str:
    text = text.lower().replace("_", "-")
    text = re.sub(r"[^a-z0-9.\-]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (p for p in root.rglob("*") if p.is_file())


def has_existing_gguf(root: Path, spec: ModelSpec, selected_filename: Optional[str] = None) -> Optional[Path]:
    if not root.exists():
        return None

    if selected_filename:
        target_name = selected_filename.lower()
        for p in iter_files(root):
            if p.name.lower() == target_name:
                return p

    hints = [normalize_for_search(spec.label), normalize_for_search(spec.repo_id.split("/")[-1])]
    hints += [normalize_for_search(h) for h in spec.local_name_hints]

    for p in iter_files(root):
        if p.suffix.lower() != ".gguf":
            continue
        haystack = normalize_for_search(str(p.relative_to(root)))
        if any(h and h in haystack for h in hints):
            return p

    return None


def has_existing_snapshot(root: Path, spec: ModelSpec) -> Optional[Path]:
    if not root.exists():
        return None

    expected_names = {
        safe_repo_name(spec.repo_id).lower(),
        spec.repo_id.split("/")[-1].lower(),
        spec.label.lower(),
        *[h.lower() for h in spec.local_name_hints],
    }

    dirs = [root, *[p for p in root.rglob("*") if p.is_dir()]]
    for d in dirs:
        name = d.name.lower()
        if name in expected_names or any(h in name for h in expected_names if h):
            if (d / "config.json").exists() or (d / "modules.json").exists() or any(d.glob("*.safetensors")) or any(d.glob("*.bin")):
                return d

    hints = [normalize_for_search(spec.label), normalize_for_search(spec.repo_id.split("/")[-1])]
    hints += [normalize_for_search(h) for h in spec.local_name_hints]
    for p in root.rglob("config.json"):
        haystack = normalize_for_search(str(p.parent.relative_to(root)))
        if any(h and h in haystack for h in hints):
            return p.parent

    return None


def select_gguf_file(repo_id: str, *, preferred_filename: Optional[str], quant_preferences: tuple[str, ...], exclude_name_contains: tuple[str, ...], token: Optional[str]) -> str:
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
        for f in ggufs:
            if Path(f).name.lower() == preferred_filename.lower():
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


def download_gguf(spec: ModelSpec, root: Path, *, quant_preferences: tuple[str, ...], token: Optional[str], dry_run: bool, force: bool) -> dict:
    t0 = time.time()
    selected_filename = select_gguf_file(
        spec.repo_id,
        preferred_filename=spec.preferred_filename,
        quant_preferences=quant_preferences,
        exclude_name_contains=spec.exclude_name_contains,
        token=token,
    )

    existing = None if force else has_existing_gguf(root, spec, selected_filename=Path(selected_filename).name)
    if existing:
        return {"label": spec.label, "repo_id": spec.repo_id, "kind": spec.kind, "format": spec.format, "status": "skipped_existing", "selected_file": selected_filename, "local_path": str(existing), "seconds": round(time.time() - t0, 2)}

    local_dir = root / "generation" / safe_repo_name(spec.repo_id)
    if dry_run:
        return {"label": spec.label, "repo_id": spec.repo_id, "kind": spec.kind, "format": spec.format, "status": "dry_run_would_download", "selected_file": selected_filename, "local_dir": str(local_dir), "seconds": round(time.time() - t0, 2)}

    local_dir.mkdir(parents=True, exist_ok=True)
    path = hf_hub_download(
        repo_id=spec.repo_id,
        filename=selected_filename,
        repo_type="model",
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
        token=token,
        resume_download=True,
    )
    return {"label": spec.label, "repo_id": spec.repo_id, "kind": spec.kind, "format": spec.format, "status": "downloaded", "selected_file": selected_filename, "local_path": str(path), "seconds": round(time.time() - t0, 2)}


def download_snapshot_model(spec: ModelSpec, root: Path, *, token: Optional[str], dry_run: bool, force: bool) -> dict:
    t0 = time.time()
    existing = None if force else has_existing_snapshot(root, spec)
    if existing:
        return {"label": spec.label, "repo_id": spec.repo_id, "kind": spec.kind, "format": spec.format, "status": "skipped_existing", "local_path": str(existing), "seconds": round(time.time() - t0, 2)}

    sub = "embeddings" if spec.kind == "embedding" else "rerankers"
    local_dir = root / sub / safe_repo_name(spec.repo_id)
    if dry_run:
        return {"label": spec.label, "repo_id": spec.repo_id, "kind": spec.kind, "format": spec.format, "status": "dry_run_would_download", "local_dir": str(local_dir), "seconds": round(time.time() - t0, 2)}

    local_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_download(
        repo_id=spec.repo_id,
        repo_type="model",
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
        token=token,
        resume_download=True,
        allow_patterns=SNAPSHOT_ALLOW_PATTERNS,
        ignore_patterns=SNAPSHOT_IGNORE_PATTERNS,
    )
    return {"label": spec.label, "repo_id": spec.repo_id, "kind": spec.kind, "format": spec.format, "status": "downloaded", "local_path": str(path), "seconds": round(time.time() - t0, 2)}


def select_models(mode: str) -> list[ModelSpec]:
    enabled = [m for m in MODELS if m.enabled]
    if mode == "all":
        return enabled
    if mode == "generation":
        return [m for m in enabled if m.kind == "generation"]
    if mode == "small-generation":
        return [m for m in enabled if m.kind == "generation" and m.tier == "small"]
    if mode == "medium-generation":
        return [m for m in enabled if m.kind == "generation" and m.tier in {"small", "medium"}]
    if mode == "large-generation":
        return [m for m in enabled if m.kind == "generation" and m.tier == "large"]
    if mode == "retrieval":
        return [m for m in enabled if m.kind in {"embedding", "reranker"}]
    if mode == "embeddings":
        return [m for m in enabled if m.kind == "embedding"]
    if mode == "rerankers":
        return [m for m in enabled if m.kind == "reranker"]
    raise ValueError(f"Unknown --only mode: {mode}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download VTD local models from Hugging Face.")
    parser.add_argument("--models-root", type=Path, default=Path("models"), help="Root folder to store models. Default: ./models")
    parser.add_argument("--only", choices=["all", "generation", "small-generation", "medium-generation", "large-generation", "retrieval", "embeddings", "rerankers"], default="all", help="Which model group to download.")
    parser.add_argument("--quant", default=os.environ.get("GGUF_QUANT", "Q4_K_M"), help="Preferred GGUF quantization. Default: Q4_K_M. Fallbacks are automatic.")
    parser.add_argument("--force", action="store_true", help="Download again even if a matching local model is found.")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be downloaded.")
    parser.add_argument("--manifest", type=Path, default=None, help="Optional manifest output JSON path.")
    args = parser.parse_args()

    root = args.models_root.resolve()
    root.mkdir(parents=True, exist_ok=True)

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    quant_preferences = tuple(dict.fromkeys([args.quant, *DEFAULT_QUANT_PREFERENCES]))
    selected = select_models(args.only)
    manifest: list[dict] = []

    print("=" * 80)
    print("VTD Hugging Face Model Downloader")
    print(f"models_root: {root}")
    print(f"mode:        {args.only}")
    print(f"dry_run:     {args.dry_run}")
    print(f"force:       {args.force}")
    print(f"hf_token:    {'set' if token else 'not set'}")
    print(f"models:      {len(selected)}")
    print("=" * 80)

    for i, spec in enumerate(selected, start=1):
        print(f"\n[{i}/{len(selected)}] {spec.label}")
        print(f"repo: {spec.repo_id}")
        print(f"kind: {spec.kind} | format: {spec.format} | tier: {spec.tier}")

        try:
            if spec.format == "gguf":
                result = download_gguf(spec, root, quant_preferences=quant_preferences, token=token, dry_run=args.dry_run, force=args.force)
            else:
                result = download_snapshot_model(spec, root, token=token, dry_run=args.dry_run, force=args.force)

            print(f"status: {result['status']}")
            if "selected_file" in result:
                print(f"file:   {result['selected_file']}")
            if "local_path" in result:
                print(f"path:   {result['local_path']}")
            if "local_dir" in result:
                print(f"dir:    {result['local_dir']}")

        except GatedRepoError as exc:
            result = {"label": spec.label, "repo_id": spec.repo_id, "kind": spec.kind, "format": spec.format, "status": "failed_gated_repo", "error": str(exc)}
            print("status: failed_gated_repo")
            print("hint: accept the model license on Hugging Face and set $env:HF_TOKEN='hf_...'")
        except RepositoryNotFoundError as exc:
            result = {"label": spec.label, "repo_id": spec.repo_id, "kind": spec.kind, "format": spec.format, "status": "failed_repo_not_found_or_private", "error": str(exc)}
            print("status: failed_repo_not_found_or_private")
        except HfHubHTTPError as exc:
            result = {"label": spec.label, "repo_id": spec.repo_id, "kind": spec.kind, "format": spec.format, "status": "failed_hf_http_error", "error": str(exc)}
            print("status: failed_hf_http_error")
            print(str(exc)[:1000])
        except Exception as exc:
            result = {"label": spec.label, "repo_id": spec.repo_id, "kind": spec.kind, "format": spec.format, "status": "failed", "error": repr(exc)}
            print("status: failed")
            print(repr(exc))

        manifest.append(result)

    out_path = args.manifest or (root / "download_manifest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 80)
    print(f"Manifest written to: {out_path}")
    print("Summary:")
    counts: dict[str, int] = {}
    for item in manifest:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")
    print("=" * 80)

    failed = [x for x in manifest if str(x["status"]).startswith("failed")]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
