import pandas as pd
import pytest

from app.data_quality.plugins.validators.category_validator import CategoryValidator
from app.data_quality.plugins.validators.date_validator import DateValidator
from app.data_quality.plugins.validators.duplicate_validator import DuplicateValidator
from app.data_quality.plugins.validators.missing_validator import MissingValueValidator
from app.data_quality.plugins.validators.outlier_validator import OutlierValidator
from app.data_quality.plugins.validators.type_validator import TypeValidator


def test_missing_value_validator() -> None:
    df = pd.DataFrame({"col1": [1, None, "N/A", "NULL", "-"]})
    validator = MissingValueValidator()
    issues = validator.validate(df)

    assert len(issues) == 1
    assert issues[0].column == "col1"
    assert issues[0].affected_count == 4


def test_duplicate_validator() -> None:
    df = pd.DataFrame(
        {
            "customer_id": [1, 1, 2, 3],
            "name": ["Alice", "Alice", "Bob", "Charlie"],
        }
    )
    validator = DuplicateValidator()
    issues = validator.validate(df)

    assert len(issues) >= 1
    types = [i.issue_type for i in issues]
    assert "DUPLICATE_ROWS" in types or "DUPLICATE_IDENTIFIER" in types


def test_type_validator_currency() -> None:
    df = pd.DataFrame({"price": ["$100.00", "$200.50", "$300.00"]})
    validator = TypeValidator()
    issues = validator.validate(df)

    assert len(issues) == 1
    assert issues[0].issue_type == "CURRENCY_FORMAT_TEXT"


def test_category_validator() -> None:
    df = pd.DataFrame({"city": ["Mumbai", "mumbai", "MUMBAI ", "Delhi"]})
    validator = CategoryValidator()
    issues = validator.validate(df)

    assert len(issues) == 1
    assert issues[0].issue_type == "CATEGORY_CASE_INCONSISTENCY"


def test_date_validator() -> None:
    df = pd.DataFrame({"order_date": ["2024-01-01", "invalid_date_str", "2024-02-01"]})
    validator = DateValidator()
    issues = validator.validate(df)

    assert len(issues) == 1
    assert issues[0].issue_type == "INVALID_DATE_FORMAT"


def test_outlier_validator() -> None:
    df = pd.DataFrame({"values": [10, 12, 11, 13, 12, 11, 500]})
    validator = OutlierValidator()
    issues = validator.validate(df)

    assert len(issues) == 1
    assert issues[0].issue_type == "NUMERIC_OUTLIERS"
