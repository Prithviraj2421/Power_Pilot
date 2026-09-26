"""Tests for the StatisticsCalculator."""
import pytest
import numpy as np
import pandas as pd

from app.intelligence.schema.statistics_calculator import StatisticsCalculator


class TestStatisticsCalculator:
    """Tests for the StatisticsCalculator."""

    def setup_method(self) -> None:
        self.calc = StatisticsCalculator()

    def test_counts_missing_values(self) -> None:
        """Should correctly count NaN and None values."""
        series = pd.Series([1, np.nan, 3, None, 5])
        stats = self.calc.calculate(series)
        assert stats.missing_count == 2

    def test_counts_unique_values(self) -> None:
        """Should correctly count distinct non-null values."""
        series = pd.Series(["a", "b", "a", "c"])
        stats = self.calc.calculate(series)
        assert stats.unique_count == 3

    def test_detects_nullable(self) -> None:
        """Should set nullable=True when missing values present."""
        series = pd.Series([1, np.nan])
        stats = self.calc.calculate(series)
        assert stats.nullable is True

    def test_detects_non_nullable(self) -> None:
        """Should set nullable=False when no missing values."""
        series = pd.Series([1, 2, 3])
        stats = self.calc.calculate(series)
        assert stats.nullable is False

    def test_detects_unique_column(self) -> None:
        """Should set is_unique=True when all non-null values are distinct."""
        series = pd.Series([1, 2, 3, 4])
        stats = self.calc.calculate(series)
        assert stats.is_unique is True

    def test_detects_non_unique(self) -> None:
        """Should set is_unique=False when duplicates present."""
        series = pd.Series([1, 1, 2])
        stats = self.calc.calculate(series)
        assert stats.is_unique is False

    def test_handles_all_null(self) -> None:
        """All-null column should produce expected results."""
        series = pd.Series([np.nan, None, np.nan])
        stats = self.calc.calculate(series)
        assert stats.missing_count == 3
        assert stats.unique_count == 0
        assert stats.nullable is True
        assert stats.is_unique is False

    def test_total_count_correct(self) -> None:
        """total_count should equal the length of the series."""
        series = pd.Series([1, 2, np.nan, 4])
        stats = self.calc.calculate(series)
        assert stats.total_count == 4
