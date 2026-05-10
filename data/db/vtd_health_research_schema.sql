PRAGMA foreign_keys = ON;

CREATE TABLE dim_source (
    source_id INTEGER PRIMARY KEY,
    source_name TEXT NOT NULL UNIQUE,
    file_name TEXT NOT NULL,
    description TEXT,
    row_count INTEGER NOT NULL
);

CREATE TABLE country_prevalence_wide (
    prevalence_row_id INTEGER PRIMARY KEY,
    country_name TEXT NOT NULL,
    country_code TEXT,
    year INTEGER NOT NULL,
    is_country_like INTEGER NOT NULL DEFAULT 1,
    schizophrenia_pct REAL,
    depression_pct REAL,
    anxiety_pct REAL,
    bipolar_pct REAL,
    eating_disorder_pct REAL,
    UNIQUE(country_name, year)
);

CREATE TABLE country_prevalence_long (
    prevalence_id INTEGER PRIMARY KEY,
    country_name TEXT NOT NULL,
    country_code TEXT,
    year INTEGER NOT NULL,
    is_country_like INTEGER NOT NULL DEFAULT 1,
    disorder TEXT NOT NULL CHECK (disorder IN ('schizophrenia','depression','anxiety','bipolar','eating_disorder')),
    prevalence_pct REAL NOT NULL,
    UNIQUE(country_name, year, disorder)
);

CREATE TABLE student_depression (
    student_depression_id INTEGER PRIMARY KEY,
    source_row_id INTEGER UNIQUE,
    gender TEXT,
    age REAL,
    city TEXT,
    country TEXT DEFAULT 'India',
    profession TEXT,
    academic_pressure REAL,
    work_pressure REAL,
    cgpa_10 REAL,
    study_satisfaction REAL,
    job_satisfaction REAL,
    sleep_duration_category TEXT,
    dietary_habits TEXT,
    degree TEXT,
    suicidal_thoughts INTEGER CHECK (suicidal_thoughts IN (0,1) OR suicidal_thoughts IS NULL),
    work_study_hours REAL,
    financial_stress REAL,
    family_history_mental_illness INTEGER CHECK (family_history_mental_illness IN (0,1) OR family_history_mental_illness IS NULL),
    depression_flag INTEGER CHECK (depression_flag IN (0,1) OR depression_flag IS NULL),
    sleep_mid_hours REAL
);

CREATE TABLE student_habits_performance (
    habit_row_id INTEGER PRIMARY KEY,
    original_student_id TEXT UNIQUE,
    age INTEGER,
    gender TEXT,
    study_hours_per_day REAL,
    social_media_hours REAL,
    netflix_hours REAL,
    part_time_job INTEGER CHECK (part_time_job IN (0,1) OR part_time_job IS NULL),
    attendance_percentage REAL,
    sleep_hours REAL,
    diet_quality TEXT,
    exercise_frequency INTEGER,
    parental_education_level TEXT,
    internet_quality TEXT,
    mental_health_rating INTEGER,
    extracurricular_participation INTEGER CHECK (extracurricular_participation IN (0,1) OR extracurricular_participation IS NULL),
    exam_score REAL
);

CREATE TABLE mental_health_general (
    general_row_id INTEGER PRIMARY KEY,
    age INTEGER,
    gender TEXT,
    employment_status TEXT,
    work_environment TEXT,
    mental_health_history INTEGER CHECK (mental_health_history IN (0,1) OR mental_health_history IS NULL),
    seeks_treatment INTEGER CHECK (seeks_treatment IN (0,1) OR seeks_treatment IS NULL),
    stress_level INTEGER,
    sleep_hours REAL,
    physical_activity_days INTEGER,
    depression_score INTEGER,
    anxiety_score INTEGER,
    social_support_score INTEGER,
    productivity_score REAL,
    mental_health_risk TEXT
);

CREATE TABLE university_student_mental_health (
    university_row_id INTEGER PRIMARY KEY,
    survey_timestamp TEXT,
    age REAL,
    gender TEXT,
    course TEXT,
    year_of_study INTEGER,
    cgpa_range TEXT,
    cgpa_mid REAL,
    marital_status INTEGER CHECK (marital_status IN (0,1) OR marital_status IS NULL),
    depression_diagnosis INTEGER CHECK (depression_diagnosis IN (0,1) OR depression_diagnosis IS NULL),
    anxiety_diagnosis INTEGER CHECK (anxiety_diagnosis IN (0,1) OR anxiety_diagnosis IS NULL),
    panic_attack INTEGER CHECK (panic_attack IN (0,1) OR panic_attack IS NULL),
    treatment_seeking INTEGER CHECK (treatment_seeking IN (0,1) OR treatment_seeking IS NULL)
);

