from dataclasses import dataclass
from typing import List

from app.models.issue import Issue


@dataclass
class CleaningPlan:

    current_score: int

    predicted_score: int

    issues: List[Issue]