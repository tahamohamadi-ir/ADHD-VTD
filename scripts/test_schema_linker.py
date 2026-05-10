from __future__ import annotations

from _bootstrap_path import PROJECT_ROOT

from src.schema.schema_linker import SchemaLinker

queries = [
    "میانگین نمره افسردگی دانشجویان زن چقدر است؟",
    "چند دانشجو اضطراب دارند؟",
    "میانگین معدل دانشجویان مرد را بده",
    "افراد با خواب کمتر از ۶ ساعت را نشان بده",
]

print(f"PROJECT_ROOT = {PROJECT_ROOT}")

linker = SchemaLinker()

for q in queries:
    print("=" * 80)
    print(q)
    result = linker.link(q)
    if hasattr(result, "model_dump"):
        print(result.model_dump())
    else:
        print(result)
