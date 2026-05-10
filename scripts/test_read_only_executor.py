from __future__ import annotations

from _bootstrap_path import PROJECT_ROOT
from src.db.read_only_executor import ReadOnlyExecutor


def main() -> int:
    executor = ReadOnlyExecutor(max_rows=20)
    for sql in [
        "SELECT COUNT(*) AS n FROM student_depression",
        "SELECT gender, COUNT(*) AS n FROM student_depression GROUP BY gender ORDER BY n DESC",
        "DELETE FROM student_depression",
    ]:
        print("=" * 80)
        print(sql)
        result = executor.execute_readonly(sql)
        print(result)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
