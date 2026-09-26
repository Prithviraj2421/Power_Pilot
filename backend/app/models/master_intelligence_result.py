from dataclasses import dataclass, field
from typing import Optional

from app.models.business_profile import BusinessProfile
from app.models.dashboard_models import DashboardRecommendationReport
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.data_quality_models import DataPreparationReport, DatasetQualityReport
from app.models.dataset_profile import DatasetProfile
from app.models.decision_models import DecisionReport
from app.models.detected_entity import DetectedEntity
from app.models.insight_models import InsightReport
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport


@dataclass(slots=True)
class MasterIntelligenceResult:
    """
    Master container aggregating outputs from all 12 pipeline stages.
    """

    dataset_profile: DatasetProfile
    detected_entities: list[DetectedEntity]
    quality_report: Optional[DatasetQualityReport] = None
    preparation_report: Optional[DataPreparationReport] = None
    business_profile: Optional[BusinessProfile] = None
    data_intelligence_report: Optional[DataIntelligenceReport] = None
    insight_report: Optional[InsightReport] = None
    relationship_report: Optional[RelationshipReport] = None
    kpi_report: Optional[KPIReport] = None
    dashboard_report: Optional[DashboardRecommendationReport] = None
    decision_report: Optional[DecisionReport] = None
