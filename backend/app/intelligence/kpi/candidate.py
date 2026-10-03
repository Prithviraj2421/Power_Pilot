from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.common.enums import Priority
from app.intelligence.kpi.ir import Expr


@dataclass(frozen=True)
class KPICandidate:
    """What a KPI plugin proposes: a named expression over real columns, not yet verified.

    The engine compiles it, verifies it against the data, and only then turns it into a
    ``KPIRecommendation``. ``example_target`` is a conventional benchmark the plugin knows
    about; it is never shown as if it came from the user's data.
    """

    name: str
    priority: Priority
    confidence: float
    reason: str
    expression: Expr
    business_impact: Optional[str] = None
    example_target: Optional[str] = None
