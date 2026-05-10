from __future__ import annotations

from _bootstrap_path import PROJECT_ROOT
from src.schema.value_linker import ValueLinker


def main() -> int:
    linker = ValueLinker()
    tests = [
        ("دانشجویان زن", ["student_depression.gender"]),
        ("دانشجویان مرد", ["student_depression.gender"]),
        ("افسرده ها", ["student_depression.depression_flag"]),
        ("ریسک mental health high", ["mental_health_general.mental_health_risk"]),
        ("شیوع اضطراب در کشورها", ["country_prevalence_long.disorder"]),
    ]
    for text, cols in tests:
        print("=" * 80)
        print(text, cols)
        for link in linker.resolve_as_dicts(text, cols):
            print(link)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
