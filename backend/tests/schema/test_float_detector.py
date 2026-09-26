import pytest
import pandas as pd
from app.intelligence.schema.TypeDetector.float_detector import FloatDetector
from app.models.type_detection_result import TypeDetectionResult
from app.common.enums import PhysicalType

class TestFloatDetector:
    def setup_method(self):
        self.detector = FloatDetector()

    def test_detects_native_float_with_fractions(self):
        """Test detection of native float series with fractional parts."""
        series = pd.Series([1.5, 2.7, 3.14])
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.FLOAT
        assert result.confidence == 1.0

    def test_rejects_all_whole_numbers(self):
        """Test rejection of floats that are actually whole numbers (let IntegerDetector handle)."""
        series = pd.Series([1.0, 2.0, 3.0])
        result = self.detector.detect(series)
        assert result is None

    def test_detects_string_float(self):
        """Test detection of floats stored as strings."""
        series = pd.Series(['1.5', '2.7', '3.14'])
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.FLOAT

    def test_rejects_non_numeric_strings(self):
        """Test rejection of non-numeric strings."""
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

    def test_rejects_string_int_no_fractions(self):
        """Test rejection of string integers with no fractional parts."""
        series = pd.Series(['1', '2', '3'])
        result = self.detector.detect(series)
        assert result is None
