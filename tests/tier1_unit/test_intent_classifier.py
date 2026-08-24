from __future__ import annotations

from src.core.enums import ExpectedAction, IntentLabel
from src.nlu.intent_classifier import IntentClassifier


def test_dashboard_country_disorder_question_generates_sql():
    question = (
        "\u062f\u0627\u0634\u0628\u0648\u0631\u062f "
        "\u062a\u063a\u06cc\u06cc\u0631 \u062c\u0647\u0627\u0646\u06cc eating_disorder: "
        "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646\u060c \u0635\u062f\u06a9\u200c\u0647\u0627 "
        "\u0648 \u0628\u06cc\u0634\u062a\u0631\u06cc\u0646 \u062a\u063a\u06cc\u06cc\u0631 "
        "\u06a9\u0634\u0648\u0631\u0647\u0627 \u0631\u0627 \u0628\u062f\u0647."
    )

    decision = IntentClassifier().classify(question)

    assert decision.intent == IntentLabel.GROUPING_QUERY
    assert decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.GENERATE_SQL


def test_matrix_build_request_is_safe_sql_capable_not_unsafe():
    question = (
        "\u0645\u0627\u062a\u0631\u06cc\u0633 \u062e\u0648\u0627\u0628 \u0648 "
        "\u0631\u0698\u06cc\u0645 \u063a\u0630\u0627\u06cc\u06cc \u0628\u0631\u0627\u06cc "
        "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u0648 CGPA \u0628\u0633\u0627\u0632."
    )

    decision = IntentClassifier().classify(question)

    assert decision.intent == IntentLabel.GROUPING_QUERY
    assert decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.GENERATE_SQL


def test_trend_country_disorder_question_does_not_ask_clarification():
    question = (
        "\u0631\u0648\u0646\u062f \u0634\u06cc\u0648\u0639 "
        "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u0627\u06cc\u0631\u0627\u0646 "
        "\u062f\u0631 \u0633\u0627\u0644\u200c\u0647\u0627 \u0631\u0627 \u0628\u062f\u0647."
    )

    decision = IntentClassifier().classify(question)

    assert decision.intent == IntentLabel.TREND_QUERY
    assert decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.GENERATE_SQL


def test_rank_by_group_question_does_not_ask_clarification():
    question = (
        "\u0631\u062a\u0628\u0647\u200c\u0628\u0646\u062f\u06cc "
        "diet_quality \u0628\u0631 \u0627\u0633\u0627\u0633 "
        "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 exam_score \u0631\u0627 \u0628\u062f\u0647."
    )

    decision = IntentClassifier().classify(question)

    assert decision.intent == IntentLabel.RANKING_QUERY
    assert decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.GENERATE_SQL


def test_country_benchmark_dashboard_question_does_not_ask_clarification():
    question = (
        "\u062f\u0627\u0634\u0628\u0648\u0631\u062f \u0645\u0642\u0627\u06cc\u0633\u0647 "
        "\u06a9\u0634\u0648\u0631\u0647\u0627 \u0628\u0631\u0627\u06cc anxiety: "
        "\u0622\u062e\u0631\u06cc\u0646 \u0633\u0627\u0644\u060c \u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 "
        "\u0648 \u0628\u06cc\u0634\u062a\u0631\u06cc\u0646 \u0634\u06cc\u0648\u0639."
    )

    decision = IntentClassifier().classify(question)

    assert decision.intent == IntentLabel.COMPARISON_QUERY
    assert decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.GENERATE_SQL


def test_low_sample_exclusion_question_is_safe_sql_capable():
    question = (
        "\u0646\u0631\u062e \u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u0634\u0647\u0631\u0647\u0627 "
        "\u0631\u0627 \u0628\u062f\u0647 \u0648 \u0634\u0647\u0631\u0647\u0627\u06cc "
        "\u06a9\u0645\u200c\u0646\u0645\u0648\u0646\u0647 \u0631\u0627 \u062d\u0630\u0641 \u06a9\u0646."
    )

    decision = IntentClassifier().classify(question)

    assert decision.intent == IntentLabel.RATE_QUERY
    assert decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.GENERATE_SQL


def test_workplace_conflict_analysis_does_not_ask_clarification():
    question = (
        "\u062f\u0631 \u0646\u0638\u0631\u0633\u0646\u062c\u06cc "
        "\u0645\u062d\u06cc\u0637 \u06a9\u0627\u0631\u060c \u062a\u0636\u0627\u062f "
        "\u0628\u06cc\u0646 \u0622\u0645\u0627\u062f\u06af\u06cc \u0633\u0627\u0632\u0645\u0627\u0646\u06cc "
        "\u0648 \u062a\u0631\u0633 \u0627\u0632 \u0645\u0635\u0627\u062d\u0628\u0647 "
        "\u0633\u0644\u0627\u0645\u062a \u0631\u0648\u0627\u0646 \u0631\u0627 \u062a\u062d\u0644\u06cc\u0644 \u06a9\u0646."
    )

    decision = IntentClassifier().classify(question)

    assert decision.intent == IntentLabel.COMPARISON_QUERY
    assert decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.GENERATE_SQL


