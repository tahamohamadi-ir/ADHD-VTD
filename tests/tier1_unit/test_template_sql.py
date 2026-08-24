from __future__ import annotations

import json
from pathlib import Path

from src.db.read_only_executor import ReadOnlyExecutor
from src.generation.output_parser import OutputParser
from src.generation.template_sql import try_generate_template_sql
from src.schema.schema_registry import SchemaRegistry
from src.sql_validation.validation_pipeline import ValidationPipeline


def _sql_for(question: str) -> str:
    response = try_generate_template_sql(question)
    assert response is not None
    parsed = OutputParser.extract_json(response)
    assert parsed
    sql = parsed.get("sql")
    assert isinstance(sql, str)
    assert sql
    result = ValidationPipeline(registry=SchemaRegistry()).validate(sql)
    assert result.ok, result.issues
    return sql


def _dataset_case(case_id: str) -> dict:
    dataset_path = Path("data/questions/full/vtd_question_sql_400_merged_validated.json")
    examples = json.loads(dataset_path.read_text(encoding="utf-8"))["examples"]
    for case in examples:
        if case["id"] == case_id:
            return case
    raise AssertionError(f"Dataset case not found: {case_id}")


def test_sensitive_row_level_templates_abstain():
    for case_id in ("VTD-137", "VTD-199"):
        case = _dataset_case(case_id)
        assert try_generate_template_sql(case["question_fa"]) is None


def test_country_disorder_trend_template():
    sql = _sql_for(
        "\u0631\u0648\u0646\u062f \u0634\u06cc\u0648\u0639 \u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u0627\u06cc\u0631\u0627\u0646 \u062f\u0631 \u0637\u0648\u0644 \u0632\u0645\u0627\u0646 \u0686\u06af\u0648\u0646\u0647 \u0627\u0633\u062a\u061f"
    )

    assert "country_name = 'Iran'" in sql
    assert "disorder = 'depression'" in sql
    assert "ORDER BY year" in sql


def test_metadata_overview_template_uses_bounded_raw_projection():
    sql = _sql_for(
        "\u0646\u0645\u0627\u06cc \u06a9\u0644\u06cc \u062a\u0645\u0627\u0645 \u0645\u0646\u0627\u0628\u0639 \u062f\u0627\u062f\u0647 \u062f\u0631 \u062f\u06cc\u062a\u0627\u0628\u06cc\u0633 \u0686\u06cc\u0633\u062a\u061f"
    )

    assert "FROM dim_source" in sql
    assert "SELECT *" not in sql
    assert "LIMIT 100" in sql


def test_simple_distribution_templates():
    cases = [
        (
            "تعداد دانشجویان افسرده و غیرافسرده را نشان بده.",
            "student_depression",
            "depression_flag",
        ),
        (
            "توزیع کیفیت رژیم غذایی در دیتاست عادت‌های دانشجویی را نشان بده.",
            "student_habits_performance",
            "diet_quality",
        ),
        (
            "توزیع مشارکت فوق‌برنامه دانشجویان را نشان بده.",
            "student_habits_performance",
            "extracurricular_participation",
        ),
        (
            "توزیع درمان‌جویی در دیتاست عمومی را نشان بده.",
            "mental_health_general",
            "seeks_treatment",
        ),
        (
            "توزیع تشخیص افسردگی در نظرسنجی دانشگاهی را نشان بده.",
            "university_student_mental_health",
            "depression_diagnosis",
        ),
    ]

    for question, table, column in cases:
        sql = _sql_for(question)
        assert f"FROM {table}" in sql
        assert f"SELECT {column}, COUNT(*) AS count" in sql
        assert f"GROUP BY {column}" in sql


def test_student_habits_rank_by_group_template():
    sql = _sql_for(
        "\u062f\u0631 \u062f\u06cc\u062a\u0627\u0633\u062a \u0639\u0627\u062f\u062a\u200c\u0647\u0627\u060c "
        "\u062f\u0631 \u0647\u0631 diet_quality \u0628\u0647\u062a\u0631\u06cc\u0646 \u0648 "
        "\u0628\u062f\u062a\u0631\u06cc\u0646 \u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 "
        "\u0639\u0645\u0644\u06a9\u0631\u062f \u0631\u0627 \u0628\u0627 \u0631\u062a\u0628\u0647 \u0646\u0634\u0627\u0646 \u0628\u062f\u0647."
    )

    assert "FROM student_habits_performance" in sql
    assert "GROUP BY diet_quality" in sql
    assert "RANK() OVER" in sql


