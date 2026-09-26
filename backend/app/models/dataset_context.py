from dataclasses import dataclass, field
import pandas as pd
from typing import Optional, Dict, List
from app.models.workflow_state import WorkflowState

@dataclass
class DatasetContext:

    filename: str

    dataframe: pd.DataFrame

    report: Optional[Dict] = None

    cleaning_plan: Optional[Dict] = None

    rule_issues: Optional[List] = field(default_factory=list)

    cleaned_dataframe: Optional[pd.DataFrame] = None

    profile: Optional[Dict] = None

    kpis: Optional[List] = field(default_factory=list)

    recommendations: Optional[List] = field(default_factory=list)

    metadata: Optional[Dict] = field(default_factory=dict)

    state: WorkflowState = WorkflowState.CREATED