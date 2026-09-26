import pytest
import pandas as pd
from app.intelligence.schema.TypeDetector.boolean_detector import BooleanDetector
from app.models.type_detection_result import TypeDetectionResult
from app.common.enums import PhysicalType
from app.common.constants import BOOLEAN_VALUES

class TestBooleanDetector:
    def setup_method(self):
        self.detector = BooleanDetector()

    def test_detects_true_false_strings(self):
        """Test detection of 'true' and 'false' strings."""
        series = pd.Series(['true', 'false', 'true'])
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.BOOLEAN
        assert result.confidence == 1.0

    def test_detects_yes_no(self):
        """Test detection of 'yes' and 'no' strings."""
        series = pd.Series(['yes', 'no', 'yes', 'no'])
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.BOOLEAN

    def test_detects_mixed_case(self):
        """Test detection of mixed case boolean strings."""
        series = pd.Series(['True', 'FALSE', 'Yes', 'NO'])
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.BOOLEAN

    def test_detects_one_zero(self):
        """Test detection of '1' and '0' strings."""
        series = pd.Series(['1', '0', '1', '0'])
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.BOOLEAN

    def test_rejects_non_boolean(self):
        """Test rejection of non-boolean strings."""
        series = pd.Series(['apple', 'banana'])
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

    def test_handles_mixed_with_nulls(self):
        """Test boolean detection with nulls mixed in."""
        series = pd.Series(['true', None, 'false'])
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.BOOLEAN

    def test_evidence_contains_tokens(self):
        """Test that evidence strings mention found tokens."""
        series = pd.Series(['true', 'false'])
        result = self.detector.detect(series)
        assert result is not None
        assert result.evidence
        # Evidence should contain info about tokens found
