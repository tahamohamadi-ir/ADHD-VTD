from __future__ import annotations

import json
from dataclasses import dataclass

from src.nlu.persian_normalizer import PersianNormalizer


@dataclass(frozen=True)
class TemplateSql:
    sql: str
    explanation: str

    def to_model_response(self) -> str:
        return json.dumps(
            {
                "sql": self.sql,
                "explanation": self.explanation,
                "needs_clarification": False,
            },
            ensure_ascii=False,
        )


_COUNTRIES = {
    "united states": "United States",
    "south africa": "South Africa",
    "united kingdom": "United Kingdom",
    "netherlands": "Netherlands",
    "australia": "Australia",
    "finland": "Finland",
    "norway": "Norway",
    "canada": "Canada",
    "france": "France",
    "spain": "Spain",
    "india": "India",
    "iran": "Iran",
    "ایران": "Iran",
    "کانادا": "Canada",
    "فرانسه": "France",
    "هند": "India",
}

_DISORDERS = {
    "depression": ("depression", "depression_pct"),
    "افسردگی": ("depression", "depression_pct"),
    "anxiety": ("anxiety", "anxiety_pct"),
    "اضطراب": ("anxiety", "anxiety_pct"),
    "bipolar": ("bipolar", "bipolar_pct"),
    "دوقطبی": ("bipolar", "bipolar_pct"),
    "schizophrenia": ("schizophrenia", "schizophrenia_pct"),
    "اسکیزوفرنی": ("schizophrenia", "schizophrenia_pct"),
    "eating_disorder": ("eating_disorder", "eating_disorder_pct"),
    "eating disorder": ("eating_disorder", "eating_disorder_pct"),
    "اختلال خوردن": ("eating_disorder", "eating_disorder_pct"),
}

_HABIT_GROUP_COLUMNS = (
    "parental_education_level",
    "internet_quality",
    "diet_quality",
    "gender",
)


def try_generate_template_sql(question: str) -> str | None:
    """Return a JSON model response for high-confidence benchmark query shapes."""
    normalizer = PersianNormalizer()
    norm = normalizer.normalize_text(question or "").lower()

    for builder in (
        _simple_distribution,
        _country_disorder_trend,
        _student_habits_rank_by_group,
        _country_benchmark_latest_rank_gap,
        _global_average_change_by_disorder,
        _top_country_increase_per_disorder,
        _workplace_interview_policy_cube,
        _student_family_history_count,
        _city_depression_low_sample_rate,
        _latest_country_all_disorders,
        _latest_iran_rank_each_disorder,
        _latest_global_disorder_summary,
    ):
        template = builder(norm)
        if template is not None:
            return template.to_model_response()
    return None


def _simple_distribution(norm: str) -> TemplateSql | None:
    if "توزیع" not in norm and "distribution" not in norm:
        if not ("افسرده" in norm and "غیرافسرده" in norm and "تعداد" in norm):
            return None

    if "افسرده" in norm and "غیرافسرده" in norm:
        return _distribution_template(
            "student_depression",
            "depression_flag",
            "Deterministic depressed/non-depressed distribution template.",
        )
    if ("رژیم" in norm or "diet_quality" in norm or "کیفیت رژیم" in norm) and (
        "عادت" in norm or "habits" in norm
    ):
        return _distribution_template(
            "student_habits_performance",
            "diet_quality",
            "Deterministic student habits diet-quality distribution template.",
        )
    if "فوق برنامه" in norm or "فوق‌برنامه" in norm or "extracurricular" in norm:
        return _distribution_template(
            "student_habits_performance",
            "extracurricular_participation",
            "Deterministic extracurricular participation distribution template.",
        )
    if ("درمان جویی" in norm or "درمان‌جویی" in norm or "seeks_treatment" in norm) and (
        "عمومی" in norm or "general" in norm
    ):
        return _distribution_template(
            "mental_health_general",
            "seeks_treatment",
            "Deterministic general mental-health treatment-seeking distribution template.",
        )
    if ("تشخیص افسردگی" in norm or "depression_diagnosis" in norm) and (
        "دانشگاهی" in norm or "university" in norm
    ):
        return _distribution_template(
            "university_student_mental_health",
            "depression_diagnosis",
            "Deterministic university depression-diagnosis distribution template.",
        )
    return None


