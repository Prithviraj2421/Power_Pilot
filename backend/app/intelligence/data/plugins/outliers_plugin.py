from typing import Optional

import pandas as pd

from app.intelligence.data.base_data_intelligence_plugin import BaseDataIntelligencePlugin
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import OutlierReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class OutliersPlugin(BaseDataIntelligencePlugin):
    """
    Data intelligence plugin for detecting outliers in numeric columns
    using the Interquartile Range (IQR) method.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> tuple[OutlierReport, ...]:
        """
        Analyzes the DataFrame for numeric outliers using IQR.
        """
        reports = []

        numeric_cols = df.select_dtypes(include=["number"]).columns

        for col in numeric_cols:
            series = df[col].dropna()
            if series.empty:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outliers = series[(series < lower_bound) | (series > upper_bound)]
            outlier_count = len(outliers)

            if outlier_count > 0:
                outlier_percentage = (outlier_count / len(series)) * 100.0
                confidence = 0.9 if outlier_percentage < 5 else (0.7 if outlier_percentage < 15 else 0.5)

                report = OutlierReport(
                    column_name=str(col),
                    outlier_count=outlier_count,
                    outlier_percentage=round(outlier_percentage, 2),
                    method_used="IQR",
                    outlier_bounds=(round(lower_bound, 4), round(upper_bound, 4)),
                    confidence=confidence,
                    reasoning=f"Found {outlier_count} values outside the IQR bounds [{lower_bound:.2f}, {upper_bound:.2f}].",
                )
                reports.append(report)

        return tuple(reports)
