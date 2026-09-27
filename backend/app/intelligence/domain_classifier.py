"""
Domain Classifier module facade for PowerPilot.

Ingests a DatasetProfile enriched by Schema Analyzer and Entity Detector,
evaluates all registered domain plugins, ranks candidates by confidence,
and enriches the DatasetProfile.
"""

from app.common.enums import DatasetDomain
from app.common.logger import get_logger
from app.core.config import get_settings
from app.intelligence.domain.base_domain_classifier import BaseDomainClassifier
from app.intelligence.domain.classifiers import DOMAIN_CLASSIFIER_REGISTRY
from app.models.dataset_profile import DatasetProfile
from app.models.domain_detection_result import DomainDetectionResult

logger = get_logger("DomainClassifier")


class DomainClassifier:
    """
    Facade orchestrating domain classification across registered domain plugins.

    Evaluates each registered domain plugin against a DatasetProfile,
    ranks the candidate domains by confidence descending, enriches the profile,
    and returns the ranked candidates list.
    """

    def __init__(self, min_confidence: float | None = None) -> None:
        """Initialize all registered domain classifier plugins.

        ``min_confidence`` defaults to the configured threshold. Below it a
        dataset is reported as UNKNOWN rather than given the best of several weak
        guesses -- a label like "RETAIL" carries the same visual weight at 25%
        confidence as at 80%, and every downstream engine (KPI templates,
        dashboard layout, strategic decisions) builds on it as though it were
        established. Each of those engines has a generic fallback for UNKNOWN,
        so admitting uncertainty degrades gracefully.
        """
        self._min_confidence = (
            get_settings().min_domain_confidence if min_confidence is None else min_confidence
        )
        self._classifiers: list[BaseDomainClassifier] = [
            classifier_cls() for classifier_cls in DOMAIN_CLASSIFIER_REGISTRY
        ]

    def classify(self, profile: DatasetProfile) -> list[DomainDetectionResult]:
        """
        Classify the business domain of a DatasetProfile.

        Parameters
        ----------
        profile : DatasetProfile
            The dataset profile enriched by Schema Analyzer and Entity Detector.

        Returns
        -------
        list[DomainDetectionResult]
            Ranked candidate domain classification results ordered by confidence descending.
        """
        candidate_results: list[DomainDetectionResult] = []

        for classifier in self._classifiers:
            try:
                result = classifier.classify(profile)
                if result is not None:
                    candidate_results.append(result)
            except Exception:
                # Individual classifier failure should not break the pipeline
                continue

        # Sort candidate results by confidence descending; tiebreaker by domain value
        ranked_candidates = sorted(
            candidate_results,
            key=lambda r: (r.confidence, r.domain.value),
            reverse=True,
        )

        # Enrich DatasetProfile
        if ranked_candidates and ranked_candidates[0].confidence >= self._min_confidence:
            profile.detected_domain = ranked_candidates[0].domain
            profile.domain_confidence = ranked_candidates[0].confidence
        else:
            if ranked_candidates:
                best = ranked_candidates[0]
                logger.info(
                    f"'{profile.dataset_name}' classified as UNKNOWN: the strongest "
                    f"candidate was {best.domain.value} at {best.confidence:.2f}, below "
                    f"the {self._min_confidence:.2f} threshold. Ranked candidates remain "
                    "on the profile."
                )
            profile.detected_domain = DatasetDomain.UNKNOWN
            profile.domain_confidence = 0.0

        # Kept regardless of the outcome, so a rejected best guess is still
        # inspectable rather than silently discarded.

        profile.candidate_domains = ranked_candidates

        return ranked_candidates
