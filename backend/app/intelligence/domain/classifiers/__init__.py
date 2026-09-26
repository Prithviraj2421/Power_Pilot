"""
Domain classifier plugin registry.

Exports all concrete domain classifier classes and the canonical priority registry.
"""

from app.intelligence.domain.base_domain_classifier import BaseDomainClassifier
from app.intelligence.domain.classifiers.finance_classifier import FinanceClassifier
from app.intelligence.domain.classifiers.healthcare_classifier import HealthcareClassifier
from app.intelligence.domain.classifiers.hr_classifier import HRClassifier
from app.intelligence.domain.classifiers.logistics_classifier import LogisticsClassifier
from app.intelligence.domain.classifiers.marketing_classifier import MarketingClassifier
from app.intelligence.domain.classifiers.retail_classifier import RetailClassifier

DOMAIN_CLASSIFIER_REGISTRY: tuple[type[BaseDomainClassifier], ...] = (
    RetailClassifier,
    FinanceClassifier,
    HRClassifier,
    HealthcareClassifier,
    MarketingClassifier,
    LogisticsClassifier,
)

__all__ = [
    "BaseDomainClassifier",
    "RetailClassifier",
    "FinanceClassifier",
    "HRClassifier",
    "HealthcareClassifier",
    "MarketingClassifier",
    "LogisticsClassifier",
    "DOMAIN_CLASSIFIER_REGISTRY",
]
