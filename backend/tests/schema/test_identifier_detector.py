"""Tests for the IdentifierDetector."""
import pytest
import pandas as pd

from app.intelligence.schema.identifier_detector import IdentifierDetector


class TestIdentifierDetector:
    """Tests for the IdentifierDetector."""

    def setup_method(self) -> None:
        self.detector = IdentifierDetector()

    def test_detects_id_column_by_name(self) -> None:
        """Column named 'id' with unique values should be detected as identifier."""
        series = pd.Series([101, 102, 103])
        result = self.detector.detect(series, column_name="id")
        assert result.is_identifier is True

    def test_detects_id_by_suffix(self) -> None:
        """Column named 'customer_id' with unique values should be detected."""
        series = pd.Series(["C1", "C2", "C3"])
        result = self.detector.detect(series, column_name="customer_id")
        assert result.is_identifier is True

    def test_detects_sequential_integers(self) -> None:
        """Monotonically increasing integers with ID-like name should be detected."""
        series = pd.Series([1, 2, 3, 4, 5])
        result = self.detector.detect(series, column_name="row_num")
        assert result.is_identifier is True

    def test_rejects_non_unique_values(self) -> None:
        """Column with many duplicates should be rejected as identifier."""
        series = pd.Series(["cat1", "cat1", "cat2", "cat1", "cat2"])
        result = self.detector.detect(series, column_name="category")
        assert result.is_identifier is False

    def test_rejects_non_id_name_non_unique(self) -> None:
        """Non-ID named column with duplicates should be rejected."""
        series = pd.Series([9.99, 9.99, 19.99, 9.99])
        result = self.detector.detect(series, column_name="price")
        assert result.is_identifier is False

    def test_handles_all_null(self) -> None:
        """All-null column should not be detected as identifier."""
        series = pd.Series([None, None, None])
        result = self.detector.detect(series, column_name="id")
        assert result.is_identifier is False
        assert result.confidence == 0.0

    def test_evidence_explains_decision(self) -> None:
        """Evidence should be non-empty and contain descriptive strings."""
        series = pd.Series([1, 2, 3])
        result = self.detector.detect(series, column_name="id")
        assert len(result.evidence) > 0
        assert all(isinstance(e, str) for e in result.evidence)

    def test_confidence_between_0_and_1(self) -> None:
        """Confidence score should always be between 0.0 and 1.0."""
        series = pd.Series([1, 2, 3])
        result = self.detector.detect(series, column_name="id")
        assert 0.0 <= result.confidence <= 1.0

    def test_name_only_not_enough(self) -> None:
        """ID-like name alone should not be enough if values aren't unique."""
        series = pd.Series(["A", "A", "A", "A", "A"])
        result = self.detector.detect(series, column_name="id")
        assert result.is_identifier is False
