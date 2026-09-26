from dataclasses import dataclass
from datetime import datetime
import pandas as pd

@dataclass
class DatasetVersion:

    version: int

    timestamp: datetime

    dataframe: pd.DataFrame

    quality_score: int

    state: str

    operation: str

    description: str