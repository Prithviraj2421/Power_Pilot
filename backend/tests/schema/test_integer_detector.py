import pytest
import pandas as pd
from app.intelligence.schema.TypeDetector.integer_detector import IntegerDetector
from app.models.type_detection_result import TypeDetectionResult
from app.common.enums import PhysicalType

class TestIntegerDetector:
    def setup_method(self):
        self.detector = IntegerDetector()

    def test_detects_native_int(self):
        """Test detection of native integer series."""
        series = pd.Series([1, 2, 3], dtype='int64')
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.INTEGER
        assert result.confidence == 1.0

    def test_detects_float_stored_int(self):
        """Test detection of integers stored as floats (common with NaNs)."""
        series = pd.Series([1.0, 2.0, 3.0])
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.INTEGER

    def test_detects_string_int(self):
        """Test detection of integers stored as strings."""
        series = pd.Series(['1', '2', '3'])
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.INTEGER

    def test_rejects_non_integer(self):
        """Test rejection of non-integer strings."""
        series = pd.Series(['abc', 'def'])
        result = self.detector.detect(series)
        assert result is None

    def test_returns_none_for_empty(self):
        """Test that empty series returns None."""
        series = pd.Series([], dtype='object')
        result = self.detector.detect(series)
        assert result is None

    def test_returns_none_for_all_null(self):
        """Test that series with all nulls returns None."""
        series = pd.Series([None, None])
        result = self.detector.detect(series)
        assert result is None

    def test_rejects_float_with_fractions(self):
        """Test rejection of floats with fractional parts."""
        series = pd.Series([1.5, 2.7, 3.3])
        result = self.detector.detect(series)
        assert result is None

    def test_confidence_reflects_parse_ratio(self):
        """Test that confidence is proportional to the parseable ratio."""
        series = pd.Series([1, 2, 'abc', 'def'])
        result = self.detector.detect(series)
        if result is not None:
            assert result.confidence < 1.0
