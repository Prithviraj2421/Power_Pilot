import pandas as pd

from app.data_quality.assessment_engine import DataQualityAssessmentEngine
from app.data_quality.preparation_engine import DataPreparationEngine
from app.models.data_quality_models import (
    DataPreparationReport,
    DatasetQualityReport,
    PreparationConfig,
)


class DataQualityPreparationEngine:
    """
    Master Stage 1 Facade providing Data Quality Assessment (Phase 1)
    and Data Preparation & Standardization (Phase 2).
    """

    def __init__(self) -> None:
        self.assessment_engine = DataQualityAssessmentEngine()
        self.preparation_engine = DataPreparationEngine()

    def assess_quality(self, df: pd.DataFrame, dataset_name: str = "Dataset.csv") -> DatasetQualityReport:
        """
        Execute Phase 1 Data Quality Assessment.
        """
        return self.assessment_engine.assess(df, dataset_name=dataset_name)

    def prepare_data(
        self, df: pd.DataFrame, config: PreparationConfig = PreparationConfig(), dataset_name: str = "Dataset.csv"
    ) -> tuple[pd.DataFrame, DataPreparationReport]:
        """
        Execute Phase 2 Data Preparation & Standardization.
        """
        return self.preparation_engine.prepare(df, config=config, dataset_name=dataset_name)