CREATE TABLE workplace_mental_health_survey (
    workplace_row_id INTEGER PRIMARY KEY,
    survey_timestamp TEXT,
    survey_year INTEGER,
    age_raw REAL,
    age REAL,
    gender_raw TEXT,
    gender TEXT,
    country TEXT,
    state TEXT,
    self_employed INTEGER CHECK (self_employed IN (0,1) OR self_employed IS NULL),
    family_history INTEGER CHECK (family_history IN (0,1) OR family_history IS NULL),
    treatment INTEGER CHECK (treatment IN (0,1) OR treatment IS NULL),
    work_interfere TEXT,
    no_employees TEXT,
    remote_work INTEGER CHECK (remote_work IN (0,1) OR remote_work IS NULL),
    tech_company INTEGER CHECK (tech_company IN (0,1) OR tech_company IS NULL),
    benefits TEXT,
    care_options TEXT,
    wellness_program TEXT,
    seek_help TEXT,
    anonymity TEXT,
    leave_difficulty TEXT,
    mental_health_consequence TEXT,
    phys_health_consequence TEXT,
    coworkers TEXT,
    supervisor TEXT,
    mental_health_interview TEXT,
    phys_health_interview TEXT,
    mental_vs_physical TEXT,
    obs_consequence INTEGER CHECK (obs_consequence IN (0,1) OR obs_consequence IS NULL),
    comments TEXT
);

CREATE INDEX idx_country_prevalence_long_country_year ON country_prevalence_long(country_name, year);
CREATE INDEX idx_country_prevalence_long_disorder_year ON country_prevalence_long(disorder, year);
CREATE INDEX idx_student_depression_city ON student_depression(city);
CREATE INDEX idx_student_depression_gender ON student_depression(gender);
CREATE INDEX idx_student_depression_depression ON student_depression(depression_flag);
CREATE INDEX idx_student_habits_gender ON student_habits_performance(gender);
CREATE INDEX idx_general_risk ON mental_health_general(mental_health_risk);
CREATE INDEX idx_general_gender ON mental_health_general(gender);
CREATE INDEX idx_workplace_country_year ON workplace_mental_health_survey(country, survey_year);
CREATE INDEX idx_workplace_gender ON workplace_mental_health_survey(gender);
CREATE INDEX idx_university_course ON university_student_mental_health(course);

CREATE VIEW vw_country_prevalence_pivot AS
SELECT
    country_name,
    country_code,
    year,
    MAX(CASE WHEN disorder = 'schizophrenia' THEN prevalence_pct END) AS schizophrenia_pct,
    MAX(CASE WHEN disorder = 'depression' THEN prevalence_pct END) AS depression_pct,
    MAX(CASE WHEN disorder = 'anxiety' THEN prevalence_pct END) AS anxiety_pct,
    MAX(CASE WHEN disorder = 'bipolar' THEN prevalence_pct END) AS bipolar_pct,
    MAX(CASE WHEN disorder = 'eating_disorder' THEN prevalence_pct END) AS eating_disorder_pct
FROM country_prevalence_long
GROUP BY country_name, country_code, year;

CREATE VIEW vw_unified_individual_mental_health AS
SELECT
    'student_depression' AS source_name,
    student_depression_id AS record_id,
    age,
    gender,
    country,
    city AS location,
    'Student' AS population_type,
    depression_flag AS depression_flag,
    NULL AS anxiety_flag,
    NULL AS treatment_flag,
    sleep_mid_hours AS sleep_hours,
    academic_pressure AS stress_score,
    NULL AS social_support_score,
    NULL AS depression_score,
    NULL AS anxiety_score,
    NULL AS productivity_score,
    cgpa_10 AS cgpa_10,
    NULL AS exam_score,
    NULL AS study_hours_per_day,
    work_study_hours AS work_study_hours,
    NULL AS physical_activity_days,
    family_history_mental_illness AS family_history_flag
