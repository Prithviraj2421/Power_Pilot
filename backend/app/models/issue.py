from dataclasses import dataclass

@dataclass
class Issue:

    type: str

    severity: str

    affected_columns: list

    recommendation: str

    expected_improvement: int

    message: str