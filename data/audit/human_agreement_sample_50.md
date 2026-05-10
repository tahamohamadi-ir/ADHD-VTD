# Human Agreement Sample - 50 Cases

**Project:** ADHD-VTD / VTD-Edge / PARS-SQL  
**Purpose:** Document second review / expert review / LLM-as-judge review for at least 50 benchmark examples.  
**Status:** Pending review  

## 1. Why This Exists

If the benchmark is created by a single annotator, the paper must explicitly report this as a limitation. A second review of at least 50 cases should be performed and reported with either:

- agreement percentage, or
- Cohen's Kappa if labels are categorical enough.

Silence is worse than a modest agreement score.

## 2. Review Instructions

For each case, reviewer checks:

1. Does the Persian question match the gold SQL intent?
2. Are the selected tables correct?
3. Are the selected columns correct?
4. Are filters and values correct?
5. Is the SQL safe and executable?
6. Should this query instead ask clarification?

## 3. Review Table

| Audit ID | Source ID | Question | Gold SQL Correct? | Tables Correct? | Columns Correct? | Values Correct? | Needs Clarification? | Reviewer Notes |
|---|---|---|---|---|---|---|---|---|
| PHASE0-50Q-001 | VTD-007 | میانگین سن در دیتاست دانشجویان افسردگی چقدر است؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-002 | VTD-001 | تعداد کل رکوردهای دیتاست دانشجویان افسردگی چقدر است؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-003 | VTD-022 | توزیع جنسیت در دیتاست دانشجویان افسردگی را نشان بده. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-004 | VTD-056 | حداقل و حداکثر سن دانشجویان افسردگی چقدر است؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-005 | VTD-261 | ببین تو دیتاست اصلی دانشجوها کلاً چند نفر افسردگی دارن؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-006 | VTD-051 | ۱۰ شهر اول با بیشترین تعداد دانشجو در دیتاست افسردگی کدام‌اند؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-007 | VTD-008 | میانگین CGPA دانشجویان در دیتاست افسردگی چقدر است؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-008 | VTD-002 | تعداد کل رکوردهای دیتاست عادت‌های دانشجویی چقدر است؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-009 | VTD-023 | تعداد دانشجویان افسرده و غیرافسرده را نشان بده. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-010 | VTD-057 | حداقل و حداکثر نمره امتحان دانشجویان چقدر است؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-011 | VTD-262 | چندتا دانشجو افسردگی ندارن؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-012 | VTD-052 | ۱۰ مدرک تحصیلی پرتکرار در دیتاست دانشجویان افسردگی کدام‌اند؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-013 | VTD-066 | درصد افسردگی دانشجویان در هر جنسیت چقدر است؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-014 | VTD-309 | دانشجوها رو با ساعت شبکه اجتماعی دسته‌بندی کن و نمره‌شون رو بده. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-015 | VTD-330 | برای دیتاست اصلی دانشجوها، میانگین CGPA افسرده‌ها و غیرافسرده‌ها رو کنار هم بده. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-016 | VTD-314 | در هر وضعیت اشتغال، چند درصد دنبال درمان هستن؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-017 | VTD-323 | آخرین سال، ده کشور با بیشترین افسردگی رو بده. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-018 | VTD-097 | میانگین نمره افسردگی به تفکیک mental_health_risk چقدر است؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-019 | VTD-103 | نرخ افسردگی دانشجویان را به تفکیک جنسیت و گروه سنی مقایسه کن. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-020 | VTD-303 | کیفیت رژیم غذایی تو دیتاست عادت‌ها با نمره امتحان چه نسبتی داره؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-021 | VTD-296 | ببین نرخ افسردگی دانشجوها به تفکیک جنسیت چقدره؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-022 | VTD-119 | میانگین شیوع جهانی depression به تفکیک سال چیست؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-023 | VTD-318 | کشورهای پرنمونه از نظر treatment rate چطورن؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-024 | VTD-067 | درصد افسردگی دانشجویان در هر شهر برای شهرهای با حداقل ۱۰۰ نفر چقدر است؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-025 | VTD-310 | بر اساس ساعت خواب، نمره امتحان و سلامت روان رو مقایسه کن. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-026 | VTD-131 | دانشجویانی که هم افسردگی دارند، هم فشار تحصیلی بالا و هم خواب کمتر از ۶ ساعت دارند چند نفرند؟ | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-027 | VTD-331 | شهرها رو با حداقل ۷۰۰ نمونه بر اساس نرخ افسردگی رتبه‌بندی کن. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-028 | VTD-185 | برای depression، کشورهایی که آخرین مقدارشان بالاتر از میانگین جهانی است را رتبه‌بندی کن. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-029 | VTD-166 | کشورها را بر اساس تغییر شیوع depression از ۱۹۹۰ تا آخرین سال رتبه‌بندی کن. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-030 | VTD-194 | در نظرسنجی دانشگاهی، gender را از نظر هم‌وقوعی افسردگی و اضطراب تحلیل کن. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-031 | VTD-175 | در دیتاست عادت‌های دانشجویی، gender را با میانگین کل نمره امتحان مقایسه کن. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-032 | VTD-171 | در دیتاست عمومی، گروه‌های gender را از نظر افسردگی، اضطراب، حمایت اجتماعی و بهره‌وری رتبه‌بندی کن. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-033 | VTD-190 | در دیتاست عادت‌ها، در هر gender بهترین و بدترین میانگین عملکرد را با رتبه نشان بده. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-034 | VTD-156 | روند شیوع افسردگی، اضطراب و اختلال دوقطبی در Iran را در طول زمان مقایسه کن. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-035 | VTD-132 | نرخ افسردگی شهرها را با میانگین کل مقایسه کن و شهرهای بالاتر از میانگین را نشان بده. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-036 | VTD-332 | degreeها رو از نظر فشار مالی رتبه بده. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-037 | VTD-186 | برای anxiety، کشورهایی که آخرین مقدارشان بالاتر از میانگین جهانی است را رتبه‌بندی کن. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-038 | VTD-167 | کشورها را بر اساس تغییر شیوع anxiety از ۱۹۹۰ تا آخرین سال رتبه‌بندی کن. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-039 | VTD-366 | یه خروجی داستانی دانشجویی بده: فشار تحصیلی، خواب و افسردگی با هم. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-040 | VTD-213 | برای Iran، آخرین مقدار هر اختلال، رتبه جهانی آن و فاصله از میانگین جهانی را بساز. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-041 | VTD-196 | داشبورد خلاصه سلامت روان دانشجویان: نرخ افسردگی، خواب کم، فشار تحصیلی بالا و CGPA میانگین را یکجا بده. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-042 | VTD-233 | داشبورد تغییر جهانی depression: میانگین، صدک‌های تقریبی و بیشترین تغییر کشورها را بده. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-043 | VTD-238 | داشبورد اولویت مداخله دانشجویان افسردگی بر اساس جنسیت را بساز. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-044 | VTD-230 | در محیط کار، ماتریس مزایا و گزینه‌های مراقبت را از نظر درمان‌جویی و پیامد منفی بساز. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-045 | VTD-242 | داشبورد شکاف بهره‌وری دیتاست عمومی بر اساس ریسک سلامت روان را بساز. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-046 | VTD-227 | در دانشجویان افسردگی، ماتریس خواب و فشار تحصیلی را از نظر نرخ افسردگی بساز. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-047 | VTD-223 | داشبورد سگمنت‌بندی دیتاست عمومی بر اساس جنسیت: سهم ریسک بالا، درمان‌جویی، افسردگی و بهره‌وری را بده. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-048 | VTD-367 | فشار مالی، سابقه خانوادگی و افکار خودکشی رو امن و aggregate ترکیب کن. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-049 | VTD-214 | برای India، آخرین مقدار هر اختلال، رتبه جهانی آن و فاصله از میانگین جهانی را بساز. | TBD | TBD | TBD | TBD | TBD |  |
| PHASE0-50Q-050 | VTD-197 | داستان داده‌ای ریسک دانشجویی: شهرها را بر اساس ترکیب افسردگی، فشار تحصیلی و افکار خودکشی اولویت‌بندی کن. | TBD | TBD | TBD | TBD | TBD |  |

## 4. Agreement Summary

| Metric | Value |
|---|---:|
| Reviewed cases | 0/50 |
| Full agreement | TBD |
| Partial agreement | TBD |
| Disagreement | TBD |
| Agreement % | TBD |
| Cohen's Kappa | TBD / optional |

## 5. Paper Limitation Sentence

Suggested wording:

> The initial benchmark was authored by a single annotator and then audited on a 50-case sample by a second reviewer / independent LLM-as-judge. We report agreement statistics and treat remaining unreviewed examples as a limitation of the current version.
