from dataclasses import dataclass
from datetime import datetime
import pandas as pd

@dataclass
class DatasetVersion:

    version: int

    created_at: datetime

    dataframe: pd.DataFrame

    quality_score: int

    description: str

    operation: str

    