from __future__ import annotations

import importlib.util
import json
import platform
import sqlite3
import sys
from pathlib import Path

from _bootstrap_path import PROJECT_ROOT


def check_import(module: str) -> dict:
    spec = importlib.util.find_spec(module)
    return {"module": module, "available": spec is not None}


def main() -> int:
    data_dir = PROJECT_ROOT / "data"
    db_path = data_dir / "db" / "vtd_health_research_v1.db"
    models_dir = PROJECT_ROOT / "models"

    checks: list[dict] = []
    checks.append({"check": "project_root", "ok": PROJECT_ROOT.exists(), "value": str(PROJECT_ROOT)})
    checks.append({"check": "python_version", "ok": sys.version_info >= (3, 12), "value": sys.version})
    checks.append({"check": "platform", "ok": True, "value": platform.platform()})
    checks.append({"check": "data_dir_exists", "ok": data_dir.exists(), "value": str(data_dir)})
    checks.append({"check": "db_exists", "ok": db_path.exists(), "value": str(db_path)})
    checks.append({"check": "models_dir_exists", "ok": models_dir.exists(), "value": str(models_dir)})

    ggufs = sorted(p.name for p in models_dir.glob("*.gguf")) if models_dir.exists() else []
    checks.append({"check": "gguf_models_found", "ok": len(ggufs) > 0, "count": len(ggufs), "models": ggufs[:20]})

    if db_path.exists():
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            conn.close()
            checks.append({"check": "db_opens_readonly", "ok": True, "table_count": len(tables)})
        except Exception as exc:
            checks.append({"check": "db_opens_readonly", "ok": False, "error": repr(exc)})

    for module in [
        "pydantic",
        "sqlglot",
        "llama_cpp",
        "chromadb",
        "sentence_transformers",
        "rank_bm25",
        "rapidfuzz",
        "networkx",
        "src.config.paths",
        "src.core.enums",
        "src.core.types",
    ]:
        info = check_import(module)
        checks.append({"check": f"import:{module}", "ok": info["available"]})

    ok = all(c.get("ok") for c in checks if c["check"] not in {"gguf_models_found"})
    report_path = PROJECT_ROOT / "data" / "audit" / "smoke_test_environment.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ok": ok, "report": str(report_path), "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
