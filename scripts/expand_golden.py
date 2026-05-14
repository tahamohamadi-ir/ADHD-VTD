"""Expand golden examples, few shot bank, and indexed examples.

Samples 50 high-quality records from the 400 merged dataset and formats
them into the three targeted formats.
"""
from __future__ import annotations
import json, random, sys, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.jsonl import write_jsonl
from scripts.check_schema_column_references import extract_table_refs, extract_column_refs

TRAIN_DATASET = Path("data/questions/train/train.json")
GOLDEN = Path("data/golden_sql/golden_examples.jsonl")
FEW_SHOT = Path("data/golden_sql/few_shot_bank.jsonl")
INDEXED = Path("data/rag/indexed_examples.jsonl")

def get_intent(sql: str) -> str:
    s = sql.upper()
    if "GROUP BY" in s: return "grouping_query"
    if "AVG(" in s or "MAX(" in s or "MIN(" in s or "SUM(" in s: return "aggregation_query"
    if "COUNT(" in s: return "count_query"
    return "general_sql_query"

def get_skeleton(sql: str) -> str:
    s = sql.upper()
    if "JOIN" in s and "GROUP BY" in s: return "SELECT ... FROM t1 JOIN t2 ON ... GROUP BY ..."
    if "GROUP BY" in s: return "SELECT ... FROM table GROUP BY ..."
    if "WHERE" in s: return "SELECT ... FROM table WHERE ..."
    return "SELECT ... FROM table"

def main():
    examples = json.loads(TRAIN_DATASET.read_text(encoding="utf-8"))
    random.seed(42)
    # Pick 50 diverse examples
    sampled = random.sample(examples, 50)
    
    gold_data = []
    few_shot_data = []
    indexed_data = []
    
    for ex in sampled:
        sql = ex.get("sql", "")
        tables = list(extract_table_refs(sql))
        cols = list(extract_column_refs(sql, set(tables)))
        clean_cols = [c.split(".")[-1] for c in cols]
        
        intent = get_intent(sql)
        rhash = hashlib.sha256(sql.encode()).hexdigest()[:16]
        
        # Golden
        gold_data.append({
            "id": ex.get("id"),
            "question_fa": ex.get("question_fa"),
            "sql": sql,
            "intent": intent,
            "difficulty": ex.get("difficulty", "easy"),
            "tables": tables,
            "columns": clean_cols,
            "result_hash": rhash
        })
        
        # Few shot
        few_shot_data.append({
            "id": f"fs_{ex.get('id')}",
            "question_fa": ex.get("question_fa"),
            "sql": sql,
            "intent": intent,
            "skeleton": get_skeleton(sql),
            "tables": tables,
            "difficulty": ex.get("difficulty", "easy")
        })
        
        # Indexed
        indexed_data.append({
            "id": f"idx_{ex.get('id')}",
            "question_fa": ex.get("question_fa"),
            "sql": sql,
            "text_for_embedding": f"{ex.get('question_fa')} {intent} {' '.join(tables)} {' '.join(clean_cols)}",
            "intent": intent,
            "tables": tables,
            "columns": clean_cols,
            "metadata": {
                "difficulty": ex.get("difficulty", "easy"),
                "category": ex.get("category", "unknown")
            }
        })

    # write
    write_jsonl(GOLDEN, gold_data)
    write_jsonl(FEW_SHOT, few_shot_data[:30])  # keep 30 for few shot
    write_jsonl(INDEXED, indexed_data)
    
    print(f"✅ Generated {len(gold_data)} golden examples")
    print(f"✅ Generated {len(few_shot_data[:30])} few-shot examples")
    print(f"✅ Generated {len(indexed_data)} indexed examples")

if __name__ == "__main__":
    main()
