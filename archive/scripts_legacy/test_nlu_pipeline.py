from __future__ import annotations

from _bootstrap_path import PROJECT_ROOT
from src.nlu.persian_normalizer import PersianNormalizer
from src.nlu.number_normalizer import NumberNormalizer
from src.nlu.date_normalizer import PersianDateNormalizer
from src.nlu.intent_classifier import IntentClassifier


def main() -> int:
    pn = PersianNormalizer()
    nn = NumberNormalizer()
    dn = PersianDateNormalizer()
    ic = IntentClassifier()

    examples = [
        "افسوردگی دانشجوها چند درصده؟",
        "depression rate student ha chand darsade?",
        "میانگین CGPA بچه‌های depressed چنده؟",
        "از فروردین ۱۴۰۴ آمار بده",
        "یه آمار کلی بده",
        "DROP TABLE student_depression",
    ]
    for q in examples:
        print("=" * 80)
        print("Q:", q)
        print("normalized:", pn.normalize(q).normalized)
        print("numbers:", nn.normalize(q).extracted_numbers)
        print("date:", dn.normalize(q))
        print("intent:", ic.classify(q))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