def test_family_history_student_count_does_not_ask_clarification():
    question = (
        "\u0686\u0646\u062f \u0646\u0641\u0631 \u062a\u0648 "
        "\u062f\u06cc\u062a\u0627\u0633\u062a \u062f\u0627\u0646\u0634\u062c\u0648\u0647\u0627 "
        "\u0633\u0627\u0628\u0642\u0647 \u062e\u0627\u0646\u0648\u0627\u062f\u06af\u06cc "
        "\u0645\u0634\u06a9\u0644 \u0631\u0648\u0627\u0646 \u062f\u0627\u0631\u0646\u061f"
    )

    decision = IntentClassifier().classify(question)

    assert decision.intent == IntentLabel.COUNT_QUERY
    assert decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.GENERATE_SQL


def test_latest_year_all_disorders_question_generates_sql():
    question = (
        "\u0628\u0631\u0627\u06cc \u0627\u06cc\u0631\u0627\u0646 \u062a\u0648 "
        "\u0622\u062e\u0631\u06cc\u0646 \u0633\u0627\u0644\u060c "
        "\u0647\u0645\u0647 \u0627\u062e\u062a\u0644\u0627\u0644\u200c\u0647\u0627 "
        "\u0631\u0648 \u06a9\u0646\u0627\u0631 \u0647\u0645 \u0628\u062f\u0647."
    )

    decision = IntentClassifier().classify(question)

    assert decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.GENERATE_SQL


def test_latest_year_country_rank_prefers_ranking_over_trend():
    question = (
        "\u0631\u062a\u0628\u0647 \u0627\u06cc\u0631\u0627\u0646 "
        "\u0628\u0631\u0627\u06cc \u0647\u0631 \u0627\u062e\u062a\u0644\u0627\u0644 "
        "\u062a\u0648 \u0622\u062e\u0631\u06cc\u0646 \u0633\u0627\u0644 \u0686\u0646\u062f\u0647\u061f"
    )

    decision = IntentClassifier().classify(question)

    assert decision.intent == IntentLabel.RANKING_QUERY
    assert decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.GENERATE_SQL


def test_privacy_request_is_unsafe_with_privacy_label():
    question = (
        "\u0628\u0631\u0627\u06cc user\u0647\u0627\u06cc "
        "\u0627\u0641\u0633\u0631\u062f\u0647 \u0627\u0633\u0645 \u0648 "
        "\u0645\u0634\u062e\u0635\u0627\u062a \u0641\u0631\u062f\u06cc \u0628\u062f\u0647."
    )

    decision = IntentClassifier().classify(question)

    assert decision.intent == IntentLabel.UNSAFE_QUERY
    assert not decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.REFUSE_UNSAFE_SQL
    assert decision.safety_label == "privacy_risk"


def test_dashboard_explanation_advice_answers_without_sql():
    question = (
        "\u0627\u06cc\u0646 \u062f\u0627\u0634\u0628\u0648\u0631\u062f "
        "\u0631\u0648 \u0686\u0637\u0648\u0631 \u0628\u0631\u0627\u06cc "
        "\u0645\u062f\u06cc\u0631 \u062a\u0648\u0636\u06cc\u062d \u0628\u062f\u0645\u061f"
    )

    decision = IntentClassifier().classify(question)

    assert not decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.ANSWER_WITHOUT_SQL


def test_nl2sql_evaluation_advice_answers_without_sql():
    question = (
        "\u0628\u0631\u0627\u06cc \u0627\u06cc\u0646 "
        "\u067e\u0631\u0648\u0698\u0647 \u0645\u0639\u06cc\u0627\u0631\u0647\u0627\u06cc "
        "evaluation \u0645\u062f\u0644 NL2SQL \u0631\u0648 "
        "\u062a\u0648\u0636\u06cc\u062d \u0628\u062f\u0647."
    )

    decision = IntentClassifier().classify(question)

    assert not decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.ANSWER_WITHOUT_SQL


def test_chart_visual_advice_answers_chart_recommendation():
    question = (
        "\u0628\u0631\u0627\u06cc z-score "
        "\u0634\u0647\u0631\u0647\u0627\u06cc \u067e\u0631\u0631\u06cc\u0633\u06a9 "
        "\u0686\u0647 visual \u0628\u0647\u062a\u0631\u0647\u061f"
    )

    decision = IntentClassifier().classify(question)

    assert not decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.ANSWER_CHART_RECOMMENDATION


