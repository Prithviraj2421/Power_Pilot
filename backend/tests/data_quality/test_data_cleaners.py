import pandas as pd
import pytest

from app.data_quality.plugins.cleaners.category_cleaner import CategoryCleaner
from app.data_quality.plugins.cleaners.date_cleaner import DateCleaner
from app.data_quality.plugins.cleaners.duplicate_cleaner import DuplicateCleaner
from app.data_quality.plugins.cleaners.missing_cleaner import MissingValueCleaner
from app.data_quality.plugins.cleaners.numeric_cleaner import NumericCleaner
from app.models.data_quality_models import DuplicateStrategy, ImputationStrategy


def test_missing_value_cleaner_median() -> None:
    df = pd.DataFrame({"val": [10.0, None, 30.0, 20.0]})
    cleaner = MissingValueCleaner()
    cleaned, audit = cleaner.clean(df, ImputationStrategy.MEDIAN)

    assert cleaned["val"].isna().sum() == 0
    assert cleaned["val"].iloc[1] == 20.0
    assert len(audit) == 1


def test_duplicate_cleaner_remove() -> None:
    df = pd.DataFrame({"id": [1, 1, 2], "val": ["a", "a", "b"]})
    cleaner = DuplicateCleaner()
    cleaned, audit = cleaner.clean(df, DuplicateStrategy.REMOVE)

    assert len(cleaned) == 2
    assert len(audit) == 1


def test_category_cleaner_normalization() -> None:
    df = pd.DataFrame({"city": ["mumbai", "MUMBAI ", "Delhi"]})
    cleaner = CategoryCleaner()
    cleaned, audit = cleaner.clean(df)

    assert cleaned["city"].tolist() == ["Mumbai", "Mumbai", "Delhi"]
    assert len(audit) == 1


def test_numeric_cleaner_currency_parsing() -> None:
    df = pd.DataFrame({"amount": ["$1,000.50", "$2,500.00"]})
    cleaner = NumericCleaner()
    cleaned, audit = cleaner.clean(df)

    assert cleaned["amount"].dtype == "float64"
    assert cleaned["amount"].iloc[0] == 1000.50
    assert len(audit) == 1


def test_date_cleaner_iso_conversion() -> None:
    df = pd.DataFrame({"created_date": ["01/15/2024", "2024-02-20"]})
    cleaner = DateCleaner()
    cleaned, audit = cleaner.clean(df)

    assert cleaned["created_date"].iloc[0] == "2024-01-15"
    assert len(audit) == 1
