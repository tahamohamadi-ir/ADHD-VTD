# VTD Schema Reference

> Tables: 11

## country_prevalence_long
**Rows:** 32100

| Column | Type | PK |
|---|---|---|
| `prevalence_id` | INTEGER | ✅ |
| `country_name` | TEXT |  |
| `country_code` | TEXT |  |
| `year` | INTEGER |  |
| `is_country_like` | INTEGER |  |
| `disorder` | TEXT |  |
| `prevalence_pct` | REAL |  |

---

## country_prevalence_wide
**Rows:** 6420

| Column | Type | PK |
|---|---|---|
| `prevalence_row_id` | INTEGER | ✅ |
| `country_name` | TEXT |  |
| `country_code` | TEXT |  |
| `year` | INTEGER |  |
| `is_country_like` | INTEGER |  |
| `schizophrenia_pct` | REAL |  |
| `depression_pct` | REAL |  |
| `anxiety_pct` | REAL |  |
| `bipolar_pct` | REAL |  |
| `eating_disorder_pct` | REAL |  |

---

## dim_source
**Rows:** 6

| Column | Type | PK |
|---|---|---|
| `source_id` | INTEGER | ✅ |
| `source_name` | TEXT |  |
| `file_name` | TEXT |  |
| `description` | TEXT |  |
| `row_count` | INTEGER |  |

---

## mental_health_general
**Rows:** 10000

| Column | Type | PK |
|---|---|---|
| `general_row_id` | INTEGER | ✅ |
| `age` | INTEGER |  |
| `gender` | TEXT |  |
| `employment_status` | TEXT |  |
| `work_environment` | TEXT |  |
| `mental_health_history` | INTEGER |  |
| `seeks_treatment` | INTEGER |  |
| `stress_level` | INTEGER |  |
| `sleep_hours` | REAL |  |
| `physical_activity_days` | INTEGER |  |
| `depression_score` | INTEGER |  |
| `anxiety_score` | INTEGER |  |
| `social_support_score` | INTEGER |  |
| `productivity_score` | REAL |  |
| `mental_health_risk` | TEXT |  |

---

## student_depression
**Rows:** 27901

| Column | Type | PK |
|---|---|---|
| `student_depression_id` | INTEGER | ✅ |
| `source_row_id` | INTEGER |  |
| `gender` | TEXT |  |
| `age` | REAL |  |
| `city` | TEXT |  |
| `country` | TEXT |  |
| `profession` | TEXT |  |
| `academic_pressure` | REAL |  |
| `work_pressure` | REAL |  |
| `cgpa_10` | REAL |  |
| `study_satisfaction` | REAL |  |
| `job_satisfaction` | REAL |  |
| `sleep_duration_category` | TEXT |  |
| `dietary_habits` | TEXT |  |
| `degree` | TEXT |  |
| `suicidal_thoughts` | INTEGER |  |
| `work_study_hours` | REAL |  |
| `financial_stress` | REAL |  |
| `family_history_mental_illness` | INTEGER |  |
| `depression_flag` | INTEGER |  |
| `sleep_mid_hours` | REAL |  |

---

## student_habits_performance
**Rows:** 1000

| Column | Type | PK |
|---|---|---|
| `habit_row_id` | INTEGER | ✅ |
| `original_student_id` | TEXT |  |
| `age` | INTEGER |  |
| `gender` | TEXT |  |
| `study_hours_per_day` | REAL |  |
| `social_media_hours` | REAL |  |
| `netflix_hours` | REAL |  |
| `part_time_job` | INTEGER |  |
| `attendance_percentage` | REAL |  |
| `sleep_hours` | REAL |  |
| `diet_quality` | TEXT |  |
| `exercise_frequency` | INTEGER |  |
| `parental_education_level` | TEXT |  |
| `internet_quality` | TEXT |  |
| `mental_health_rating` | INTEGER |  |
| `extracurricular_participation` | INTEGER |  |
| `exam_score` | REAL |  |

---

## university_student_mental_health
**Rows:** 101