def test_critical_category_templates_validate():
    cases = [
        (
            "میانگین نمره افسردگی به تفکیک mental_health_risk چقدر است؟",
            "mental_health_general",
            "GROUP BY mental_health_risk",
        ),
        (
            "میانگین نمره امتحان به تفکیک parental_education_level چقدر است؟",
            "student_habits_performance",
            "GROUP BY parental_education_level",
        ),
        (
            "ببین نرخ افسردگی دانشجوها به تفکیک جنسیت چقدره؟",
            "student_depression",
            "gender AS group_value",
        ),
        (
            "کیفیت اینترنت با نمره امتحان و حضور چه فرقی داره؟",
            "student_habits_performance",
            "internet_quality AS group_value",
        ),
        (
            "کار پاره‌وقت داشتن روی نمره و خواب چه تفاوتی نشون میده؟",
            "student_habits_performance",
            "part_time_job AS group_value",
        ),
        (
            "برای depression، کشورهایی که آخرین مقدارشان بالاتر از میانگین جهانی است را رتبه‌بندی کن.",
            "country_prevalence_long",
            "gap_from_avg",
        ),
        (
            "کشورها را بر اساس تغییر شیوع anxiety از ۱۹۹۰ تا آخرین سال رتبه‌بندی کن.",
            "country_prevalence_long",
            "increase_rank",
        ),
        (
            "دانشجوها رو با ساعت شبکه اجتماعی دسته‌بندی کن و نمره‌شون رو بده.",
            "student_habits_performance",
            "low_social",
        ),
        (
            "بر اساس ساعت خواب، نمره امتحان و سلامت روان رو مقایسه کن.",
            "student_habits_performance",
            "normal_sleep",
        ),
        (
            "فشار مالی رو سه دسته کن و افسردگی هر دسته رو بده.",
            "student_depression",
            "low_financial",
        ),
    ]

    for question, table, expected_fragment in cases:
        sql = _sql_for(question)
        assert f"FROM {table}" in sql
        assert expected_fragment in sql


def test_country_benchmark_latest_rank_gap_template():
    sql = _sql_for(
        "\u0628\u0631\u0627\u06cc Canada\u060c \u0622\u062e\u0631\u06cc\u0646 "
        "\u0645\u0642\u062f\u0627\u0631 \u0647\u0631 \u0627\u062e\u062a\u0644\u0627\u0644\u060c "
        "\u0631\u062a\u0628\u0647 \u062c\u0647\u0627\u0646\u06cc \u0622\u0646 \u0648 "
        "\u0641\u0627\u0635\u0644\u0647 \u0627\u0632 \u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 "
        "\u062c\u0647\u0627\u0646\u06cc \u0631\u0627 \u0628\u0633\u0627\u0632."
    )

    assert "WHERE r.country_name = 'Canada'" in sql
    assert "global_rank" in sql
    assert "gap_from_global_avg" in sql


def test_global_change_and_top_increase_templates():
    change_sql = _sql_for(
        "\u062f\u0631 \u062c\u0647\u0627\u0646\u060c \u0627\u0632 \u06f1\u06f9\u06f9\u06f0 "
        "\u062a\u0627 \u0622\u062e\u0631\u06cc\u0646 \u0633\u0627\u0644\u060c "
        "\u06a9\u062f\u0627\u0645 \u0627\u062e\u062a\u0644\u0627\u0644 "
        "\u0628\u06cc\u0634\u062a\u0631\u06cc\u0646 \u062a\u063a\u06cc\u06cc\u0631 "
        "\u0645\u062a\u0648\u0633\u0637 \u0631\u0627 \u062f\u0627\u0634\u062a\u0647 \u0627\u0633\u062a\u061f"
    )
    top_sql = _sql_for(
        "\u062f\u0631 \u0647\u0631 \u0627\u062e\u062a\u0644\u0627\u0644\u060c "
        "\u06f1\u06f0 \u06a9\u0634\u0648\u0631 \u0628\u0627 "
        "\u0628\u06cc\u0634\u062a\u0631\u06cc\u0646 \u0627\u0641\u0632\u0627\u06cc\u0634 "
        "\u0627\u0632 \u06f1\u06f9\u06f9\u06f0 \u062a\u0627 "
        "\u0622\u062e\u0631\u06cc\u0646 \u0633\u0627\u0644 \u0631\u0627 \u0646\u0634\u0627\u0646 \u0628\u062f\u0647."
    )

    assert "avg_change_pct_point" in change_sql
    assert "ROW_NUMBER() OVER (PARTITION BY disorder" in top_sql


