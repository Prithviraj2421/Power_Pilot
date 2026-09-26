"""Tests for the SampleCalculator."""
import pytest
import numpy as np
import pandas as pd

from app.common.constants import MAX_SAMPLE_VALUES
from app.intelligence.schema.sample_calculator import SampleCalculator


class TestSampleCalculator:
    """Tests for the SampleCalculator."""

    def setup_method(self) -> None:
        self.calc = SampleCalculator()

    def test_returns_samples_for_numeric(self) -> None:
        """Numeric columns should include min, max, and median."""
        series = pd.Series([10, 50, 20, 40, 30])
        samples = self.calc.calculate(series)
        assert 10 in samples  # min
        assert 50 in samples  # max
        assert len(samples) > 0

    def test_returns_samples_for_text(self) -> None:
        """Text columns should return most frequent values."""
        series = pd.Series(["apple", "banana", "apple", "cherry", "apple", "banana"])
        samples = self.calc.calculate(series)
        assert "apple" in samples  # most frequent
        assert len(samples) > 0

    def test_respects_max_sample_limit(self) -> None:
        """Number of returned samples should not exceed MAX_SAMPLE_VALUES."""
        series = pd.Series(range(1000))
        samples = self.calc.calculate(series)
        assert len(samples) <= MAX_SAMPLE_VALUES

    def test_returns_empty_for_all_null(self) -> None:
        """All-null column should return empty list."""
        series = pd.Series([None, None, np.nan])
        samples = self.calc.calculate(series)
        assert samples == []

    def test_returns_all_when_fewer_than_limit(self) -> None:
        """When unique values are fewer than limit, all should be returned."""
        series = pd.Series(["a", "b", "c", "a", "b"])
        samples = self.calc.calculate(series)
        assert set(samples) == {"a", "b", "c"}

    def test_returns_native_python_types(self) -> None:
        """Numpy types should be converted to native Python types."""
        series = pd.Series([np.int64(42), np.float64(3.14)])
        samples = self.calc.calculate(series)
        for sample in samples:
            assert isinstance(sample, (int, float, str, bool))
            assert not isinstance(sample, (np.integer, np.floating))

    def test_handles_single_value(self) -> None:
        """Single-value column should return a list with that one value."""
        series = pd.Series([42])
        samples = self.calc.calculate(series)
        assert len(samples) == 1
