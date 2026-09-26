from dataclasses import dataclass, field
from typing import Optional

from app.common.enums import DatasetDomain


@dataclass(slots=True, frozen=True)
class DecisionAction:
    """
    Immutable strategic action recommendation produced by the Decision Engine.
    """

    action_title: str
    description: str
    target_entity: str
    urgency: str  # 'IMMEDIATE', 'SHORT_TERM', 'MEDIUM_TERM', 'LONG_TERM'
    expected_roi: str
    risk_level: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    confidence: float
    reasoning: str
    supporting_evidence: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class ScenarioOption:
    """
    Immutable scenario analysis option evaluating alternative strategic paths.
    """

    scenario_name: str
    description: str
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    projected_impact: str = ""
    probability_of_success: float = 0.0


@dataclass(slots=True, frozen=True)
class DecisionReport:
    """
    Unified immutable report detailing executive decision actions, scenarios, and risk matrix.
    """

    executive_decision_summary: str
    domain: DatasetDomain = DatasetDomain.UNKNOWN
    primary_decisions: tuple[DecisionAction, ...] = field(default_factory=tuple)
    scenario_options: tuple[ScenarioOption, ...] = field(default_factory=tuple)
    risk_matrix_summary: str = ""
    all_decisions: tuple[DecisionAction, ...] = field(default_factory=tuple)