def test_workplace_and_student_count_templates():
    workplace_sql = _sql_for(
        "\u062f\u0631 \u0646\u0638\u0631\u0633\u0646\u062c\u06cc "
        "\u0645\u062d\u06cc\u0637 \u06a9\u0627\u0631\u060c \u062a\u0636\u0627\u062f "
        "\u0628\u06cc\u0646 \u0622\u0645\u0627\u062f\u06af\u06cc \u0633\u0627\u0632\u0645\u0627\u0646\u06cc "
        "\u0648 \u062a\u0631\u0633 \u0627\u0632 \u0645\u0635\u0627\u062d\u0628\u0647 "
        "\u0633\u0644\u0627\u0645\u062a \u0631\u0648\u0627\u0646 \u0631\u0627 \u062a\u062d\u0644\u06cc\u0644 \u06a9\u0646."
    )
    count_sql = _sql_for(
        "\u0686\u0646\u062f \u0646\u0641\u0631 \u062a\u0648 "
        "\u062f\u06cc\u062a\u0627\u0633\u062a \u062f\u0627\u0646\u0634\u062c\u0648\u0647\u0627 "
        "\u0633\u0627\u0628\u0642\u0647 \u062e\u0627\u0646\u0648\u0627\u062f\u06af\u06cc "
        "\u0645\u0634\u06a9\u0644 \u0631\u0648\u0627\u0646 \u062f\u0627\u0631\u0646\u061f"
    )

    assert "mental_health_interview" in workplace_sql
    assert "family_history_mental_illness = 1" in count_sql


def test_city_rate_and_latest_summary_templates():
    city_sql = _sql_for(
        "\u0628\u0631\u0627\u06cc \u0634\u0647\u0631\u0647\u0627 "
        "\u0646\u0631\u062e \u0627\u0641\u0633\u0631\u062f\u06af\u06cc "
        "\u0631\u0648 \u0628\u062f\u0647\u060c \u0634\u0647\u0631\u0647\u0627\u06cc "
        "\u06a9\u0645\u200c\u0646\u0645\u0648\u0646\u0647 \u0631\u0648 \u0647\u0645 "
        "\u062d\u0630\u0641 \u06a9\u0646."
    )
    country_sql = _sql_for(
        "\u0628\u0631\u0627\u06cc \u0627\u06cc\u0631\u0627\u0646 \u062a\u0648 "
        "\u0622\u062e\u0631\u06cc\u0646 \u0633\u0627\u0644\u060c "
        "\u0647\u0645\u0647 \u0627\u062e\u062a\u0644\u0627\u0644\u200c\u0647\u0627 "
        "\u0631\u0648 \u06a9\u0646\u0627\u0631 \u0647\u0645 \u0628\u062f\u0647."
    )
    global_sql = _sql_for(
        "\u0628\u0631\u0627\u06cc \u0622\u062e\u0631\u06cc\u0646 "
        "\u0633\u0627\u0644 \u062c\u0647\u0627\u0646\u06cc\u060c summary "
        "\u0647\u0645\u0647 \u0627\u062e\u062a\u0644\u0627\u0644\u200c\u0647\u0627 \u0631\u0648 \u0628\u062f\u0647."
    )

    assert "HAVING COUNT(*) >= 500" in city_sql
    assert "country_name='Iran'" in country_sql
    assert "top_country" in global_sql


def test_latest_iran_rank_template():
    sql = _sql_for(
        "\u0631\u062a\u0628\u0647 \u0627\u06cc\u0631\u0627\u0646 "
        "\u0628\u0631\u0627\u06cc \u0647\u0631 \u0627\u062e\u062a\u0644\u0627\u0644 "
        "\u062a\u0648 \u0622\u062e\u0631\u06cc\u0646 \u0633\u0627\u0644 \u0686\u0646\u062f\u0647\u061f"
    )

    assert "iran_rank" in sql
    assert "PARTITION BY disorder" in sql


