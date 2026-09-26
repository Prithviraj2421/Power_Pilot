import json
from typing import Any
import pandas as pd

from app.models.master_intelligence_result import MasterIntelligenceResult


class JsonExportBuilder:
    """
    Builder serializing MasterIntelligenceResult object into clean JSON bytes.
    """

    @staticmethod
    def _default_serializer(obj: Any) -> Any:
        if hasattr(obj, "value"):
            return obj.value
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return str(obj)

    @classmethod
    def build_master_json(cls, result: MasterIntelligenceResult) -> bytes:
        data = {
            "dataset_name": result.dataset_profile.dataset_name,
            "detected_domain": result.dataset_profile.detected_domain,
            "total_rows": result.dataset_profile.total_rows,
            "total_columns": result.dataset_profile.total_columns,
            "quality_report": result.quality_report,
            "preparation_report": result.preparation_report,
            "business_profile": result.business_profile,
            "data_intelligence_report": result.data_intelligence_report,
            "insight_report": result.insight_report,
            "relationship_report": result.relationship_report,
            "kpi_report": result.kpi_report,
            "dashboard_report": result.dashboard_report,
            "decision_report": result.decision_report,
        }
        json_str = json.dumps(data, default=cls._default_serializer, indent=2)
        return json_str.encode("utf-8")
