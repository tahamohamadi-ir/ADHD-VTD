import json
from pathlib import Path

bad_ids = {"VTD-154", "VTD-155", "VTD-206", "VTD-207", "VTD-251", "VTD-352", "VTD-382", "VTD-383"}
f400 = Path("data/questions/full/vtd_question_sql_400_merged_validated.json")

def fix():
    d = json.loads(f400.read_text(encoding="utf-8"))
    orig_len = len(d["examples"])
    d["examples"] = [x for x in d["examples"] if x["id"] not in bad_ids]
    new_len = len(d["examples"])
    d["total_examples"] = new_len
    f400.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Removed {orig_len - new_len} hallucinated examples. Remaining: {new_len}")

if __name__ == "__main__":
    fix()
