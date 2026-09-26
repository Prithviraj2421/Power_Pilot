"""
Entity detector plugin registry.

Exports all concrete semantic entity detector classes and the canonical priority list.
"""

from app.intelligence.entity.base_entity_detector import BaseEntityDetector
from app.intelligence.entity.detectors.cost_detector import CostDetector
from app.intelligence.entity.detectors.customer_detector import CustomerDetector
from app.intelligence.entity.detectors.date_detector import DateDetector
from app.intelligence.entity.detectors.employee_detector import EmployeeDetector
from app.intelligence.entity.detectors.identifier_detector import IdentifierDetector
from app.intelligence.entity.detectors.product_detector import ProductDetector
from app.intelligence.entity.detectors.profit_detector import ProfitDetector
from app.intelligence.entity.detectors.quantity_detector import QuantityDetector
from app.intelligence.entity.detectors.region_detector import RegionDetector
from app.intelligence.entity.detectors.revenue_detector import RevenueDetector

ENTITY_DETECTOR_REGISTRY: tuple[type[BaseEntityDetector], ...] = (
    CustomerDetector,
    ProductDetector,
    RevenueDetector,
    ProfitDetector,
    CostDetector,
    QuantityDetector,
    DateDetector,
    RegionDetector,
    EmployeeDetector,
    IdentifierDetector,
)

__all__ = [
    "BaseEntityDetector",
    "CustomerDetector",
    "ProductDetector",
    "RevenueDetector",
    "ProfitDetector",
    "CostDetector",
    "QuantityDetector",
    "DateDetector",
    "RegionDetector",
    "EmployeeDetector",
    "IdentifierDetector",
    "ENTITY_DETECTOR_REGISTRY",
]
