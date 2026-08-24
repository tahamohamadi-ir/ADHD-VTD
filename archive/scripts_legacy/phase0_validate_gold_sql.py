from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _bootstrap_path import PROJECT_ROOT

DB_PATH = PROJECT_ROOT / "data" / "db" / "vtd_health_research_v1.db"
CASES_PATH = PROJECT_ROOT / "data" / "questions" / "audit" / "phase0_50q_audit_cases.json"
RESULTS_PATH = PROJECT_ROOT / "data" / "questions" / "audit" / "phase0_50q_audit_results.jsonl"
FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|MERGE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|EXEC|CALL)\b", re.I)


def is_safe_select(sql: str) -> tuple[bool, str | None]:
    stripped = sql.strip().rstrip(";").strip()
    if ";" in stripped:
        return False, "MULTI_STATEMENT"
    if FORBIDDEN.search(stripped):
        return False, "FORBIDDEN_KEYWORD"
    if not re.match(r"^\s*(WITH\b.+?\bSELECT\b|SELECT\b)", stripped, flags=re.I | re.S):
        return False, "NOT_SELECT"
    return True, None


def result_hash(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    payload = json.dumps({"columns": columns, "rows": rows}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def execute(conn: sqlite3.Connection, sql: str) -> dict:
    start = time.perf_counter()
    cur = conn.execute(sql)
    columns = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchall()
    latency_ms = int((time.perf_counter() - start) * 1000)
    return {
        "columns": columns,
        "row_count": len(rows),
        "column_count": len(columns),
        "sample_rows": [list(r) for r in rows[:5]],
        "result_hash": result_hash(columns, rows),
        "latency_ms": latency_ms,
    }


def main() -> int:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10)
    rows = []
    try:
        for c in cases:
            sql = c["gold_sql"]
            safe, err = is_safe_select(sql)
            row = {
                "audit_id": c["audit_id"],
                "source_id": c["source_id"],
                "executed_at_utc": datetime.now(timezone.utc).isoformat(),
                "gold_sql_executed": False,
                "execution_success": False,
                "safety_ok": safe,
                "safety_error": err,
                "error": None,
            }
            if not safe:
                row["error"] = err
                rows.append(row)
                continue
            try:
                out = execute(conn, sql)
                row.update(out)
                row["gold_sql_executed"] = True
                row["execution_success"] = True
            except Exception as exc:
                row["error"] = repr(exc)
            rows.append(row)
    finally:
        conn.close()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    ok = sum(1 for r in rows if r.get("execution_success"))
    print(f"✅ Wrote {RESULTS_PATH}")
    print(f"Executed successfully: {ok}/{len(rows)}")
    return 0 if ok == len(rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
