from __future__ import annotations

import re

import pytest

import src.evaluation.paraphrase_holdout as paraphrase_holdout
from src.evaluation.dataset_loader import normalize_case
from src.evaluation.paraphrase_holdout import (
    METHOD,
    PARAPHRASE_RULES,
    build_holdout_dataset,
    build_metadata_block,
    paraphrase_question,
    select_holdout_cases,
)

SAMPLE_QUESTIONS = [
    "میانگین نمره امتحان دانشجویان بر اساس کیفیت اینترنت چقدر است؟",
    "توزیع تشخیص افسردگی در نظرسنجی دانشگاهی را نشان بده.",
    "میانگین سن در دیتاست دانشجویان افسردگی چقدر است؟",
    "تعداد کل رکوردهای دیتاست دانشجویان افسردگی چقدر است؟",
    "جنسیت\u200cها تو دیتاست افسردگی دانشجوها چه تعدادی دارن؟",
    "بازه سال\u200cهای داده جهانی رو بهم بده.",
    "از survey محل کار چندتا پاسخ داریم؟",
    "میانگین افسردگی و اضطراب بر اساس سطح ریسک سلامت روان عمومی چقدر است؟",
    "رابطه استفاده از شبکه اجتماعی و نمره امتحان را دسته\u200cبندی کن.",
    "وضعیت benefits سلامت روان تو شرکت\u200cها چطوریه؟",
    "میانگین شیوع جهانی bipolar به تفکیک سال چیست؟",
    "شهرهای outlier از نظر نرخ افسردگی رو با z-score بده.",
    "ریسک\u200cها رو برای کسانی بده که استرس بالاتر از میانگین و خواب پایین\u200cتر از میانگین دارن.",
    "درمان\u200cجویی محیط کار را به تفکیک شرکت فناوری و وضعیت دورکاری نشان بده.",
    "نرخ افسردگی بر اساس عادت غذایی دانشجویان چقدر است؟",
    "تعداد رکوردهای شیوع جهانی برای Germany چقدر است؟",
    "میانگین شیوع جهانی افسردگی چقدره؟",
    "ریسک سلامت روان با خواب، استرس و بهره\u200cوری چه وضعی داره؟",
    "شهرها رو با حداقل ۷۰۰ نمونه بر اساس نرخ افسردگی رتبه\u200cبندی کن.",
    "برای ایران تغییر سال\u200cبه\u200cسال افسردگی رو حساب کن.",
    "در آخرین سال موجود، میانگین شیوع اختلال\u200cها فقط برای کشورها چقدر است؟",
    "بیشترین نرخ افسردگی مربوط به کدام گروه سنی است؟",
    "کمترین معدل دانشجویان چقدر است؟",
    "میانگین نمره افسردگی دانشجوهای زن چقدره?",
    "چند درصد دانشجوها افسرده هستند?",
    "بهترین معدل بین دانشجوها کیه?",
    "از هر اختلال تو جدول long چند رکورد داریم؟",
    "روند شیوع افسردگی، اضطراب و اختلال دوقطبی در Brazil را در طول زمان مقایسه کن.",
]


def _make_case(cid: str, difficulty: str, question: str = "تعداد کل رکوردها چقدر است؟") -> dict:
    return {
        "id": cid,
        "difficulty": difficulty,
        "category": "count",
        "pattern": "simple_count",
        "question_fa": question,
        "sql": "SELECT COUNT(*) AS total FROM t;",
        "recommended_visual": "kpi",
        "safe_sql": True,
        "dialect": "sqlite",
    }


def _stratified_pool() -> list[dict]:
    pool = [_make_case(f"E{i:03d}", "easy") for i in range(50)]
    pool += [_make_case(f"M{i:03d}", "medium") for i in range(30)]
    pool += [_make_case(f"H{i:03d}", "hard") for i in range(20)]
    return pool


def test_rule_pack_has_at_least_25_rules():
    assert len(PARAPHRASE_RULES) >= 25


