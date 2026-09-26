"""Tests for the CategoryDetector plugin."""
import pytest
import pandas as pd

from app.common.enums import PhysicalType
from app.common.constants import CATEGORY_MAX_CARDINALITY, CATEGORY_MAX_RATIO
from app.intelligence.schema.TypeDetector.category_detector import CategoryDetector


class TestCategoryDetector:
    """Tests for the CategoryDetector."""

    def setup_method(self) -> None:
        self.detector = CategoryDetector()

    def test_detects_low_cardinality(self) -> None:
        """Low cardinality object column should be detected as CATEGORICAL.

        2 unique values out of 20 → cardinality ratio = 0.10 < 0.20.
        """
        series = pd.Series(["A", "B"] * 10, dtype="object")
        result = self.detector.detect(series)
        assert result is not None
        assert result.physical_type == PhysicalType.CATEGORICAL

    def test_rejects_high_cardinality_count(self) -> None:
        """More than CATEGORY_MAX_CARDINALITY unique values should be rejected."""
        series = pd.Series([str(i) for i in range(50)], dtype="object")
        result = self.detector.detect(series)
        assert result is None

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

    def test_rejects_high_cardinality_ratio(self) -> None:
        """Cardinality ratio above CATEGORY_MAX_RATIO should be rejected.

        10 unique values out of 10 → ratio = 1.0 > 0.20.
        """
        series = pd.Series([f"val_{i}" for i in range(10)], dtype="object")
        result = self.detector.detect(series)
        assert result is None

    def test_evidence_includes_top_values(self) -> None:
        """Evidence should mention cardinality and top values.

        3 unique values out of 30 → ratio = 0.10 < 0.20.
        """
        series = pd.Series(["A", "B", "C"] * 10, dtype="object")
        result = self.detector.detect(series)
        assert result is not None
        assert len(result.evidence) > 0
        # Check that evidence mentions cardinality or top values
        evidence_text = " ".join(result.evidence).lower()
        assert "unique" in evidence_text or "cardinality" in evidence_text

    def test_confidence_inversely_proportional_to_cardinality(self) -> None:
        """Lower cardinality should produce higher confidence."""
        # Very low cardinality: 2 unique in 40
        low_card = pd.Series(["X", "Y"] * 20, dtype="object")
        result_low = self.detector.detect(low_card)

        # Higher cardinality: 4 unique in 40
        high_card = pd.Series(["A", "B", "C", "D"] * 10, dtype="object")
        result_high = self.detector.detect(high_card)

        assert result_low is not None
        assert result_high is not None
        assert result_low.confidence >= result_high.confidence
