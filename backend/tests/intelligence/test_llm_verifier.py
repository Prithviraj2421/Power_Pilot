"""Tests for numeric claim verification.

This is the component that turns "grounded" from a prompt instruction into
something enforced. If it is wrong in the permissive direction, a fabricated
figure reaches a user as analysis; if it is wrong in the strict direction, good
answers get discarded. Both directions are tested.
"""

from __future__ import annotations

import pytest

from app.intelligence.llm.verifier import extract_numbers, verify_numeric_claims

FACTS = """
DATA QUALITY
  - Overall score: 91.7% (grade A)
  - Issues detected: 8
CLEANING APPLIED
  - Rows before cleaning: 61
  - Rows after cleaning: 60
TRENDS
  - unit_price is decreasing over order_date (slope -12.5, change -92.4%)
CORRELATIONS
  - discount vs profit: -0.81 (strong_negative)
BUSINESS ANOMALIES
  - Margin collapse: profit observed 1,234.56 vs expected 10,000.00
"""


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def test_extracts_plain_integers_and_decimals() -> None:
    values = [value for _token, value in extract_numbers("There are 8 issues and 91.7 percent.")]
    assert 8.0 in values
    assert 91.7 in values


def test_extracts_percentages_currency_and_thousands() -> None:
    values = [value for _token, value in extract_numbers("Revenue was $1,234.56, up 12.5%.")]
    assert 1234.56 in values
    assert 12.5 in values


def test_extracts_negative_numbers() -> None:
    values = [value for _token, value in extract_numbers("The coefficient is -0.81.")]
    assert -0.81 in values


def test_does_not_treat_identifier_digits_as_numbers() -> None:
    """column_2 and v1.2 are names, not claims."""
    tokens = [token for token, _value in extract_numbers("See column_2 and version v1.2")]
    assert tokens == []


# ---------------------------------------------------------------------------
# Grounded answers pass
# ---------------------------------------------------------------------------


def test_answer_quoting_the_facts_verbatim_is_grounded() -> None:
    answer = "Data quality is 91.7% with 8 issues detected."

    result = verify_numeric_claims(answer, FACTS)

    assert result.grounded
    assert result.unsupported_values == ()


def test_rounding_a_fact_is_accepted() -> None:
    """A model writing 92% for a stored 91.7% is rephrasing, not inventing."""
    assert verify_numeric_claims("Quality is about 92%.", FACTS).grounded


def test_reformatted_thousands_separator_is_accepted() -> None:
    assert verify_numeric_claims("Profit came in at 1234.56.", FACTS).grounded


def test_small_counts_are_not_treated_as_claims() -> None:
    """"three points below" must not trip the check on every answer."""
    answer = "There are 3 things to note, in 2 categories, across 1 dataset."

    result = verify_numeric_claims(answer, FACTS)

    assert result.grounded
    assert result.checked_count == 0


def test_numbers_supplied_by_the_user_are_allowed() -> None:
    """Repeating the question's own figure back is not a fabrication."""
    question = "Is a margin above 47.3% realistic?"

    assert verify_numeric_claims("A margin of 47.3% is not measured here.", FACTS, question).grounded


def test_an_answer_with_no_numbers_is_grounded() -> None:
    result = verify_numeric_claims("The analysis does not measure customer churn.", FACTS)

    assert result.grounded
    assert result.checked_count == 0


# ---------------------------------------------------------------------------
# Fabricated figures are caught
# ---------------------------------------------------------------------------


def test_an_invented_figure_is_rejected() -> None:
    answer = "Revenue grew 23.8% year over year."

    result = verify_numeric_claims(answer, FACTS)

    assert not result.grounded
    assert "23.8%" in result.unsupported_values


def test_a_plausible_but_absent_figure_is_rejected() -> None:
    """The dangerous case: a number that reads like analysis and is not in it."""
    answer = "Data quality is 91.7%, and the churn rate is 14.2%."

    result = verify_numeric_claims(answer, FACTS)

    assert not result.grounded
    assert result.unsupported_values == ("14.2%",)


def test_several_invented_figures_are_all_reported() -> None:
    answer = "Margins fell 18.5% while costs rose 42.7% and headcount hit 317."

    result = verify_numeric_claims(answer, FACTS)

    assert not result.grounded
    assert len(result.unsupported_values) == 3


def test_a_repeated_invented_figure_is_reported_once() -> None:
    answer = "Growth was 23.8%. That 23.8% is the headline."

    result = verify_numeric_claims(answer, FACTS)

    assert result.unsupported_values == ("23.8%",)