def test_behavior_ambiguous_patterns_ask_clarification():
    questions = [
        "\u062f\u0627\u0646\u0634\u062c\u0648\u0647\u0627\u06cc \u0628\u062f \u0631\u0648 \u067e\u06cc\u062f\u0627 \u06a9\u0646.",
        "\u0627\u062b\u0631 \u0647\u0645\u0632\u0645\u0627\u0646 \u0686\u0646\u062f \u0639\u0627\u0645\u0644 \u0631\u0648\u06cc \u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u0631\u0648 \u062a\u062d\u0644\u06cc\u0644 \u06a9\u0646.",
        "\u062f\u0627\u062f\u0647\u200c\u0647\u0627 \u0631\u0648 \u0637\u0648\u0631\u06cc normalize \u06a9\u0646 \u06a9\u0647 \u0647\u0645\u0647 \u0645\u0646\u0627\u0628\u0639 \u0642\u0627\u0628\u0644 \u0645\u0642\u0627\u06cc\u0633\u0647 \u0628\u0634\u0646.",
        "\u06cc\u0647 dashboard \u06a9\u0627\u0645\u0644 \u0628\u0633\u0627\u0632 \u06a9\u0647 \u0639\u0644\u062a \u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u0631\u0648 \u062b\u0627\u0628\u062a \u06a9\u0646\u0647.",
        "\u0628\u0631\u0627\u06cc \u0645\u0642\u0627\u0644\u0647\u060c \u0628\u0647\u062a\u0631\u06cc\u0646 \u0646\u062a\u06cc\u062c\u0647 \u0639\u0644\u0645\u06cc \u0631\u0648 \u0627\u0632 \u062f\u0627\u062f\u0647\u200c\u0647\u0627 \u0627\u0633\u062a\u062e\u0631\u0627\u062c \u06a9\u0646.",
        "\u062f\u0627\u062f\u0647 \u067e\u0631\u062a\u200c\u0647\u0627 \u0631\u0648 \u062d\u0630\u0641 \u06a9\u0646 \u0648 \u0646\u062a\u06cc\u062c\u0647 \u0631\u0648 \u0628\u062f\u0647.",
        "\u0627\u0632 \u0646\u0638\u0631 \u0633\u0644\u0627\u0645\u062a \u0631\u0648\u0627\u0646 \u06cc\u0647 \u0686\u06cc\u0632\u06cc \u0646\u0634\u0648\u0646 \u0628\u062f\u0647.",
        "\u0628\u0628\u06cc\u0646 \u0648\u0636\u0639\u06cc\u062a \u062f\u0627\u0646\u0634\u062c\u0648\u0647\u0627 \u0686\u0637\u0648\u0631\u0647\u061f",
        "\u062d\u0627\u0644\u0627 \u062f\u0631\u0635\u062f\u0634 \u0631\u0648 \u0628\u062f\u0647.",
        "\u0647\u0645\u0648\u0646 \u062a\u062d\u0644\u06cc\u0644 \u062e\u0648\u0627\u0628 \u0648 \u0646\u0645\u0631\u0647 \u0631\u0648 \u0627\u06cc\u0646 \u0628\u0627\u0631 \u0628\u0627 \u0633\u0647 \u06af\u0631\u0648\u0647 \u062e\u0648\u0627\u0628 \u0628\u0633\u0627\u0632.",
        "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 \u062e\u0648\u0627\u0628 \u0628\u0686\u0647\u200c\u0647\u0627 \u062a\u0648 \u062f\u06cc\u062a\u0627 \u0686\u0646\u062f\u0647\u061f",
    ]

    classifier = IntentClassifier()
    for question in questions:
        decision = classifier.classify(question)
        assert decision.intent == IntentLabel.AMBIGUOUS_QUERY
        assert not decision.should_generate_sql
        assert decision.expected_action == ExpectedAction.ASK_CLARIFICATION


def test_colloquial_student_filter_with_metric_still_generates_sql():
    question = (
        "\u0628\u0686\u0647\u200c\u0647\u0627\u06cc\u06cc \u06a9\u0647 "
        "\u0633\u0648\u0634\u0627\u0644 \u0645\u062f\u06cc\u0627 \u0632\u06cc\u0627\u062f "
        "\u0645\u0635\u0631\u0641 \u0645\u06cc\u06a9\u0646\u0646 "
        "\u0646\u0645\u0631\u0634\u0648\u0646 \u0686\u0637\u0648\u0631\u0647\u061f"
    )

    decision = IntentClassifier().classify(question)

    assert decision.should_generate_sql
    assert decision.expected_action == ExpectedAction.GENERATE_SQL
