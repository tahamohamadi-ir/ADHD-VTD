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
