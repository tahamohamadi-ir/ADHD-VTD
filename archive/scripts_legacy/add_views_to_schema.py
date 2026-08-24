import json
import sqlite3
from pathlib import Path

DB_PATH = Path("data/db/vtd_health_research_v1.db")
FROZEN_PATH = Path("data/schema/schema_snapshot.json")
GEN_PATH = Path("data/schema/schema_snapshot.generated.json")

def get_view_schema(conn, view_name):
    # Get columns
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({view_name})")
    cols = cursor.fetchall()
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
    row_count = cursor.fetchone()[0]
    
    columns = []
    for c in cols:
        columns.append({
            "name": c[1],
            "type": c[2] or "ANY",
            "primary_key": bool(c[5]),
            "nullable": not bool(c[3]),
            "description": f"Column {c[1]} from view {view_name}"
        })
        
    return {
        "name": view_name,
        "description": f"View {view_name}",
        "row_count": row_count,
        "columns": columns
    }

def update_snapshot(path):
    if not path.exists(): return
    d = json.loads(path.read_text(encoding="utf-8"))
    tables = d.get("tables", [])
    
    existing_tables = {t["name"] for t in tables}
    
    conn = sqlite3.connect(str(DB_PATH))
    views = ["vw_country_prevalence_pivot", "vw_unified_individual_mental_health", "vw_student_dashboard"]
    
    added = 0
    for v in views:
        if v not in existing_tables:
            v_schema = get_view_schema(conn, v)
            tables.append(v_schema)
            added += 1
            print(f"Added view {v} to {path.name}")
            
    if added:
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    update_snapshot(FROZEN_PATH)
    update_snapshot(GEN_PATH)