| Column | Type | PK |
|---|---|---|
| `university_row_id` | INTEGER | ✅ |
| `survey_timestamp` | TEXT |  |
| `age` | REAL |  |
| `gender` | TEXT |  |
| `course` | TEXT |  |
| `year_of_study` | INTEGER |  |
| `cgpa_range` | TEXT |  |
| `cgpa_mid` | REAL |  |
| `marital_status` | INTEGER |  |
| `depression_diagnosis` | INTEGER |  |
| `anxiety_diagnosis` | INTEGER |  |
| `panic_attack` | INTEGER |  |
| `treatment_seeking` | INTEGER |  |

---

## workplace_mental_health_survey
**Rows:** 1259

| Column | Type | PK |
|---|---|---|
| `workplace_row_id` | INTEGER | ✅ |
| `survey_timestamp` | TEXT |  |
| `survey_year` | INTEGER |  |
| `age_raw` | REAL |  |
| `age` | REAL |  |
| `gender_raw` | TEXT |  |
| `gender` | TEXT |  |
| `country` | TEXT |  |
| `state` | TEXT |  |
| `self_employed` | INTEGER |  |
| `family_history` | INTEGER |  |
| `treatment` | INTEGER |  |
| `work_interfere` | TEXT |  |
| `no_employees` | TEXT |  |
| `remote_work` | INTEGER |  |
| `tech_company` | INTEGER |  |
| `benefits` | TEXT |  |
| `care_options` | TEXT |  |
| `wellness_program` | TEXT |  |
| `seek_help` | TEXT |  |
| `anonymity` | TEXT |  |
| `leave_difficulty` | TEXT |  |
| `mental_health_consequence` | TEXT |  |
| `phys_health_consequence` | TEXT |  |
| `coworkers` | TEXT |  |
| `supervisor` | TEXT |  |
| `mental_health_interview` | TEXT |  |
| `phys_health_interview` | TEXT |  |
| `mental_vs_physical` | TEXT |  |
| `obs_consequence` | INTEGER |  |
| `comments` | TEXT |  |

---

## vw_country_prevalence_pivot
**Rows:** 6420

| Column | Type | PK |
|---|---|---|
| `country_name` | TEXT |  |
| `country_code` | TEXT |  |
| `year` | INTEGER |  |
| `schizophrenia_pct` | ANY |  |
| `depression_pct` | ANY |  |
| `anxiety_pct` | ANY |  |
| `bipolar_pct` | ANY |  |
| `eating_disorder_pct` | ANY |  |

---

## vw_unified_individual_mental_health
**Rows:** 40261

| Column | Type | PK |
|---|---|---|
| `source_name` | ANY |  |
| `record_id` | INTEGER |  |
| `age` | REAL |  |
| `gender` | TEXT |  |
| `country` | TEXT |  |
| `location` | TEXT |  |
| `population_type` | TEXT |  |
| `depression_flag` | INTEGER |  |
| `anxiety_flag` | INT |  |
| `treatment_flag` | INT |  |
| `sleep_hours` | REAL |  |
| `stress_score` | REAL |  |
| `social_support_score` | INT |  |
| `depression_score` | INT |  |
| `anxiety_score` | INT |  |
| `productivity_score` | REAL |  |
| `cgpa_10` | REAL |  |
| `exam_score` | REAL |  |
| `study_hours_per_day` | REAL |  |
| `work_study_hours` | REAL |  |
| `physical_activity_days` | INT |  |
| `family_history_flag` | INTEGER |  |

---

## vw_student_dashboard
**Rows:** 28901

| Column | Type | PK |
|---|---|---|
| `source_name` | ANY |  |
| `record_id` | INTEGER |  |
| `age` | REAL |  |
| `gender` | TEXT |  |
| `city` | TEXT |  |
| `degree` | TEXT |  |
| `depression_flag` | INTEGER |  |
| `academic_pressure` | REAL |  |
| `cgpa_10` | REAL |  |
| `sleep_hours` | REAL |  |
| `dietary_habits` | TEXT |  |
| `suicidal_thoughts` | INTEGER |  |
| `family_history_mental_illness` | INTEGER |  |
| `exam_score` | REAL |  |
| `attendance_percentage` | REAL |  |
| `social_media_hours` | REAL |  |
| `netflix_hours` | REAL |  |
| `mental_health_rating` | INT |  |

---
