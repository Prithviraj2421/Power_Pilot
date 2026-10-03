from dataclasses import dataclass, replace

import pandas as pd

from app.common.logger import get_logger, log_execution_time
from app.data_quality.dqpe_facade import DataQualityPreparationEngine
from app.intelligence.business_profiler import BusinessProfiler
from app.intelligence.dashboard_engine import DashboardEngine
from app.intelligence.data_intelligence_engine import DataIntelligenceEngine
from app.intelligence.decision_engine import DecisionEngine
from app.intelligence.domain_classifier import DomainClassifier
from app.intelligence.entity_detector import EntityDetector
from app.intelligence.insight_engine import InsightEngine
from app.intelligence.kpi_engine import KPIEngine
from app.intelligence.relationship_engine import RelationshipEngine
from app.intelligence.schema.schema_analyzer import SchemaAnalyzer
from app.models.data_quality_models import PreparationConfig
from app.models.master_intelligence_result import MasterIntelligenceResult

logger = get_logger("PowerPilotPipeline")


@dataclass(slots=True, frozen=True)
class PipelineExecution:
    """One pipeline run: the analysis plus the cleaned frame it was derived from.

    ``MasterIntelligenceResult`` is the serializable analysis that goes to clients.
    The cleaned DataFrame deliberately lives outside it -- it is not JSON data --
    but callers exporting a "cleaned dataset" need the real post-Stage-1 frame
    rather than the raw upload, so it is returned alongside.
    """

    result: MasterIntelligenceResult
    cleaned_dataframe: pd.DataFrame


class PowerPilotIntelligencePipeline:
    """
    Master Intelligence Pipeline orchestrator running Stage 1 (DQPE) through Stage 12.
    """

    def __init__(self) -> None:
        self.dqpe = DataQualityPreparationEngine()
        self.schema_analyzer = SchemaAnalyzer()
        self.entity_detector = EntityDetector()
        self.domain_classifier = DomainClassifier()
        self.business_profiler = BusinessProfiler()
        self.data_intelligence_engine = DataIntelligenceEngine()
        self.insight_engine = InsightEngine()
        self.relationship_engine = RelationshipEngine()
        self.kpi_engine = KPIEngine()
        self.dashboard_engine = DashboardEngine()
        self.decision_engine = DecisionEngine()

    def run_pipeline(
        self,
        df: pd.DataFrame,
        dataset_name: str = "Dataset.csv",
        prep_config: PreparationConfig = PreparationConfig(),
    ) -> MasterIntelligenceResult:
        """Run all 12 stages and return the analysis.

        Use :meth:`execute` instead when you also need the cleaned DataFrame.
        """
        return self.execute(df, dataset_name=dataset_name, prep_config=prep_config).result

    @log_execution_time(logger, "Master Intelligence Pipeline Run")
    def execute(
        self,
        df: pd.DataFrame,
        dataset_name: str = "Dataset.csv",
        prep_config: PreparationConfig = PreparationConfig(),
    ) -> PipelineExecution:
        """Run all 12 stages, returning the analysis and the cleaned DataFrame."""
        logger.info(f"Starting pipeline execution for dataset '{dataset_name}' ({len(df)} rows)")

        # Stage 1: Data Quality & Preparation Engine (DQPE)
        quality_report = self.dqpe.assess_quality(df, dataset_name=dataset_name)
        cleaned_df, prep_report = self.dqpe.prepare_data(df, config=prep_config, dataset_name=dataset_name)

        # Stage 2: Schema Analyzer (Receives ONLY Cleaned DataFrame)
        dataset_profile = self.schema_analyzer.analyze(cleaned_df, dataset_name=dataset_name)

        # Stage 3: Entity Detector
        detected_entities = self.entity_detector.detect(dataset_profile, cleaned_df)

        # Stage 4: Domain Classifier
        self.domain_classifier.classify(dataset_profile)

        # Stage 5: KPI Engine. It runs before the Business Profiler so that every KPI shown
        # anywhere (insights, executive summary, dashboard cards, exports) is one that was
        # compiled to DAX and verified against this cleaned data. Unverified ones are rejected.
        kpi_report = self.kpi_engine.recommend(dataset_profile, entities=detected_entities, df=cleaned_df)

        # Stage 6: Business Profiler. Its KPI lists are replaced with the verified ones.
        business_profile = self.business_profiler.profile(dataset_profile, detected_entities)
        business_profile = replace(
            business_profile,
            primary_kpis=kpi_report.primary_kpis,
            secondary_kpis=kpi_report.secondary_kpis,
        )

        # Stage 7: Data Intelligence Engine
        data_intelligence_report = self.data_intelligence_engine.analyze(cleaned_df, dataset_profile)

        # Stage 8: Insight Engine
        insight_report = self.insight_engine.generate(
            dataset_profile=dataset_profile,
            business_profile=business_profile,
            intelligence_report=data_intelligence_report,
            df=cleaned_df,
        )

        # Stage 9: Relationship Engine
        relationship_report = self.relationship_engine.analyze(dataset_profile, cleaned_df)

        # Stage 10: Dashboard Recommendation Engine
        dashboard_report = self.dashboard_engine.recommend(
            dataset_profile=dataset_profile,
            business_profile=business_profile,
            kpi_report=kpi_report,
            insight_report=insight_report,
        )

        # Stage 11: Strategic Decision Engine
        decision_report = self.decision_engine.decide(
            dataset_profile=dataset_profile,
            business_profile=business_profile,
            intelligence_report=data_intelligence_report,
            insight_report=insight_report,
            relationship_report=relationship_report,
            kpi_report=kpi_report,
            dashboard_report=dashboard_report,
        )

        logger.info(f"Successfully completed master pipeline execution for '{dataset_name}'")

        result = MasterIntelligenceResult(
            dataset_profile=dataset_profile,
            detected_entities=detected_entities,
            quality_report=quality_report,
            preparation_report=prep_report,
            business_profile=business_profile,
            data_intelligence_report=data_intelligence_report,
            insight_report=insight_report,
            relationship_report=relationship_report,
            kpi_report=kpi_report,
            dashboard_report=dashboard_report,
            decision_report=decision_report,
        )

        return PipelineExecution(result=result, cleaned_dataframe=cleaned_df)
