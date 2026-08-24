from __future__ import annotations

from src.schema.value_linker import ValueLinker


def test_disorder_alias_does_not_match_metric_column_names():
    links = ValueLinker().resolve_for_column(
        "depression",
        "country_prevalence_wide.eating_disorder_pct",
    )

    assert links == []


def test_dataset_depression_mention_does_not_create_positive_flag_filter():
    question = (
        "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 \u0633\u0646 \u062f\u0631 "
        "\u062f\u06cc\u062a\u0627\u0633\u062a \u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u0627\u0646 "
        "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
    )

    links = ValueLinker().resolve_for_column(
        question,
        "student_depression.depression_flag",
    )

    assert links == []


def test_explicit_depression_condition_still_links_positive_flag():
    question = (
        "\u062f\u0631\u0635\u062f \u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u0627\u0646\u06cc "
        "\u06a9\u0647 \u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u062f\u0627\u0631\u0646\u062f "
        "\u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
    )

    links = ValueLinker().resolve_for_column(
        question,
        "student_depression.depression_flag",
    )

    assert links
    assert links[0].resolved_value == 1
