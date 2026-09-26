"""
Domain Classifier module facade for PowerPilot.

Ingests a DatasetProfile enriched by Schema Analyzer and Entity Detector,
evaluates all registered domain plugins, ranks candidates by confidence,
and enriches the DatasetProfile.
"""

from app.common.enums import DatasetDomain
from app.intelligence.domain.base_domain_classifier import BaseDomainClassifier
from app.intelligence.domain.classifiers import DOMAIN_CLASSIFIER_REGISTRY
from app.models.dataset_profile import DatasetProfile
from app.models.domain_detection_result import DomainDetectionResult


class DomainClassifier:
    """
    Facade orchestrating domain classification across registered domain plugins.

    Evaluates each registered domain plugin against a DatasetProfile,
    ranks the candidate domains by confidence descending, enriches the profile,
    and returns the ranked candidates list.
    """

    _MIN_DOMAIN_CONFIDENCE_THRESHOLD: float = 0.20

    def __init__(self) -> None:
        """Initialize all registered domain classifier plugins."""
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
        if ranked_candidates and ranked_candidates[0].confidence >= self._MIN_DOMAIN_CONFIDENCE_THRESHOLD:
            profile.detected_domain = ranked_candidates[0].domain
            profile.domain_confidence = ranked_candidates[0].confidence
        else:
            profile.detected_domain = DatasetDomain.UNKNOWN
            profile.domain_confidence = 0.0

        profile.candidate_domains = ranked_candidates

        return ranked_candidates
