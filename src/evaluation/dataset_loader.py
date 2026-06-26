from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

from src.core.dataset_types import BehavioralExample, DatasetPackageSummary, PositiveExample

try:
    from src.config.paths import (
        PROJECT_ROOT,
        PHASE0_50Q_CASES_PATH,
        PHASE0_50Q_RESULTS_PATH,
        QUESTION_AUDIT_DIR,
        QUESTIONS_DIR,
    )
except Exception:  # pragma: no cover - fallback for standalone script execution
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    QUESTIONS_DIR = PROJECT_ROOT / "data" / "questions"
    QUESTION_AUDIT_DIR = QUESTIONS_DIR / "audit"
    PHASE0_50Q_CASES_PATH = QUESTION_AUDIT_DIR / "phase0_50q_audit_cases.json"
    PHASE0_50Q_RESULTS_PATH = QUESTION_AUDIT_DIR / "phase0_50q_audit_results.jsonl"


@dataclass(slots=True)
class LoadedDataset:
    path: Path
    kind: str
    cases: list[dict[str, Any]]
    metadata: dict[str, Any]

    @property
    def total(self) -> int:
        return len(self.cases)


def read_json(path: str | Path) -> Any:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {p}:{line_no}: {exc}") from exc
    return rows


def to_jsonable(value: Any) -> Any:
    """Convert project runtime objects into plain JSON-compatible values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return to_jsonable(value.model_dump())
    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))
    return str(value)


def write_json(path: str | Path, data: Any, *, indent: int = 2) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(to_jsonable(data), f, ensure_ascii=False, indent=indent)
    return p


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(to_jsonable(row), ensure_ascii=False, sort_keys=True) + "\n")
    return p


def _split_metadata_and_cases(raw: Any, *, preferred_keys: tuple[str, ...]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if isinstance(raw, list):
        return {}, raw
    if not isinstance(raw, dict):
        raise TypeError(f"Expected dataset JSON to be object or list, got {type(raw)!r}")

    cases: list[dict[str, Any]] | None = None
    matched_key = None
    for key in preferred_keys:
        value = raw.get(key)
        if isinstance(value, list):
            cases = value
            matched_key = key
            break

    if cases is None:
        # Common dataset formats in this project.
        for key in ("cases", "examples", "positive_examples", "behavioral_examples", "items"):
            value = raw.get(key)
            if isinstance(value, list):
                cases = value
                matched_key = key
                break

    if cases is None:
        raise ValueError("Could not find cases list in dataset JSON.")

    metadata = {k: v for k, v in raw.items() if k != matched_key}
    metadata["case_key"] = matched_key
    return metadata, cases


def normalize_case(case: dict[str, Any], *, source_kind: str = "unknown") -> dict[str, Any]:
    """Normalize different project dataset shapes into a common evaluation case dict.

    This does not mutate semantic content. It only adds canonical aliases used by runners.
    """
    c = dict(case)
    c.setdefault("source_kind", source_kind)
    c.setdefault("id", c.get("audit_id") or c.get("source_id") or c.get("case_id"))
    c.setdefault("question", c.get("question_fa") or c.get("user_utterance_fa") or c.get("question_en") or "")
    c.setdefault("gold_sql", c.get("gold_sql") or c.get("sql") or c.get("expected_sql"))
    c.setdefault("should_generate_sql", bool(c.get("gold_sql")))
    c.setdefault("expected_action", c.get("expected_action") or ("generate_sql" if c.get("should_generate_sql") else "ask_clarification"))
    c.setdefault("difficulty", c.get("difficulty", "unknown"))
    c.setdefault("category", c.get("category") or c.get("evaluation_type") or c.get("pattern") or "unknown")
    return c


def load_dataset(path: str | Path, *, kind: str = "auto") -> LoadedDataset:
    p = Path(path)
    raw = read_json(p)
    metadata, cases = _split_metadata_and_cases(
        raw,
        preferred_keys=("cases", "examples", "positive_examples", "behavioral_evaluation_examples"),
    )
    normalized = [normalize_case(c, source_kind=kind) for c in cases]
    if kind == "auto":
        kind = str(metadata.get("artifact") or metadata.get("project") or p.stem)
    return LoadedDataset(path=p, kind=kind, cases=normalized, metadata=metadata)


def load_phase0_50q_cases(path: str | Path | None = None) -> LoadedDataset:
    return load_dataset(path or PHASE0_50Q_CASES_PATH, kind="phase0_50q")


def load_phase0_results(path: str | Path | None = None) -> list[dict[str, Any]]:
    return read_jsonl(path or PHASE0_50Q_RESULTS_PATH)


def load_special_eval(path: str | Path | None = None) -> LoadedDataset:
    p = Path(path) if path else QUESTIONS_DIR / "special" / "vtd_evaluation_special_100.json"
    return load_dataset(p, kind="behavioral_special")


def load_positive_400(path: str | Path | None = None) -> LoadedDataset:
    p = Path(path) if path else QUESTIONS_DIR / "full" / "vtd_question_sql_400_merged_validated.json"
    return load_dataset(p, kind="positive_400")


def positive_example_from_case(case: dict[str, Any]) -> PositiveExample:
    c = normalize_case(case)
    sql = c.get("gold_sql") or c.get("sql")
    if not sql:
        raise ValueError(f"Case {c.get('id') or '<missing-id>'} is not SQL-positive: missing gold SQL.")
    return PositiveExample(
        id=str(c.get("id") or ""),
        question_fa=str(c.get("question_fa") or c.get("question") or ""),
        difficulty=str(c.get("difficulty") or "unknown"),
        category=str(c.get("category") or "unknown"),
        sql=str(sql),
        expected_tables=list(c.get("expected_tables") or []),
        expected_columns=list(c.get("expected_columns") or []),
        expected_values=list(c.get("expected_values") or []),
        expected_join_paths=list(c.get("expected_join_paths") or []),
        recommended_visual=c.get("recommended_visual"),
        safe_sql=bool(c.get("safe_sql", True)),
        dialect=str(c.get("dialect") or "sqlite"),
        metadata={k: v for k, v in c.items() if k not in {"sql", "gold_sql", "question", "question_fa"}},
    )


def behavioral_example_from_case(case: dict[str, Any]) -> BehavioralExample:
    c = normalize_case(case)
    utterance = c.get("user_utterance_fa") or c.get("question_fa") or c.get("question")
    if not utterance:
        raise ValueError(f"Behavioral case {c.get('id') or '<missing-id>'} is missing user utterance.")
    return BehavioralExample(
        id=str(c.get("id") or ""),
        evaluation_type=str(c.get("evaluation_type") or c.get("category") or "unknown"),
        user_utterance_fa=str(utterance),
        should_generate_sql=bool(c.get("should_generate_sql")),
        expected_action=str(c.get("expected_action") or "ask_clarification"),
        expected_sql=c.get("expected_sql") or c.get("gold_sql"),
        metadata={k: v for k, v in c.items() if k not in {"user_utterance_fa", "question", "question_fa"}},
    )


def load_positive_examples(path: str | Path) -> list[PositiveExample]:
    dataset = load_dataset(path, kind="positive")
    return [positive_example_from_case(case) for case in dataset.cases]


def load_behavioral_examples(path: str | Path) -> list[BehavioralExample]:
    dataset = load_dataset(path, kind="behavioral")
    return [behavioral_example_from_case(case) for case in dataset.cases]


def summarize_cases(cases: Iterable[dict[str, Any]]) -> dict[str, Any]:
    cases_list = list(cases)
    by_difficulty: dict[str, int] = {}
    by_category: dict[str, int] = {}
    sql_positive = 0
    for c in cases_list:
        d = str(c.get("difficulty", "unknown"))
        cat = str(c.get("category") or c.get("evaluation_type") or "unknown")
        by_difficulty[d] = by_difficulty.get(d, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1
        if c.get("should_generate_sql") or c.get("gold_sql"):
            sql_positive += 1
    return {
        "total": len(cases_list),
        "sql_positive": sql_positive,
        "non_sql_or_behavioral": len(cases_list) - sql_positive,
        "by_difficulty": dict(sorted(by_difficulty.items())),
        "by_category": dict(sorted(by_category.items())),
    }


def summarize_dataset_package(cases: Iterable[dict[str, Any]]) -> DatasetPackageSummary:
    summary = summarize_cases(cases)
    return DatasetPackageSummary(
        total=int(summary["total"]),
        sql_positive=int(summary["sql_positive"]),
        behavioral=int(summary["non_sql_or_behavioral"]),
        by_difficulty=dict(summary["by_difficulty"]),
        by_category=dict(summary["by_category"]),
    )


def select_samples_per_level(
    cases: Iterable[dict[str, Any]],
    samples_per_level: int,
    *,
    difficulty_key: str = "difficulty",
) -> list[dict[str, Any]]:
    """Select up to N cases from each difficulty level in deterministic order."""
    if samples_per_level <= 0:
        raise ValueError("samples_per_level must be a positive integer.")

    grouped: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        difficulty = str(case.get(difficulty_key) or "unknown")
        grouped.setdefault(difficulty, []).append(case)

    selected: list[dict[str, Any]] = []
    for difficulty in sorted(grouped):
        selected.extend(grouped[difficulty][:samples_per_level])
    return selected