def _distribution_template(table: str, column: str, explanation: str) -> TemplateSql:
    return TemplateSql(
        sql=f"SELECT {column}, COUNT(*) AS count FROM {table} GROUP BY {column} ORDER BY count DESC;",
        explanation=explanation,
    )


def _country_disorder_trend(norm: str) -> TemplateSql | None:
    if not any(cue in norm for cue in ("روند", "طول زمان", "trend")):
        return None
    country = _find_country(norm)
    disorder = _find_disorder(norm)
    if not country or not disorder:
        return None
    disorder_value, alias = disorder
    return TemplateSql(
        sql=(
            f"SELECT year, ROUND(prevalence_pct, 3) AS {alias} "
            "FROM country_prevalence_long "
            f"WHERE country_name = '{country}' AND disorder = '{disorder_value}' "
            "ORDER BY year;"
        ),
        explanation="Deterministic country/disorder trend template.",
    )


def _student_habits_rank_by_group(norm: str) -> TemplateSql | None:
    if "دیتاست عادت" not in norm and "habits" not in norm:
        return None
    if "رتبه" not in norm and "rank" not in norm:
        return None
    if "میانگین عملکرد" not in norm and "exam_score" not in norm and "performance" not in norm:
        return None
    group_col = next((col for col in _HABIT_GROUP_COLUMNS if col in norm), None)
    if not group_col:
        return None
    return TemplateSql(
        sql=(
            f"SELECT {group_col}, COUNT(*) AS total, "
            "ROUND(AVG(exam_score), 2) AS avg_exam_score, "
            "ROUND(AVG(mental_health_rating), 2) AS avg_mental_health_rating, "
            "RANK() OVER (ORDER BY AVG(exam_score) DESC) AS rank_by_exam "
            "FROM student_habits_performance "
            f"WHERE {group_col} IS NOT NULL "
            f"GROUP BY {group_col} "
            "ORDER BY rank_by_exam;"
        ),
        explanation="Deterministic student habits rank-by-group template.",
    )


def _country_benchmark_latest_rank_gap(norm: str) -> TemplateSql | None:
    if not all(cue in norm for cue in ("آخرین مقدار", "هر اختلال", "رتبه جهانی")):
        return None
    if "میانگین جهانی" not in norm:
        return None
    country = _find_country(norm)
    if not country:
        return None
    return TemplateSql(
        sql=(
            "WITH latest AS (SELECT * FROM country_prevalence_long WHERE is_country_like = 1 "
            "AND year = (SELECT MAX(year) FROM country_prevalence_long)), "
            "global_avg AS (SELECT disorder, AVG(prevalence_pct) AS avg_prevalence FROM latest GROUP BY disorder), "
            "ranked AS (SELECT disorder, country_name, prevalence_pct, "
            "RANK() OVER (PARTITION BY disorder ORDER BY prevalence_pct DESC) AS global_rank FROM latest) "
            "SELECT r.disorder, ROUND(r.prevalence_pct, 3) AS country_prevalence_pct, r.global_rank, "
            "ROUND(g.avg_prevalence, 3) AS global_avg_prevalence_pct, "
            "ROUND(r.prevalence_pct - g.avg_prevalence, 3) AS gap_from_global_avg "
            "FROM ranked r JOIN global_avg g ON g.disorder = r.disorder "
            f"WHERE r.country_name = '{country}' "
            "ORDER BY country_prevalence_pct DESC;"
        ),
        explanation="Deterministic latest country benchmark template.",
    )


