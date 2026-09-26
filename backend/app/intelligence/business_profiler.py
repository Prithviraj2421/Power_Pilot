"""
Business Intelligence Profiler module facade for PowerPilot.

Ingests technical dataset profiles, detected semantic entities, and domain classification
results to generate executive business profiles containing KPIs, questions, charts, and dashboard layouts.
"""

from typing import Optional

from app.common.enums import DatasetDomain
from app.intelligence.business.base_business_profiler import BaseBusinessProfiler
from app.intelligence.business.profilers import BUSINESS_PROFILE_REGISTRY
from app.intelligence.business.profilers.fallback_profiler import FallbackProfiler
from app.models.business_profile import BusinessProfile
from app.models.dataset_profile import DatasetProfile
from app.models.detected_entity import DetectedEntity


class BusinessProfiler:
    """
    Facade orchestrating Business Intelligence profiling across registered domain profilers.

    Selects the domain profiler matching DatasetProfile.detected_domain, generates
    executive business recommendations, and returns a complete BusinessProfile.
    """

    def __init__(self) -> None:
        """Initialize all registered domain profiler plugins into a domain lookup map."""
        self._profilers: dict[DatasetDomain, BaseBusinessProfiler] = {}
        self._fallback_profiler = FallbackProfiler()

        for profiler_cls in BUSINESS_PROFILE_REGISTRY:
            profiler = profiler_cls()
            target_domain = getattr(profiler, "target_domain", None)
            if target_domain and isinstance(target_domain, DatasetDomain):
                self._profilers[target_domain] = profiler

    def profile(
        self,
        dataset_profile: DatasetProfile,
        entities: Optional[list[DetectedEntity]] = None,
    ) -> BusinessProfile:
        """
        Synthesize technical dataset understanding into an executive BusinessProfile.

        Parameters
        ----------
        dataset_profile : DatasetProfile
            The dataset profile enriched by Schema Analyzer, Entity Detector, and Domain Classifier.
        entities : Optional[list[DetectedEntity]]
            Optional list of detected semantic entities.

        Returns
        -------
        BusinessProfile
            The generated executive business profile.
        """
        target_domain = getattr(dataset_profile, "detected_domain", DatasetDomain.UNKNOWN)
        profiler = self._profilers.get(target_domain, self._fallback_profiler)

        try:
            return profiler.profile(dataset_profile, entities)
        except Exception:
            # Fall back safely on error
            return self._fallback_profiler.profile(dataset_profile, entities)