def test_summary_describes_the_outcome() -> None:
    grounded = verify_numeric_claims("Quality is 91.7%.", FACTS)
    assert "trace to the analysis" in grounded.summary

    ungrounded = verify_numeric_claims("Churn is 14.2%.", FACTS)
    assert "could not be traced" in ungrounded.summary
    assert "14.2%" in ungrounded.summary


@pytest.mark.parametrize(
    "answer",
    [
        "Quality scored 91.7% overall.",
        "Cleaning removed rows, taking 61 down to 60.",
        "unit_price fell -92.4% across the period.",
        "discount and profit correlate at -0.81.",
    ],
)
def test_real_phrasings_of_real_facts_all_pass(answer: str) -> None:
    assert verify_numeric_claims(answer, FACTS).grounded, answer


# ---------------------------------------------------------------------------
# Citation-level verification: the right number AND the right fact
# ---------------------------------------------------------------------------

from app.intelligence.llm.facts import Fact, find_numbers, strip_citations  # noqa: E402
from app.intelligence.llm.verifier import (  # noqa: E402
    MISSING,
    UNKNOWN_FACT,
    WRONG_MEANING,
    WRONG_UNIT,
    WRONG_VALUE,
    verify_citations,
)

CITED = {
    "F1": Fact("F1", "dataset.rows", 9994, "count", "Number of rows in the dataset"),
    "F2": Fact("F2", "kpi.total_sales_revenue.value", 2297200.86, "currency", "Total Sales Revenue (KPI value)"),
    "F3": Fact("F3", "quality.overall_score", 91.66, "percent", "Overall data quality score"),
    "F4": Fact("F4", "kpi.profit_margin.value", 0.1034, "ratio", "Profit Margin (KPI value)"),
    "F5": Fact("F5", "correlation.discount.profit", -0.81, "coefficient", "Correlation coefficient between discount and profit"),
    "F6": Fact("F6", "kpi.active_customers.value", 2841, "number", "Active Customer Count (KPI value)"),
}


def kinds(answer: str, question: str = "") -> list[str]:
    return [p.kind for p in verify_citations(answer, CITED, question).problems]


def test_a_cited_number_that_matches_its_fact_passes_and_the_tag_is_stripped() -> None:
    result = verify_citations("Revenue is 2297200.86 [F2] and quality is 91.66% [F3].", CITED)

    assert result.grounded and result.checked_count == 2
    assert result.clean_text == "Revenue is 2297200.86 and quality is 91.66%."
    assert [(c.text, c.fact_id) for c in result.citations] == [("2297200.86", "F2"), ("91.66%", "F3")]
    for c in result.citations:
        assert result.clean_text[c.start : c.end] == c.text


def test_the_right_number_for_the_wrong_fact_is_rejected() -> None:
    """Revenue is 9,994 passes the old check because 9,994 is the row count. It cites the row count and says revenue."""
    assert verify_citations("The dataset has 9,994 [F1] rows.", CITED).grounded
    assert kinds("Revenue is 9,994 [F1].") == [WRONG_MEANING]
    assert kinds("Total sales revenue came to 9,994 [F1].") == [WRONG_MEANING]


def test_a_number_that_is_not_the_cited_facts_value_is_rejected() -> None:
    assert kinds("Revenue is 2,500,000 [F2].") == [WRONG_VALUE]
    assert kinds("Revenue is 9,994 [F2].") == [WRONG_VALUE]  # F2 exists, but 9,994 is not its value


def test_a_number_with_no_citation_is_rejected() -> None:
    assert kinds("Revenue is 2297200.86.") == [MISSING]
    assert kinds("Revenue is 2297200.86 and quality is 91.7% [F3].") == [MISSING]
    assert kinds("Revenue is 2297200.86 for [F2] everyone.") == [MISSING]  # a tag that is not adjacent does not count


def test_a_fact_id_that_does_not_exist_is_rejected() -> None:
    assert kinds("Revenue is 2297200.86 [F99].") == [UNKNOWN_FACT]
    assert kinds("Revenue is 2297200.86 [F2, F99].") == [UNKNOWN_FACT]