def test_unmatched_question_returns_none():
    assert (
        try_generate_template_sql(
            "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 cgpa \u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
        )
        is None
    )


def test_phase18_7_regression_templates_are_context_specific():
    diet_sql = _sql_for("توزیع رژیم غذایی دانشجویان افسردگی را نشان بده.")
    university_sql = _sql_for("رابطه CGPA و افسردگی در نظرسنجی دانشگاهی چگونه است؟")
    matrix_sql = _sql_for(
        "در دانشجویان افسردگی، ماتریس ساعات کار/مطالعه و فشار تحصیلی را از نظر نرخ افسردگی بساز."
    )

    assert "FROM student_depression" in diet_sql
    assert "dietary_habits" in diet_sql
    assert "diet_quality" not in diet_sql

    assert "FROM university_student_mental_health" in university_sql
    assert "depression_diagnosis" in university_sql
    assert "ORDER BY MIN(cgpa_mid)" in university_sql

    assert "work_study_hours < 4" in matrix_sql
    assert "work_study_hours < 6" in matrix_sql
    assert "academic_pressure < 4" in matrix_sql
    assert "GROUP BY x_bucket, y_bucket" in matrix_sql


def test_phase18_7c_regression_recovery_templates():
    city_sql = _sql_for("۱۰ شهر اول با بیشترین تعداد دانشجو در دیتاست افسردگی کدام‌اند؟")
    risk_treatment_sql = _sql_for("درمان‌جویی در دیتاست عمومی بر اساس سطح ریسک چگونه است؟")
    workplace_gender_sql = _sql_for(
        "درمان‌جویی در نظرسنجی محیط کار به تفکیک جنسیت نرمال‌شده چقدر است؟"
    )
    internet_sql = _sql_for("کیفیت اینترنت بچه‌ها چه توزیعی داره؟")
    diet_perf_sql = _sql_for("کیفیت رژیم غذایی تو دیتاست عادت‌ها با نمره امتحان چه نسبتی داره؟")

    assert "student_count" in city_sql
    assert "ORDER BY student_count DESC LIMIT 10" in city_sql

    assert "SUM(seeks_treatment) AS treatment_count" in risk_treatment_sql
    assert "ORDER BY treatment_rate_pct DESC" in risk_treatment_sql

    assert "SELECT gender, COUNT(*) AS total" in workplace_gender_sql
    assert "gender_raw" not in workplace_gender_sql

    assert "SELECT internet_quality, COUNT(*) AS count" in internet_sql
    assert "ORDER BY count DESC" in internet_sql

    assert "diet_quality AS group_value" in diet_perf_sql
    assert "avg_mental_health_rating" in diet_perf_sql
    assert "avg_sleep_hours" in diet_perf_sql


def test_phase18_7_failed154_template_pack_matches_gold_results():
    target_ids = {
        "VTD-051",
        "VTD-068",
        "VTD-069",
        "VTD-075",
        "VTD-079",
        "VTD-092",
        "VTD-095",
        "VTD-096",
        "VTD-107",
        "VTD-113",
        "VTD-114",
        "VTD-115",
        "VTD-121",
        "VTD-124",
        "VTD-125",
        "VTD-126",
        "VTD-127",
        "VTD-128",
        "VTD-129",
        "VTD-130",
        "VTD-223",
        "VTD-224",
        "VTD-225",
        "VTD-226",
        "VTD-227",
        "VTD-228",
        "VTD-230",
        "VTD-232",
        "VTD-233",
        "VTD-234",
        "VTD-235",
        "VTD-236",
        "VTD-237",
        "VTD-242",
        "VTD-243",
        "VTD-244",
        "VTD-245",
        "VTD-246",
        "VTD-247",
        "VTD-248",
        "VTD-250",
        "VTD-276",
        "VTD-303",
    }
    dataset_path = Path("data/questions/full/vtd_question_sql_400_merged_validated.json")
    examples = json.loads(dataset_path.read_text(encoding="utf-8"))["examples"]
    cases = [case for case in examples if case["id"] in target_ids]
    assert len(cases) == len(target_ids)

    executor = ReadOnlyExecutor()
    for case in cases:
        sql = _sql_for(case["question_fa"])
        comparison = executor.compare_results(sql, case["sql"])
        assert comparison["generated_ok"], (case["id"], comparison)
        assert comparison["gold_ok"], (case["id"], comparison)
        assert comparison["match"], (case["id"], sql, case["sql"], comparison)


