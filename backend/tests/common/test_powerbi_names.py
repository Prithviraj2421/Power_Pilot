import pytest

from app.common.powerbi_names import dax_column, dax_table, m_string, powerbi_table_name


@pytest.mark.parametrize(
    ("dataset_name", "expected"),
    [
        ("orders.csv", "orders"),
        ("Orders.CSV", "Orders"),
        ("Sample - Superstore.csv", "Sample_Superstore"),
        ("Bengaluru_House_Data (1).csv", "Bengaluru_House_Data_1"),
        ("report.v2.xlsx", "report_v2"),
        (".csv", "Dataset"),
    ],
)
def test_table_name_strips_extension_and_punctuation(dataset_name: str, expected: str) -> None:
    assert powerbi_table_name(dataset_name) == expected


def test_dax_references_are_quoted_and_escaped() -> None:
    assert dax_table("orders") == "'orders'"
    assert dax_table("O'Brien") == "'O''Brien'"
    assert dax_column("orders", "Sub-Category") == "'orders'[Sub-Category]"
    assert dax_column("orders", "weird]name") == "'orders'[weird]]name]"


def test_m_string_doubles_quotes_and_leaves_backslashes_alone() -> None:
    assert m_string('say "hi"') == '"say ""hi"""'
    assert m_string("C:\\data\\file.csv") == '"C:\\data\\file.csv"'
