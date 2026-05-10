from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import quote

try:
    from src.config.paths import DB_PATH
except Exception:  # pragma: no cover
    DB_PATH = Path("data/db/vtd_health_research_v1.db")


def readonly_uri(db_path: str | Path) -> str:
    path = Path(db_path).resolve()
    # SQLite URI on Windows needs forward slashes.
    uri_path = quote(str(path).replace("\\", "/"), safe="/:" )
    return f"file:{uri_path}?mode=ro"


def get_readonly_connection(db_path: str | Path | None = None, timeout: float = 10.0) -> sqlite3.Connection:
    path = Path(db_path or DB_PATH)
    if not path.exists():
        raise FileNotFoundError(f"SQLite database not found: {path}")
    conn = sqlite3.connect(readonly_uri(path), uri=True, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
