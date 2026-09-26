from dataclasses import dataclass

@dataclass
class DetectedEntity:
    """
    Represents a semantic entity detected from a dataset column.
    """

    column_name: str

    entity_type: str

    confidence: float

    reason: str