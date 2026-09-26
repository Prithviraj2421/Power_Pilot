"""Integration tests for the SchemaAnalyzer facade."""
import pytest
import pandas as pd

from app.common.enums import PhysicalType
from app.intelligence.schema.schema_analyzer import SchemaAnalyzer
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile


class TestSchemaAnalyzer:
    """Integration tests for the SchemaAnalyzer facade."""

    def setup_method(self) -> None:
        self.analyzer = SchemaAnalyzer()

    def test_analyzes_simple_dataframe(self) -> None:
        """Simple DataFrame with int, float, text columns should produce valid profile."""
        df = pd.DataFrame({
            "int_col": [1, 2, 3],
            "float_col": [1.1, 2.2, 3.3],
            "text_col": ["apple", "banana", "cherry"],
        })
        profile = self.analyzer.analyze(df, dataset_name="test.csv")

        assert isinstance(profile, DatasetProfile)
        assert profile.total_rows == 3
        assert profile.total_columns == 3
        assert len(profile.columns) == 3

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame should produce profile with zero rows and no columns."""
        df = pd.DataFrame()
        profile = self.analyzer.analyze(df, dataset_name="empty.csv")

        assert profile.total_rows == 0
        assert profile.total_columns == 0
        assert len(profile.columns) == 0

    def test_single_column_dataframe(self) -> None:
        """Single-column DataFrame should produce exactly one ColumnProfile."""
        df = pd.DataFrame({"single": [1, 2, 3]})
        profile = self.analyzer.analyze(df, dataset_name="single.csv")

        assert len(profile.columns) == 1
        assert profile.columns[0].name == "single"

    def test_column_profiles_have_required_fields(self) -> None:
        """Each ColumnProfile should have all required fields populated."""
        df = pd.DataFrame({"col1": [1, 2, 3]})
        profile = self.analyzer.analyze(df, dataset_name="test.csv")

        col = profile.columns[0]
        assert isinstance(col, ColumnProfile)
        assert col.name == "col1"
        assert col.physical_type is not None
        assert isinstance(col.nullable, bool)
        assert isinstance(col.unique, bool)
        assert isinstance(col.identifier, bool)
        assert isinstance(col.missing_count, int)
        assert isinstance(col.unique_count, int)

    def test_metadata_contains_type_distribution(self) -> None:
        """Dataset metadata should contain a type_distribution dict."""
        df = pd.DataFrame({"a": [1], "b": ["text"]})
        profile = self.analyzer.analyze(df, dataset_name="test.csv")

        assert "type_distribution" in profile.metadata
        assert isinstance(profile.metadata["type_distribution"], dict)

    def test_all_columns_profiled(self) -> None:
        """DataFrame with 5 columns should produce exactly 5 ColumnProfiles."""
        df = pd.DataFrame({
            "c1": [1], "c2": [2], "c3": [3], "c4": [4], "c5": [5],
        })
        profile = self.analyzer.analyze(df, dataset_name="five.csv")

        assert len(profile.columns) == 5

    def test_mixed_types_dataframe(self) -> None:
        """DataFrame with mixed types should detect each type correctly."""
        df = pd.DataFrame({
            "int_col": [1, 2, 3, 4, 5],
            "float_col": [1.1, 2.2, 3.3, 4.4, 5.5],
            "date_col": [
                "2023-01-01", "2023-01-02", "2023-01-03",
                "2023-01-04", "2023-01-05",
            ],
            "cat_col": ["A", "B", "A", "B", "A"],
            "text_col": [
                f"Long sentence number {i} with enough words to be clearly text"
                for i in range(5)
            ],
        })
        profile = self.analyzer.analyze(df, dataset_name="mixed.csv")

        assert len(profile.columns) == 5
        type_map = {col.name: col.physical_type for col in profile.columns}
        assert type_map["int_col"] == PhysicalType.INTEGER
        assert type_map["float_col"] == PhysicalType.FLOAT

    def test_column_metadata_contains_evidence(self) -> None:
        """Each column's metadata should contain type detection evidence."""
        df = pd.DataFrame({"col": [1, 2, 3]})
        profile = self.analyzer.analyze(df, dataset_name="test.csv")

        col = profile.columns[0]
        assert "type_detection_evidence" in col.metadata
        assert isinstance(col.metadata["type_detection_evidence"], list)
        assert len(col.metadata["type_detection_evidence"]) > 0

    def test_dataset_name_preserved(self) -> None:
        """The dataset_name passed to analyze should be preserved in the profile."""
        df = pd.DataFrame({"x": [1]})
        profile = self.analyzer.analyze(df, dataset_name="my_dataset.csv")
        assert profile.dataset_name == "my_dataset.csv"
