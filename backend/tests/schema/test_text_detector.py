"""Tests for the TextDetector plugin."""
import pytest
import pandas as pd

from app.common.enums import PhysicalType
from app.intelligence.schema.TypeDetector.text_detector import TextDetector


class TestTextDetector:
    """Tests for the TextDetector (fallback detector)."""

    def setup_method(self) -> None:
        self.detector = TextDetector()

    def test_detects_text(self) -> None:
        """High-cardinality strings should be detected as TEXT."""
        # Must be high cardinality so CategoryDetector doesn't claim it first
        series = pd.Series([f"unique text value {i}" for i in range(50)], dtype="object")
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.TEXT

    def test_rejects_non_object_dtype(self) -> None:
        """Non-object dtype should return None."""
        series = pd.Series([1, 2, 3])
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

    def test_higher_confidence_for_long_text(self) -> None:
        """Strings longer than 50 chars should yield confidence >= 0.7."""
        series = pd.Series(["a" * 55, "b" * 60, "c" * 70], dtype="object")
        result = self.detector.detect(series)
        assert result is not None
        assert result.confidence >= 0.7

    def test_higher_confidence_for_high_cardinality(self) -> None:
        """Many unique strings should boost confidence."""
        series = pd.Series([f"{i} random text content" for i in range(100)], dtype="object")
        result = self.detector.detect(series)
        assert result is not None
        assert result.confidence > 0.5  # Above base confidence

    def test_always_returns_result_for_non_empty_object(self) -> None:
        """TextDetector should always return a result for non-empty object columns."""
        series = pd.Series(["a", "b", "c"], dtype="object")
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.TEXT

    def test_evidence_contains_dtype(self) -> None:
        """Evidence should mention the column dtype."""
        series = pd.Series(["hello", "world"], dtype="object")
        result = self.detector.detect(series)
        assert result is not None
        assert any("object" in e.lower() or "dtype" in e.lower() for e in result.evidence)
