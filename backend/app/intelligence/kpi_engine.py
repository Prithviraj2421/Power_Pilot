from __future__ import annotations

from typing import Optional

import pandas as pd

from app.common.enums import DatasetDomain, Priority
from app.common.logger import get_logger
from app.core.config import get_settings
from app.intelligence.kpi.base_kpi_plugin import BaseKPIPlugin
from app.intelligence.kpi.baseline import period_baseline
from app.intelligence.kpi.candidate import KPICandidate
from app.intelligence.kpi.column_resolver import ColumnResolver, table_for
from app.intelligence.kpi.compilers import DaxCompiler
from app.intelligence.kpi.dax_executor import DaxExecutor, disagreement
from app.intelligence.kpi.plugins import KPI_RECOMMENDATION_REGISTRY, FallbackKPIPlugin
from app.intelligence.kpi.verification import verify
from app.models.business_profile import BusinessProfile
from app.models.data_intelligence_models import DataIntelligenceReport
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity
from app.models.kpi_recommendation import KPIRecommendation
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport

logger = get_logger("KPIEngine")

_NO_BASELINE = "No baseline: needs a date column spanning at least two months"


class KPIEngine:
    """
    Facade orchestrating KPI generation across registered domain plugins.

    Plugins propose KPIs as expressions over real columns. Every proposal is compiled to
    DAX, computed on the cleaned dataset, and only reported if it verifies; the rest are
    kept in ``KPIReport.rejected_kpis`` with the reason. Nothing unverified is exported.
    """

    def __init__(self, dax_executor: Optional[DaxExecutor] = None) -> None:
        """Initialize domain plugins lookup map. ``dax_executor`` enables the optional engine check."""
        self._plugins: dict[DatasetDomain, BaseKPIPlugin] = {}
        self._fallback = FallbackKPIPlugin()
        self._dax_executor = dax_executor

        for plugin_cls in KPI_RECOMMENDATION_REGISTRY:
            plugin = plugin_cls()
            target_domain = getattr(plugin, "target_domain", None)
            if target_domain and isinstance(target_domain, DatasetDomain):
                self._plugins[target_domain] = plugin

    def recommend(
        self,
        dataset_profile: DatasetProfile,
        business_profile: Optional[BusinessProfile] = None,
        intelligence_report: Optional[DataIntelligenceReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
        entities: Optional[list[DetectedEntity]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> KPIReport:
        """
        Generate ranked, verified KPI recommendations for a dataset.

        ``df`` must be the cleaned DataFrame the model will be built from. Without it nothing
        can be verified, so every KPI is rejected rather than trusted.
        """
        domain = getattr(dataset_profile, "detected_domain", DatasetDomain.UNKNOWN)
        plugin = self._plugins.get(domain, self._fallback)
        args = (dataset_profile, business_profile, intelligence_report, relationship_report, entities, df)

        try:
            candidates = list(plugin.recommend(*args))
        except Exception:
            logger.exception(f"{type(plugin).__name__} failed; using the generic KPI plugin")
            plugin, candidates = self._fallback, list(self._fallback.recommend(*args))

        verified, rejected = self._verify_all(candidates, dataset_profile, entities, df)
        if not verified and plugin is not self._fallback:
            # The domain plugin found nothing it could stand behind; say something true instead.
            more_verified, more_rejected = self._verify_all(
                list(self._fallback.recommend(*args)), dataset_profile, entities, df
            )
            verified, rejected = more_verified, rejected + more_rejected

        prio_order = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
        verified.sort(key=lambda k: (prio_order.get(k.priority, 2), -k.confidence))

        return KPIReport(
            primary_kpis=tuple(verified[:3]),
            secondary_kpis=tuple(verified[3:]),
            all_kpis=tuple(verified),
            rejected_kpis=tuple(rejected),
            domain=domain,
            total_kpis_recommended=len(verified),
        )

    def _verify_all(
        self,
        candidates: list[KPICandidate],
        profile: DatasetProfile,
        entities: Optional[list[DetectedEntity]],
        df: Optional[pd.DataFrame],
    ) -> tuple[list[KPIRecommendation], list[KPIRecommendation]]:
        date_column = ColumnResolver(profile, entities).date()
        table = table_for(profile)
        verified: list[KPIRecommendation] = []
        rejected: list[KPIRecommendation] = []
        for candidate in candidates:
            record = self._materialize(candidate, table, df, date_column)
            (verified if record.verified else rejected).append(record)
        return verified, rejected

    def _materialize(
        self, candidate: KPICandidate, table: str, df: Optional[pd.DataFrame], date_column: Optional[str]
    ) -> KPIRecommendation:
        def record(**fields) -> KPIRecommendation:
            return KPIRecommendation(
                name=candidate.name,
                priority=candidate.priority,
                confidence=candidate.confidence,
                reason=candidate.reason,
                business_impact=candidate.business_impact,
                **fields,
            )

        if df is None:
            return record(verified=False, verification_note="no dataset was supplied to verify this KPI against")

        result = verify(candidate.expression, df, table)
        if result.verified and self._engine_check_enabled():
            problem = disagreement(result.value, result.dax, table, df, self._dax_executor)
            if problem:
                return record(formula=result.dax, verified=False, verification_note=problem)
        if not result.verified:
            return record(formula=result.dax, verified=False, verification_note=result.note)

        return record(
            formula=result.dax,
            target_threshold=self._target(candidate, df, date_column),
            computed_value=result.value,
            verified=True,
            verification_note=result.note,
        )

    def _engine_check_enabled(self) -> bool:
        if not get_settings().dax_engine_check:
            return False
        if self._dax_executor is None:
            logger.warning("POWERPILOT_DAX_ENGINE_CHECK is on but no DAX executor is registered; skipping it")
            return False
        return True

    @staticmethod
    def _target(candidate: KPICandidate, df: pd.DataFrame, date_column: Optional[str]) -> str:
        """A benchmark from the data when there is one; otherwise an explicitly labelled example."""
        if date_column and date_column in df.columns:
            baseline = period_baseline(candidate.expression, df, date_column)
            if baseline:
                return baseline.text
        if candidate.example_target:
            return f"Example target (not derived from your data): {candidate.example_target}"
        return _NO_BASELINE
