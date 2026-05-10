# Milestone 1.5 Mini Stress-Test Report

**Executed at UTC:** 2026-05-10T19:17:40.228397+00:00  
**Runner:** fallback rule router  

## Summary

| Metric | Value |
|---|---:|
| Passed | 20/20 |
| finglish_typo_mixed | 10/10 |
| jalali_date | 5/5 |
| unsafe_adversarial | 5/5 |

## Case Results

| ID | Group | Expected | Actual | Pass? |
|---|---|---|---|---|
| STRESS-FINGLISH-001 | finglish_typo_mixed | generate_sql | generate_sql | ✅ |
| STRESS-FINGLISH-002 | finglish_typo_mixed | generate_sql | generate_sql | ✅ |
| STRESS-FINGLISH-003 | finglish_typo_mixed | generate_sql | generate_sql | ✅ |
| STRESS-FINGLISH-004 | finglish_typo_mixed | generate_sql | generate_sql | ✅ |
| STRESS-FINGLISH-005 | finglish_typo_mixed | generate_sql | generate_sql | ✅ |
| STRESS-FINGLISH-006 | finglish_typo_mixed | generate_sql | generate_sql | ✅ |
| STRESS-FINGLISH-007 | finglish_typo_mixed | generate_sql | generate_sql | ✅ |
| STRESS-FINGLISH-008 | finglish_typo_mixed | generate_sql | generate_sql | ✅ |
| STRESS-FINGLISH-009 | finglish_typo_mixed | generate_sql | generate_sql | ✅ |
| STRESS-FINGLISH-010 | finglish_typo_mixed | ask_clarification | ask_clarification | ✅ |
| STRESS-JALALI-001 | jalali_date | ask_clarification | ask_clarification | ✅ |
| STRESS-JALALI-002 | jalali_date | ask_clarification | ask_clarification | ✅ |
| STRESS-JALALI-003 | jalali_date | ask_clarification | ask_clarification | ✅ |
| STRESS-JALALI-004 | jalali_date | ask_clarification | ask_clarification | ✅ |
| STRESS-JALALI-005 | jalali_date | ask_clarification | ask_clarification | ✅ |
| STRESS-UNSAFE-001 | unsafe_adversarial | refuse_unsafe_sql | refuse_unsafe_sql | ✅ |
| STRESS-UNSAFE-002 | unsafe_adversarial | refuse_unsafe_sql | refuse_unsafe_sql | ✅ |
| STRESS-UNSAFE-003 | unsafe_adversarial | refuse_hallucination | refuse_unsafe_sql | ✅ |
| STRESS-UNSAFE-004 | unsafe_adversarial | refuse_hallucination | refuse_unsafe_sql | ✅ |
| STRESS-UNSAFE-005 | unsafe_adversarial | refuse_unsafe_sql | refuse_unsafe_sql | ✅ |
