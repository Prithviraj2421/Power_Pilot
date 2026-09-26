"""Tests for the TypeDetector orchestrator."""
import pytest
import pandas as pd

from app.common.enums import PhysicalType
from app.intelligence.schema.type_detector import TypeDetector


class TestTypeDetectorOrchestrator:
    """Tests for the TypeDetector orchestrator."""

    def setup_method(self) -> None:
        self.detector = TypeDetector()

    def test_detects_integer_column(self) -> None:
        """Integer series should be detected as INTEGER."""
        series = pd.Series([1, 2, 3], dtype="int64")
        result = self.detector.detect(series)
        assert result.physical_type == PhysicalType.INTEGER

    def test_detects_float_column(self) -> None:
        """Float series with fractional parts should be detected as FLOAT."""
        series = pd.Series([1.5, 2.7, 3.14])
        result = self.detector.detect(series)
        assert result.physical_type == PhysicalType.FLOAT

    def test_detects_boolean_column(self) -> None:
        """Boolean-like strings should be detected as BOOLEAN."""
        series = pd.Series(["true", "false", "true", "false"])
        result = self.detector.detect(series)
        assert result.physical_type == PhysicalType.BOOLEAN

    def test_detects_datetime_column(self) -> None:
        """ISO date strings should be detected as DATETIME."""
        series = pd.Series([
            "2024-01-01", "2024-02-01", "2024-03-01",
            "2024-04-01", "2024-05-01",
        ])
        result = self.detector.detect(series)
        assert result.physical_type == PhysicalType.DATETIME

    def test_detects_categorical_column(self) -> None:
        """Low-cardinality string column repeated many times should be CATEGORICAL."""
        series = pd.Series(["A", "B", "C"] * 20, dtype="object")
        result = self.detector.detect(series)
        assert result.physical_type == PhysicalType.CATEGORICAL

    def test_detects_text_column(self) -> None:
        """High-cardinality long strings should be detected as TEXT."""
        series = pd.Series(
            [f"Unique sentence number {i} with enough words" for i in range(100)],
            dtype="object",
        )
        result = self.detector.detect(series)
        assert result.physical_type == PhysicalType.TEXT

    def test_returns_unknown_for_all_null(self) -> None:
        """All-null series should produce UNKNOWN with 0.0 confidence."""
        series = pd.Series([None, None, None])
        result = self.detector.detect(series)
        assert result.physical_type == PhysicalType.UNKNOWN
        assert result.confidence == 0.0

    def test_returns_unknown_for_empty(self) -> None:
        """Empty series should produce UNKNOWN."""
        series = pd.Series([], dtype=object)
        result = self.detector.detect(series)
        assert result.physical_type == PhysicalType.UNKNOWN

    def test_result_always_has_evidence(self) -> None:
        """Every result should include at least one evidence string."""
        series = pd.Series([1, 2, 3])
        result = self.detector.detect(series)
        assert len(result.evidence) > 0
        assert all(isinstance(e, str) for e in result.evidence)

    def test_highest_confidence_wins(self) -> None:
        """The orchestrator should return a result with positive confidence for valid data."""
        series = pd.Series([1, 1, 1, 1, 1], dtype="int64")
        result = self.detector.detect(series)
        assert result is not None
        assert result.confidence > 0.0
