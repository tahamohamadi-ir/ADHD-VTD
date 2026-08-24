import json
from pathlib import Path

f400 = Path("data/questions/full/vtd_question_sql_400_merged_validated.json")
d = json.loads(f400.read_text(encoding="utf-8"))
ex = [x for x in d['examples'] if 'vw_' in x['sql']]

with open('scratch_8_queries.txt', 'w', encoding='utf-8') as f:
    for x in ex:
        f.write(f"ID: {x['id']}\n")
        f.write(f"Q: {x['question_fa']}\n")
        f.write(f"SQL: {x['sql']}\n\n")
