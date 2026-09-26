"""Tests for the DatetimeDetector plugin."""
import pytest
import pandas as pd

from app.common.enums import PhysicalType
from app.common.constants import DATE_PARSE_THRESHOLD
from app.intelligence.schema.TypeDetector.datetime_detector import DatetimeDetector


class TestDatetimeDetector:
    """Tests for the DatetimeDetector."""

    def setup_method(self) -> None:
        self.detector = DatetimeDetector()

    def test_detects_native_datetime(self) -> None:
        """Native datetime64 Series should be detected with confidence 1.0."""
        series = pd.to_datetime(pd.Series(["2024-01-01", "2024-02-01"]))
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.DATETIME
        assert result.confidence == 1.0

    def test_detects_iso_date_strings(self) -> None:
        """ISO date strings should be detected as DATETIME."""
        # Use enough values to exceed the threshold
        dates = [f"2024-{m:02d}-01" for m in range(1, 13)]
        series = pd.Series(dates, dtype="object")
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.DATETIME

    def test_detects_us_date_strings(self) -> None:
        """US-format date strings should be detected as DATETIME."""
        dates = [f"{m:02d}/15/2024" for m in range(1, 13)]
        series = pd.Series(dates, dtype="object")
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.DATETIME

    def test_rejects_non_date_strings(self) -> None:
        """Non-date strings should return None."""
        series = pd.Series(["hello", "world", "foo", "bar"], dtype="object")
        result = self.detector.detect(series)
        assert result is None

    def test_returns_none_for_empty(self) -> None:
        """Empty series should return None."""
        series = pd.Series([], dtype="object")
        result = self.detector.detect(series)
        assert result is None

    def test_returns_none_for_all_null(self) -> None:
        """All-null series should return None."""
        series = pd.Series([None, None], dtype="object")
        result = self.detector.detect(series)
        assert result is None

    def test_rejects_below_threshold(self) -> None:
        """When parseable dates are below DATE_PARSE_THRESHOLD, should return None."""
        # 1 date out of 11 = ~9% parseable, well below 95%
        series = pd.Series(["2024-01-01"] + ["not a date"] * 10, dtype="object")
        result = self.detector.detect(series)
        assert result is None

    def test_confidence_reflects_parse_ratio(self) -> None:
        """Confidence should equal the parse success ratio."""
        # All values parseable → confidence should be 1.0
        dates = [f"2024-{m:02d}-01" for m in range(1, 11)]
        series = pd.Series(dates, dtype="object")
        result = self.detector.detect(series)
        assert result is not None
        assert result.confidence >= DATE_PARSE_THRESHOLD
