from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from difflib import SequenceMatcher

try:
    from src.config.paths import VALUE_DICTIONARY_PATH
    from src.nlu.persian_normalizer import PersianNormalizer
except Exception:  # pragma: no cover
    VALUE_DICTIONARY_PATH = Path("data/schema/value_dictionary.generated.json")
    from persian_normalizer import PersianNormalizer

@dataclass(frozen=True)
class ValueLink:
    column: str
    user_value: str
    resolved_value: object
    confidence: float
    source: str
    reason: str | None = None

class ValueLinker:
    """Resolve natural-language values to real DB values.

    Examples:
    زن -> Female
    مرد -> Male
    افسرده -> depression_flag = 1
    ندارد -> 0 / No / False depending on column
    ریسک بالا -> High
    """

    MANUAL_ALIASES: dict[str, dict[str, object]] = {
        # gender
        "زن": {"value": "Female", "columns_like": ["gender"]},
        "دختر": {"value": "Female", "columns_like": ["gender"]},
        "female": {"value": "Female", "columns_like": ["gender"]},
        "مرد": {"value": "Male", "columns_like": ["gender"]},
        "پسر": {"value": "Male", "columns_like": ["gender"]},
        "male": {"value": "Male", "columns_like": ["gender"]},
        # binary yes/no
        "بله": {"value": 1, "columns_like": ["flag", "history", "treatment", "thoughts", "diagnosis", "attack"]},
        "دارد": {"value": 1, "columns_like": ["flag", "history", "treatment", "thoughts", "diagnosis", "attack"]},
        "دارند": {"value": 1, "columns_like": ["flag", "history", "treatment", "thoughts", "diagnosis", "attack"]},
        "yes": {"value": 1, "columns_like": ["flag", "history", "treatment", "thoughts", "diagnosis", "attack"]},
        "ندارد": {"value": 0, "columns_like": ["flag", "history", "treatment", "thoughts", "diagnosis", "attack"]},
        "ندارند": {"value": 0, "columns_like": ["flag", "history", "treatment", "thoughts", "diagnosis", "attack"]},
        "خیر": {"value": 0, "columns_like": ["flag", "history", "treatment", "thoughts", "diagnosis", "attack"]},
        "no": {"value": 0, "columns_like": ["flag", "history", "treatment", "thoughts", "diagnosis", "attack"]},
        # depression / diagnosis flags
        # Note: PersianNormalizer/ColloquialMapper may normalize "افسرده" and "depressed" to "افسردگی".
        # Therefore both symptom/condition terms and normalized terms must resolve to the binary flag
        # when the candidate column is a flag/diagnosis column.
        "افسرده": {"value": 1, "columns_like": ["depression_flag", "depression_diagnosis"]},
        "افسردگی": {"value": 1, "columns_like": ["depression_flag", "depression_diagnosis"]},
        "depressed": {"value": 1, "columns_like": ["depression_flag", "depression_diagnosis"]},
        "افسردگی دارد": {"value": 1, "columns_like": ["depression_flag", "depression_diagnosis"]},
        "دارای افسردگی": {"value": 1, "columns_like": ["depression_flag", "depression_diagnosis"]},
        "غیرافسرده": {"value": 0, "columns_like": ["depression_flag", "depression_diagnosis"]},
        "غیر افسرده": {"value": 0, "columns_like": ["depression_flag", "depression_diagnosis"]},
        "بدون افسردگی": {"value": 0, "columns_like": ["depression_flag", "depression_diagnosis"]},
        "افسردگی ندارد": {"value": 0, "columns_like": ["depression_flag", "depression_diagnosis"]},
        "افسردگی ندارند": {"value": 0, "columns_like": ["depression_flag", "depression_diagnosis"]},
        # risk levels
        "ریسک بالا": {"value": "High", "columns_like": ["risk"]},
        "پرریسک": {"value": "High", "columns_like": ["risk"]},
        "high": {"value": "High", "columns_like": ["risk"]},
        "ریسک متوسط": {"value": "Medium", "columns_like": ["risk"]},
        "medium": {"value": "Medium", "columns_like": ["risk"]},
        "ریسک پایین": {"value": "Low", "columns_like": ["risk"]},
        "low": {"value": "Low", "columns_like": ["risk"]},
        # disorders
        "افسردگی": {"value": "depression", "columns_like": ["disorder"]},
        "اضطراب": {"value": "anxiety", "columns_like": ["disorder"]},
        "دوقطبی": {"value": "bipolar", "columns_like": ["disorder"]},
        "اسکیزوفرنی": {"value": "schizophrenia", "columns_like": ["disorder"]},
        "اختلال خوردن": {"value": "eating_disorder", "columns_like": ["disorder"]},
    }

    def __init__(self, value_dictionary_path: str | Path | None = None) -> None:
        self.path = Path(value_dictionary_path or VALUE_DICTIONARY_PATH)
        self.normalizer = PersianNormalizer()
        self.dictionary = self._load_dictionary()
        self.column_values = self._flatten_values()

    def _load_dictionary(self) -> dict:
        if not self.path.exists():
            return {"tables": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _flatten_values(self) -> dict[str, list[object]]:
        out: dict[str, list[object]] = {}
        for table, tinfo in self.dictionary.get("tables", {}).items():
            for column, cinfo in tinfo.get("columns", {}).items():
                fq = f"{table}.{column}"
                out[fq] = [v.get("value") for v in cinfo.get("values", [])]
        return out

    def _column_matches_alias(self, column: str, columns_like: list[str]) -> bool:
        col = column.split(".")[-1].lower()
        if "disorder" in {part.lower() for part in columns_like}:
            return col == "disorder"
        return any(part.lower() in col for part in columns_like)

    def _value_exists(self, column: str, value: object) -> bool:
        values = self.column_values.get(column, [])
        if not values:
            return True  # allow manual for unprofiled columns; schema validator will handle column existence
        return value in values or str(value) in {str(v) for v in values}

    def _has_negative_depression_context(self, norm: str) -> bool:
        """Detect phrases that explicitly mean no/non-depressed.

        This prevents returning both 0 and 1 for phrases such as
        "افسردگی ندارد" where the normalized text still contains "افسردگی".
        """
        negative_patterns = [
            "غیرافسرده", "غیر افسرده", "بدون افسردگی", "افسردگی ندارد",
            "افسردگی ندارند", "افسردگی نداره", "افسردگی ندارن", "not depressed",
            "non depressed", "non-depressed", "no depression",
        ]
        return any(p in norm for p in negative_patterns)

    def resolve_for_column(self, text: str, column: str) -> list[ValueLink]:
        norm = self.normalizer.normalize_text(text).lower()
        links: list[ValueLink] = []
        negative_depression = self._has_negative_depression_context(norm)

        for alias, spec in sorted(self.MANUAL_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
            alias_norm = self.normalizer.normalize_text(alias).lower()
            if alias_norm in norm and self._column_matches_alias(column, list(spec["columns_like"])):
                value = spec["value"]
                # If the phrase is explicitly negative for depression, do not also emit the positive
                # normalized alias "افسردگی" for depression_flag/depression_diagnosis.
                if negative_depression and value == 1 and self._column_matches_alias(column, ["depression_flag", "depression_diagnosis"]):
                    continue
                if self._value_exists(column, value):
                    links.append(ValueLink(column, alias, value, 0.96, "manual_alias", f"{alias} -> {value}"))

        # Exact/fuzzy string match against profiled values
        for value in self.column_values.get(column, []):
            if value is None:
                continue
            value_s = str(value).lower()
            if value_s and value_s in norm:
                links.append(ValueLink(column, str(value), value, 0.98, "value_dictionary", "Exact value mention."))
            else:
                for token in re.findall(r"[\w\u0600-\u06FF_-]+", norm):
                    if len(token) >= 4 and SequenceMatcher(None, token.lower(), value_s).ratio() >= 0.88:
                        links.append(ValueLink(column, token, value, 0.82, "value_dictionary_fuzzy", "Fuzzy value match."))

        # Deduplicate by column/resolved_value
        dedup: dict[tuple[str, str], ValueLink] = {}
        for link in sorted(links, key=lambda x: x.confidence, reverse=True):
            dedup.setdefault((link.column, str(link.resolved_value)), link)
        return list(dedup.values())

    def resolve(self, text: str, candidate_columns: list[str] | None = None) -> list[ValueLink]:
        columns = candidate_columns or list(self.column_values.keys())
        links: list[ValueLink] = []
        for column in columns:
            links.extend(self.resolve_for_column(text, column))
        return sorted(links, key=lambda x: x.confidence, reverse=True)

    def resolve_as_dicts(self, text: str, candidate_columns: list[str] | None = None) -> list[dict]:
        return [link.__dict__ for link in self.resolve(text, candidate_columns)]