FROM student_depression
UNION ALL
SELECT
    'student_habits' AS source_name,
    habit_row_id AS record_id,
    age,
    gender,
    NULL AS country,
    NULL AS location,
    'Student' AS population_type,
    NULL AS depression_flag,
    NULL AS anxiety_flag,
    NULL AS treatment_flag,
    sleep_hours,
    NULL AS stress_score,
    NULL AS social_support_score,
    NULL AS depression_score,
    NULL AS anxiety_score,
    NULL AS productivity_score,
    NULL AS cgpa_10,
    exam_score,
    study_hours_per_day,
    NULL AS work_study_hours,
    exercise_frequency AS physical_activity_days,
    NULL AS family_history_flag
FROM student_habits_performance
UNION ALL
SELECT
    'mental_health_general' AS source_name,
    general_row_id AS record_id,
    age,
    gender,
    NULL AS country,
    NULL AS location,
    employment_status AS population_type,
    CASE WHEN depression_score >= 20 THEN 1 WHEN depression_score IS NOT NULL THEN 0 END AS depression_flag,
    CASE WHEN anxiety_score >= 15 THEN 1 WHEN anxiety_score IS NOT NULL THEN 0 END AS anxiety_flag,
    seeks_treatment AS treatment_flag,
    sleep_hours,
    stress_level AS stress_score,
    social_support_score,
    depression_score,
    anxiety_score,
    productivity_score,
    NULL AS cgpa_10,
    NULL AS exam_score,
    NULL AS study_hours_per_day,
    NULL AS work_study_hours,
    physical_activity_days,
    mental_health_history AS family_history_flag
FROM mental_health_general
UNION ALL
SELECT
    'university_student_survey' AS source_name,
    university_row_id AS record_id,
    age,
    gender,
    NULL AS country,
    course AS location,
    'University Student' AS population_type,
    depression_diagnosis AS depression_flag,
    anxiety_diagnosis AS anxiety_flag,
    treatment_seeking AS treatment_flag,
    NULL AS sleep_hours,
    NULL AS stress_score,
    NULL AS social_support_score,
    NULL AS depression_score,
    NULL AS anxiety_score,
    NULL AS productivity_score,
    cgpa_mid * 2.5 AS cgpa_10,
    NULL AS exam_score,
    NULL AS study_hours_per_day,
    NULL AS work_study_hours,
    NULL AS physical_activity_days,
    NULL AS family_history_flag
FROM university_student_mental_health
UNION ALL
SELECT
    'workplace_survey' AS source_name,
    workplace_row_id AS record_id,
    age,
    gender,
    country,
    state AS location,
    'Workplace/Tech' AS population_type,
    NULL AS depression_flag,
    NULL AS anxiety_flag,
    treatment AS treatment_flag,
    NULL AS sleep_hours,
    NULL AS stress_score,
    NULL AS social_support_score,
    NULL AS depression_score,
    NULL AS anxiety_score,
    NULL AS productivity_score,
    NULL AS cgpa_10,
    NULL AS exam_score,
    NULL AS study_hours_per_day,
    NULL AS work_study_hours,
    NULL AS physical_activity_days,
    family_history AS family_history_flag
FROM workplace_mental_health_survey;

CREATE VIEW vw_student_dashboard AS
SELECT
    'student_depression' AS source_name,
    student_depression_id AS record_id,
    age,
    gender,
    city,
    degree,
    depression_flag,
    academic_pressure,
    cgpa_10,
    sleep_mid_hours AS sleep_hours,
    dietary_habits,
    suicidal_thoughts,
    family_history_mental_illness,
    NULL AS exam_score,
    NULL AS attendance_percentage,
    NULL AS social_media_hours,
    NULL AS netflix_hours,
    NULL AS mental_health_rating
FROM student_depression
UNION ALL
SELECT
    'student_habits' AS source_name,
    habit_row_id AS record_id,
    age,
    gender,
    NULL AS city,
    NULL AS degree,
    NULL AS depression_flag,
    NULL AS academic_pressure,
    NULL AS cgpa_10,
    sleep_hours,
    diet_quality AS dietary_habits,
    NULL AS suicidal_thoughts,
    NULL AS family_history_mental_illness,
    exam_score,
    attendance_percentage,
    social_media_hours,
    netflix_hours,
    mental_health_rating
FROM student_habits_performance;
