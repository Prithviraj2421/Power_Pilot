"""
TypeDetector plugin registry.

Exports all concrete detector classes and the canonical detection
priority order used by the TypeDetector orchestrator.

Detectors are ordered from most specific to least specific to
minimize false positives:

  1. Boolean  — very narrow value set; checked first
  2. Integer  — subset of float; must precede float
  3. Float    — numeric but not integer
  4. Datetime — string-parseable temporal values
  5. Category — low-cardinality strings
  6. Text     — fallback catch-all
"""

from app.intelligence.schema.TypeDetector.base_detector import BaseDetector
from app.intelligence.schema.TypeDetector.boolean_detector import BooleanDetector
from app.intelligence.schema.TypeDetector.integer_detector import IntegerDetector
from app.intelligence.schema.TypeDetector.float_detector import FloatDetector
from app.intelligence.schema.TypeDetector.datetime_detector import DatetimeDetector
from app.intelligence.schema.TypeDetector.category_detector import CategoryDetector
from app.intelligence.schema.TypeDetector.text_detector import TextDetector

# Canonical detection priority order (most specific → least specific)
DETECTOR_PRIORITY: tuple[type[BaseDetector], ...] = (
    BooleanDetector,
    IntegerDetector,
    FloatDetector,
    DatetimeDetector,
    CategoryDetector,
    TextDetector,
)

__all__ = [
    "BaseDetector",
    "BooleanDetector",
    "IntegerDetector",
    "FloatDetector",
    "DatetimeDetector",
    "CategoryDetector",
    "TextDetector",
    "DETECTOR_PRIORITY",
]