def test_most_sample_questions_actually_change():
    changed = 0
    for question in SAMPLE_QUESTIONS:
        try:
            paraphrased = paraphrase_question(question, 0)
        except ValueError:
            continue
        if paraphrased != question:
            changed += 1
    assert changed / len(SAMPLE_QUESTIONS) >= 0.9


def test_paraphrase_question_is_deterministic(sample_persian_questions):
    questions = SAMPLE_QUESTIONS + sample_persian_questions
    for index, question in enumerate(questions):
        assert paraphrase_question(question, index) == paraphrase_question(question, index)


def test_paraphrase_question_varies_by_variant_index():
    question = SAMPLE_QUESTIONS[0]
    outputs = {paraphrase_question(question, idx) for idx in range(10)}
    assert len(outputs) >= 2

    colloquial = "میانگین نمره افسردگی دانشجوهای زن چقدره؟"
    targeted = {paraphrase_question(colloquial, idx) for idx in (17, 19, 27)}
    assert len(targeted) >= 3


def test_paraphrase_question_raises_after_exhausting_candidates(monkeypatch):
    monkeypatch.setattr(
        paraphrase_holdout,
        "PARAPHRASE_RULES",
        [(re.compile(r"\bZZZ\b"), "YYY")],
    )
    with pytest.raises(ValueError):
        paraphrase_question("متن بدون هیچ الگوی شناخته‌شده", 0)


def test_select_holdout_is_deterministic_for_same_seed():
    pool = _stratified_pool()
    first = select_holdout_cases(pool, 12, seed=187)
    second = select_holdout_cases(pool, 12, seed=187)
    assert first == second


def test_select_holdout_respects_proportions_within_tolerance():
    pool = _stratified_pool()
    selected = select_holdout_cases(pool, 10, seed=5)
    counts: dict[str, int] = {}
    for case in selected:
        counts[case["difficulty"]] = counts.get(case["difficulty"], 0) + 1
    assert len(selected) == 10
    assert abs(counts.get("easy", 0) - 5) <= 1
    assert abs(counts.get("medium", 0) - 3) <= 1
    assert abs(counts.get("hard", 0) - 2) <= 1


def test_select_holdout_has_no_duplicate_ids_and_handles_duplicates_in_input():
    pool = _stratified_pool()
    pool.append(dict(_make_case("E001", "easy")))
    selected = select_holdout_cases(pool, 15, seed=99)
    ids = [case["id"] for case in selected]
    assert len(ids) == len(set(ids)) == 15


def test_build_holdout_manifest_fields_present():
    pool = _stratified_pool()
    holdout, manifest = build_holdout_dataset(pool, 8, seed=187)
    required = {
        "generated_at_utc",
        "seed",
        "method",
        "source_count",
        "held_out_count",
        "difficulty_counts",
    }
    assert required <= set(manifest)
    assert manifest["method"] == METHOD == "rule_based_paraphrase_v1"
    assert manifest["seed"] == 187
    assert manifest["source_count"] == len(pool)
    assert manifest["held_out_count"] == len(holdout) == 8


def test_build_holdout_cases_keep_schema_and_change_question():
    pool = _stratified_pool()
    source_by_id = {case["id"]: case for case in pool}
    holdout, _ = build_holdout_dataset(pool, 8, seed=187)
    for new_case in holdout:
        source = source_by_id[new_case["original_case_id"]]
        assert set(new_case) == set(source) | {"original_case_id"}
        assert new_case["id"].endswith("-P")
        assert new_case["id"].startswith(source["id"])
        assert new_case["question_fa"] != source["question_fa"]
        normalized = normalize_case(new_case)
        assert normalized["id"] == new_case["id"]
        assert normalized["question"] == new_case["question_fa"]
        assert normalized["gold_sql"]
        assert normalized["should_generate_sql"] is True


def test_build_holdout_caps_n_to_available_cases():
    pool = _stratified_pool()[:10]
    holdout, manifest = build_holdout_dataset(pool, 99, seed=1)
    assert len(holdout) == manifest["held_out_count"] == 10


def test_metadata_block_shape():
    block = build_metadata_block(400, 48, 187)
    assert block == {
        "method": METHOD,
        "seed": 187,
        "source_case_count": 400,
        "held_out_count": 48,
    }