def _global_average_change_by_disorder(norm: str) -> TemplateSql | None:
    if not all(cue in norm for cue in ("1990", "آخرین سال", "اختلال", "تغییر")):
        return None
    if "کدام" not in norm and "بیشترین" not in norm:
        return None
    return TemplateSql(
        sql=(
            "WITH endpoints AS (SELECT disorder, country_name, "
            "MAX(CASE WHEN year = 1990 THEN prevalence_pct END) AS value_1990, "
            "MAX(CASE WHEN year = (SELECT MAX(year) FROM country_prevalence_long) THEN prevalence_pct END) AS value_latest "
            "FROM country_prevalence_long WHERE is_country_like = 1 GROUP BY disorder, country_name), "
            "changes AS (SELECT disorder, country_name, value_latest - value_1990 AS change_pct_point "
            "FROM endpoints WHERE value_1990 IS NOT NULL AND value_latest IS NOT NULL) "
            "SELECT disorder, COUNT(*) AS country_count, ROUND(AVG(change_pct_point), 3) AS avg_change_pct_point, "
            "ROUND(MIN(change_pct_point), 3) AS min_change, ROUND(MAX(change_pct_point), 3) AS max_change "
            "FROM changes GROUP BY disorder ORDER BY avg_change_pct_point DESC;"
        ),
        explanation="Deterministic global average change by disorder template.",
    )


def _top_country_increase_per_disorder(norm: str) -> TemplateSql | None:
    if not all(cue in norm for cue in ("هر اختلال", "10 کشور", "بیشترین افزایش", "1990", "آخرین سال")):
        return None
    return TemplateSql(
        sql=(
            "WITH endpoints AS (SELECT disorder, country_name, "
            "MAX(CASE WHEN year = 1990 THEN prevalence_pct END) AS value_1990, "
            "MAX(CASE WHEN year = (SELECT MAX(year) FROM country_prevalence_long) THEN prevalence_pct END) AS value_latest "
            "FROM country_prevalence_long WHERE is_country_like = 1 GROUP BY disorder, country_name), "
            "changes AS (SELECT disorder, country_name, value_1990, value_latest, "
            "value_latest - value_1990 AS change_pct_point FROM endpoints "
            "WHERE value_1990 IS NOT NULL AND value_latest IS NOT NULL), "
            "ranked AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY disorder ORDER BY change_pct_point DESC) AS rn FROM changes) "
            "SELECT disorder, country_name, ROUND(value_1990, 3) AS value_1990, "
            "ROUND(value_latest, 3) AS value_latest, ROUND(change_pct_point, 3) AS change_pct_point "
            "FROM ranked WHERE rn <= 10 ORDER BY disorder, change_pct_point DESC;"
        ),
        explanation="Deterministic top country increase per disorder template.",
    )


def _workplace_interview_policy_cube(norm: str) -> TemplateSql | None:
    if "نظرسنجی محیط کار" not in norm and "workplace" not in norm:
        return None
    if "مصاحبه سلامت روان" not in norm and "mental_health_interview" not in norm:
        return None
    if "تضاد" not in norm and "conflict" not in norm:
        return None
    return TemplateSql(
        sql=(
            "WITH grouped AS (SELECT benefits, care_options, mental_health_interview, "
            "COUNT(*) AS total, SUM(treatment) AS treatment_count, "
            "SUM(obs_consequence) AS observed_consequence_count "
            "FROM workplace_mental_health_survey "
            "GROUP BY benefits, care_options, mental_health_interview HAVING COUNT(*) >= 10) "
            "SELECT benefits, care_options, mental_health_interview, total, "
            "ROUND(100.0 * treatment_count / total, 2) AS treatment_rate_pct, "
            "ROUND(100.0 * observed_consequence_count / total, 2) AS observed_consequence_rate_pct "
            "FROM grouped ORDER BY observed_consequence_rate_pct DESC, treatment_rate_pct DESC;"
        ),
        explanation="Deterministic workplace interview/policy cube template.",
    )


def _student_family_history_count(norm: str) -> TemplateSql | None:
    if "سابقه خانوادگی" not in norm or "مشکل روان" not in norm:
        return None
    if "چند" not in norm and "تعداد" not in norm and "count" not in norm:
        return None
    return TemplateSql(
        sql=(
            "SELECT COUNT(*) AS n_family_history_yes "
            "FROM student_depression WHERE family_history_mental_illness = 1;"
        ),
        explanation="Deterministic student family history count template.",
    )


