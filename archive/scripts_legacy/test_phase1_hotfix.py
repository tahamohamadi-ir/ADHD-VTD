from __future__ import annotations

from _bootstrap_path import PROJECT_ROOT

from src.schema.value_linker import ValueLinker
from src.nlu.number_normalizer import NumberNormalizer


def assert_true(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    print(f"PROJECT_ROOT={PROJECT_ROOT}")

    linker = ValueLinker()
    links = linker.resolve_as_dicts("دانشجویان زن افسرده", ["student_depression.gender", "student_depression.depression_flag"])
    print(links)
    assert_true(any(x["resolved_value"] == "Female" for x in links), "زن must resolve to Female")
    assert_true(any(x["resolved_value"] == 1 for x in links), "افسرده/افسردگی must resolve to depression_flag=1")

    neg_links = linker.resolve_as_dicts("دانشجوهای بدون افسردگی", ["student_depression.depression_flag"])
    print(neg_links)
    assert_true(any(x["resolved_value"] == 0 for x in neg_links), "بدون افسردگی must resolve to depression_flag=0")
    assert_true(not any(x["resolved_value"] == 1 for x in neg_links), "Negative depression phrase must not also emit value=1")

    nums = NumberNormalizer().normalize("یه آمار کلی بده")
    print(nums)
    assert_true(nums.extracted_numbers == [], "Colloquial یه must not be extracted as number 1")

    nums2 = NumberNormalizer().normalize("۱۰ شهر اول")
    print(nums2)
    assert_true(10 in nums2.extracted_numbers, "Persian digits must still normalize/extract")

    print("Phase 1 hotfix checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
