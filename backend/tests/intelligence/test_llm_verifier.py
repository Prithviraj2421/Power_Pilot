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