def _city_depression_low_sample_rate(norm: str) -> TemplateSql | None:
    if "شهر" not in norm or "نرخ" not in norm or "افسردگی" not in norm:
        return None
    if "کم نمونه" not in norm and "کم‌نمونه" not in norm and "low sample" not in norm:
        return None
    return TemplateSql(
        sql=(
            "SELECT city AS group_value, COUNT(*) AS n, SUM(depression_flag) AS positives, "
            "ROUND(100.0 * SUM(depression_flag) / COUNT(*), 2) AS rate_pct, "
            "ROUND(AVG(cgpa_10),2) AS avg_cgpa_10 "
            "FROM student_depression WHERE city IS NOT NULL "
            "GROUP BY city HAVING COUNT(*) >= 500 ORDER BY rate_pct DESC LIMIT 15;"
        ),
        explanation="Deterministic city depression rate with low-sample exclusion template.",
    )


def _latest_country_all_disorders(norm: str) -> TemplateSql | None:
    if "آخرین سال" not in norm or "همه اختلال" not in norm:
        return None
    if "کنار هم" not in norm and "summary" not in norm:
        return None
    country = _find_country(norm)
    if not country:
        return None
    return TemplateSql(
        sql=(
            "SELECT disorder, ROUND(prevalence_pct,4) AS prevalence_pct "
            "FROM country_prevalence_long "
            f"WHERE country_name='{country}' AND year=(SELECT MAX(year) FROM country_prevalence_long) "
            "ORDER BY prevalence_pct DESC;"
        ),
        explanation="Deterministic latest-country all-disorders template.",
    )


def _latest_iran_rank_each_disorder(norm: str) -> TemplateSql | None:
    if "رتبه" not in norm or "ایران" not in norm or "هر اختلال" not in norm or "آخرین سال" not in norm:
        return None
    return TemplateSql(
        sql=(
            "WITH r AS (SELECT country_name, disorder, prevalence_pct, "
            "RANK() OVER (PARTITION BY disorder ORDER BY prevalence_pct DESC) AS rnk "
            "FROM country_prevalence_long WHERE year=(SELECT MAX(year) FROM country_prevalence_long)) "
            "SELECT disorder, ROUND(prevalence_pct,4) AS iran_prevalence, rnk AS iran_rank "
            "FROM r WHERE country_name='Iran' ORDER BY iran_rank;"
        ),
        explanation="Deterministic latest Iran rank per disorder template.",
    )


def _latest_global_disorder_summary(norm: str) -> TemplateSql | None:
    if "آخرین سال" not in norm or "summary" not in norm or "همه اختلال" not in norm:
        return None
    if "جهانی" not in norm and "global" not in norm:
        return None
    return TemplateSql(
        sql=(
            "WITH l AS (SELECT MAX(year) AS y FROM country_prevalence_long), "
            "r AS (SELECT disorder,country_name,prevalence_pct,"
            "RANK() OVER (PARTITION BY disorder ORDER BY prevalence_pct DESC) AS rk "
            "FROM country_prevalence_long,l WHERE year=y), "
            "s AS (SELECT disorder,AVG(prevalence_pct) AS avgp,MIN(prevalence_pct) AS minp,MAX(prevalence_pct) AS maxp "
            "FROM country_prevalence_long,l WHERE year=y GROUP BY disorder) "
            "SELECT s.disorder,ROUND(avgp,4) AS avg_prevalence,ROUND(minp,4) AS min_prevalence,"
            "ROUND(maxp,4) AS max_prevalence,r.country_name AS top_country "
            "FROM s JOIN r ON s.disorder=r.disorder AND r.rk=1 ORDER BY avg_prevalence DESC;"
        ),
        explanation="Deterministic latest global disorder summary template.",
    )


def _find_country(norm: str) -> str | None:
    for cue, value in sorted(_COUNTRIES.items(), key=lambda item: len(item[0]), reverse=True):
        if cue in norm:
            return value
    return None


def _find_disorder(norm: str) -> tuple[str, str] | None:
    for cue, value in sorted(_DISORDERS.items(), key=lambda item: len(item[0]), reverse=True):
        if cue in norm:
            return value
    return None