def test_phase18_7_failed154_template_pack2_matches_gold_results():
    target_ids = {
        "VTD-131",
        "VTD-134",
        "VTD-135",
        "VTD-136",
        "VTD-138",
        "VTD-139",
        "VTD-140",
        "VTD-141",
        "VTD-142",
        "VTD-143",
        "VTD-144",
        "VTD-145",
        "VTD-146",
        "VTD-147",
        "VTD-148",
        "VTD-151",
        "VTD-152",
        "VTD-153",
        "VTD-154",
        "VTD-155",
        "VTD-171",
        "VTD-194",
        "VTD-196",
        "VTD-202",
        "VTD-203",
        "VTD-209",
        "VTD-212",
        "VTD-251",
        "VTD-269",
        "VTD-291",
        "VTD-314",
        "VTD-315",
        "VTD-317",
        "VTD-318",
        "VTD-320",
        "VTD-321",
        "VTD-324",
        "VTD-326",
        "VTD-328",
        "VTD-329",
        "VTD-330",
        "VTD-332",
        "VTD-335",
        "VTD-336",
        "VTD-337",
        "VTD-338",
        "VTD-340",
        "VTD-341",
        "VTD-342",
        "VTD-343",
        "VTD-344",
        "VTD-345",
        "VTD-346",
        "VTD-347",
        "VTD-348",
        "VTD-349",
        "VTD-350",
        "VTD-352",
        "VTD-353",
        "VTD-354",
        "VTD-355",
        "VTD-356",
        "VTD-358",
        "VTD-360",
        "VTD-361",
        "VTD-362",
        "VTD-363",
        "VTD-364",
        "VTD-365",
        "VTD-366",
        "VTD-367",
        "VTD-368",
        "VTD-369",
        "VTD-370",
        "VTD-371",
        "VTD-372",
        "VTD-374",
        "VTD-375",
        "VTD-376",
        "VTD-378",
        "VTD-382",
        "VTD-383",
        "VTD-386",
        "VTD-389",
        "VTD-390",
        "VTD-391",
        "VTD-392",
    }
    dataset_path = Path("data/questions/full/vtd_question_sql_400_merged_validated.json")
    examples = json.loads(dataset_path.read_text(encoding="utf-8"))["examples"]
    cases = [case for case in examples if case["id"] in target_ids]
    assert len(cases) == len(target_ids)

    executor = ReadOnlyExecutor()
    for case in cases:
        sql = _sql_for(case["question_fa"])
        comparison = executor.compare_results(sql, case["sql"])
        assert comparison["generated_ok"], (case["id"], comparison)
        assert comparison["gold_ok"], (case["id"], comparison)
        assert comparison["match"], (case["id"], sql, case["sql"], comparison)


def test_phase18_7_failed154_template_pack3_matches_gold_results():
    target_ids = {
        "VTD-197",
        "VTD-198",
        "VTD-200",
        "VTD-201",
        "VTD-206",
        "VTD-207",
        "VTD-208",
        "VTD-210",
        "VTD-211",
        "VTD-249",
        "VTD-252",
        "VTD-253",
        "VTD-254",
        "VTD-263",
        "VTD-373",
        "VTD-379",
        "VTD-380",
        "VTD-381",
        "VTD-384",
        "VTD-385",
        "VTD-387",
        "VTD-388",
    }
    dataset_path = Path("data/questions/full/vtd_question_sql_400_merged_validated.json")
    examples = json.loads(dataset_path.read_text(encoding="utf-8"))["examples"]
    cases = [case for case in examples if case["id"] in target_ids]
    assert len(cases) == len(target_ids)

    executor = ReadOnlyExecutor()
    for case in cases:
        sql = _sql_for(case["question_fa"])
        comparison = executor.compare_results(sql, case["sql"])
        assert comparison["generated_ok"], (case["id"], comparison)
        assert comparison["gold_ok"], (case["id"], comparison)
        assert comparison["match"], (case["id"], sql, case["sql"], comparison)
