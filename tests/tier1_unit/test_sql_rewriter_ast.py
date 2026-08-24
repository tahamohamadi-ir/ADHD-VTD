from src.sql_validation.sql_rewriter import SQLRewriter


class TestSQLRewriterAST:
    def test_strip_fences(self):
        rewriter = SQLRewriter()
        sql = "```sql\nSELECT * FROM t;\n```"
        assert rewriter.rewrite(sql, add_limit=False) == "SELECT * FROM t"

    def test_fix_gpa(self):
        rewriter = SQLRewriter()
        sql = "SELECT gpa FROM student_depression"
        rewritten = rewriter.rewrite(sql, add_limit=False)
        assert "cgpa" in rewritten.lower()
        assert "gpa" not in rewritten.lower().replace("cgpa", "")

    def test_fix_student_family_history_alias(self):
        rewriter = SQLRewriter()
        sql = "SELECT family_history, COUNT(*) FROM student_depression GROUP BY family_history"
        rewritten = rewriter.rewrite(sql, add_limit=False)
        assert "family_history_mental_illness" in rewritten.lower()
        assert " family_history," not in rewritten.lower()

    def test_keep_workplace_family_history_column(self):
        rewriter = SQLRewriter()
        sql = "SELECT family_history, COUNT(*) FROM workplace_mental_health_survey GROUP BY family_history"
        rewritten = rewriter.rewrite(sql, add_limit=False)
        assert "family_history_mental_illness" not in rewritten.lower()
        assert "family_history" in rewritten.lower()

    def test_ensure_limit(self):
        rewriter = SQLRewriter()
        sql = "SELECT * FROM student_depression"
        rewritten = rewriter.rewrite(sql, add_limit=True)
        assert "LIMIT 100" in rewritten.upper()

    def test_no_limit_on_group(self):
        rewriter = SQLRewriter()
        sql = "SELECT gender FROM student_depression GROUP BY gender"
        rewritten = rewriter.rewrite(sql, add_limit=True)
        assert "LIMIT" not in rewritten.upper()

    def test_no_limit_on_agg(self):
        rewriter = SQLRewriter()
        sql = "SELECT COUNT(*) FROM student_depression"
        rewritten = rewriter.rewrite(sql, add_limit=True)
        assert "LIMIT" not in rewritten.upper()

    def test_rounds_avg_projection(self):
        rewriter = SQLRewriter()
        sql = "SELECT AVG(age) AS avg_age FROM student_depression"
        rewritten = rewriter.rewrite(sql, add_limit=False)
        assert "ROUND(AVG(age), 2) AS avg_age" in rewritten

    def test_rounds_percentage_ratio_projection(self):
        rewriter = SQLRewriter()
        sql = "SELECT 100.0 * SUM(depression_flag) / COUNT(*) AS depression_rate_pct FROM student_depression"
        rewritten = rewriter.rewrite(sql, add_limit=False)
        assert (
            "ROUND(100.0 * SUM(depression_flag) / COUNT(*), 2) AS depression_rate_pct" in rewritten
        )

    def test_keeps_existing_round_projection(self):
        rewriter = SQLRewriter()
        sql = "SELECT ROUND(AVG(age), 2) AS avg_age FROM student_depression"
        rewritten = rewriter.rewrite(sql, add_limit=False)
        assert rewritten.count("ROUND(") == 1

    def test_does_not_round_window_rank_projection(self):
        rewriter = SQLRewriter()
        sql = (
            "SELECT gender, RANK() OVER (ORDER BY AVG(depression_score) DESC) AS rank_by_depression "
            "FROM mental_health_general GROUP BY gender"
        )
        rewritten = rewriter.rewrite(sql, add_limit=False)
        assert "ROUND(RANK()" not in rewritten
        assert "RANK() OVER" in rewritten

    def test_does_not_round_inner_cte_aggregate(self):
        rewriter = SQLRewriter()
        sql = (
            "WITH grouped AS (SELECT gender, AVG(cgpa_10) AS avg_cgpa FROM student_depression GROUP BY gender) "
            "SELECT gender, ROUND(avg_cgpa, 2) AS avg_cgpa FROM grouped"
        )
        rewritten = rewriter.rewrite(sql, add_limit=False)
        assert "AVG(cgpa_10) AS avg_cgpa" in rewritten
        assert "ROUND(AVG(cgpa_10)" not in rewritten

    def test_question_rewrite_removes_dataset_name_depression_filter(self):
        rewriter = SQLRewriter()
        sql = (
            "SELECT AVG(age) FROM student_depression WHERE depression_flag = 1 AND age IS NOT NULL"
        )
        rewritten = rewriter.rewrite_for_question(
            sql,
            question=(
                "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 \u0633\u0646 \u062f\u0631 "
                "\u062f\u06cc\u062a\u0627\u0633\u062a \u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u0627\u0646 "
                "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
            ),
            add_limit=False,
        )
        assert "depression_flag" not in rewritten
        assert "age IS NULL" in rewritten

    def test_question_rewrite_keeps_explicit_depressed_filter(self):
        rewriter = SQLRewriter()
        sql = (
            "SELECT AVG(age) FROM student_depression WHERE depression_flag = 1 AND age IS NOT NULL"
        )
        rewritten = rewriter.rewrite_for_question(
            sql,
            question=(
                "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 \u0633\u0646 \u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u0627\u0646\u06cc "
                "\u06a9\u0647 \u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u062f\u0627\u0631\u0646\u062f \u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
            ),
            add_limit=False,
        )
        assert "depression_flag = 1" in rewritten

    def test_question_rewrite_removes_spurious_global_total_filters(self):
        rewriter = SQLRewriter()
        sql = "SELECT COUNT(*) AS record_count FROM country_prevalence_long WHERE country_name = 'Iran' LIMIT 100"
        rewritten = rewriter.rewrite_for_question(
            sql,
            question=(
                "\u062a\u0639\u062f\u0627\u062f \u06a9\u0644 \u0631\u06a9\u0648\u0631\u062f\u0647\u0627\u06cc "
                "\u0634\u06cc\u0648\u0639 \u062c\u0647\u0627\u0646\u06cc \u0633\u0644\u0627\u0645\u062a "
                "\u0631\u0648\u0627\u0646 \u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
            ),
            add_limit=False,
        )
        assert rewritten == "SELECT COUNT(*) AS record_count FROM country_prevalence_long"

    def test_question_rewrite_keeps_named_global_country_filter(self):
        rewriter = SQLRewriter()
        sql = "SELECT COUNT(*) AS record_count FROM country_prevalence_long WHERE country_name = 'Iran'"
        rewritten = rewriter.rewrite_for_question(
            sql,
            question=(
                "\u062a\u0639\u062f\u0627\u062f \u0631\u06a9\u0648\u0631\u062f\u0647\u0627\u06cc "
                "\u0634\u06cc\u0648\u0639 \u062c\u0647\u0627\u0646\u06cc \u0628\u0631\u0627\u06cc Iran "
                "\u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
            ),
            add_limit=False,
        )
        assert "country_name = 'Iran'" in rewritten