def test_rounding_to_the_precision_written_is_accepted() -> None:
    assert verify_citations("Quality is 91.7% [F3].", CITED).grounded  # 91.66 -> 91.7
    assert verify_citations("Quality is 92% [F3].", CITED).grounded
    assert verify_citations("Revenue is $2.30M [F2].", CITED).grounded
    assert verify_citations("Revenue is 2.3 million [F2].", CITED).grounded
    assert verify_citations("About 2,297,201 [F2] in revenue.", CITED).grounded
    assert kinds("Quality is 91.8% [F3].") == [WRONG_VALUE]  # 91.66 does not round to 91.8
    assert kinds("Quality is 91.6% [F3].") == [WRONG_VALUE]
    assert kinds("Revenue is $2.4M [F2].") == [WRONG_VALUE]


def test_a_ratio_may_be_written_as_a_percent_and_a_plain_number_may_cite_a_percent() -> None:
    assert verify_citations("Profit margin is 10.3% [F4].", CITED).grounded  # 0.1034 -> 10.3%
    assert verify_citations("Profit margin is 0.10 [F4].", CITED).grounded
    assert verify_citations("The quality score is 91.7 [F3].", CITED).grounded


def test_a_number_written_with_the_wrong_unit_is_rejected() -> None:
    assert kinds("There are $9,994 [F1] rows.") == [WRONG_UNIT]  # a count is not money
    assert kinds("There are 9,994% [F1] rows.") == [WRONG_UNIT]  # a count is not a percent
    assert kinds("The correlation between discount and profit is -81% [F5].") == [WRONG_VALUE]  # -81 is not -0.81 ...
    assert kinds("Revenue is 91.66% [F2].") == [WRONG_VALUE] or kinds("Revenue is 91.66% [F2].") == [WRONG_UNIT]
    assert kinds("Discount and profit correlate at $0.81 [F5].") in ([WRONG_UNIT], [WRONG_VALUE])
    assert kinds("The quality score is $91.66 [F3].") == [WRONG_UNIT]  # a percent is not money


def test_money_may_be_written_for_a_generic_number_fact() -> None:
    assert verify_citations("We have 2,841 [F6] active customers.", CITED).grounded
    assert verify_citations("Revenue is $2,297,200.86 [F2].", CITED).grounded


def test_the_wrong_meaning_is_judged_by_the_sentence_not_the_digits() -> None:
    assert verify_citations("There are 2,841 [F6] active customers.", CITED).grounded
    assert kinds("Total revenue is 2,841 [F6].") == [WRONG_MEANING]
    assert kinds("The profit margin stands at 91.7% [F3].") == [WRONG_MEANING]  # quality score, not margin


def test_a_sentence_about_nothing_in_the_analysis_is_not_second_guessed() -> None:
    """Meaning is only judged when the sentence names something the analysis has facts about."""
    assert verify_citations("Roughly 9,994 [F1] entries in all.", CITED).grounded


def test_numbers_from_the_question_and_small_whole_numbers_need_no_citation() -> None:
    assert verify_citations("A margin of 47.3% is not measured here.", CITED, "Is our margin 47.3%?").grounded
    assert verify_citations("Here are 3 findings and 2 risks.", CITED).grounded
    assert not verify_citations("Here are 30 findings.", CITED).grounded


def test_a_tag_can_cite_several_facts_if_one_of_them_fits() -> None:
    result = verify_citations("There are 9,994 [F1, F2] rows.", CITED)
    assert result.grounded and result.citations[0].fact_id == "F1"


def test_citations_report_the_fact_behind_each_figure() -> None:
    result = verify_citations("Revenue is $2.30M [F2].", CITED)
    (citation,) = result.citations
    assert citation.to_dict() == {"start": 11, "end": 17, "text": "$2.30M", "fact_id": "F2",
                                  "label": "Total Sales Revenue (KPI value)", "value": 2297200.86, "unit": "currency"}


def test_failures_say_what_went_wrong() -> None:
    result = verify_citations("Revenue is 9,994 [F1]. Quality is 91.7%.", CITED)
    assert not result.grounded
    assert set(result.unsupported_values) == {"9,994", "91.7%"}
    assert "failed citation checks" in result.summary and "no fact id" in result.summary


def test_number_reading_and_tag_stripping() -> None:
    assert [m.value for m in find_numbers("up 12.5% to $1.2M, from 3,400")] == [12.5, 1_200_000, 3400]
    assert find_numbers("see column_2 and v1.2") == []
    assert strip_citations("Revenue is 2.30M [F12], up 5% [F13, F14].") == "Revenue is 2.30M, up 5%."
    assert strip_citations("no tags here") == "no tags here"
