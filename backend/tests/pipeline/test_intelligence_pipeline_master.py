import pandas as pd
import pytest

from app.common.enums import DatasetDomain
from app.models.master_intelligence_result import MasterIntelligenceResult
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline


def test_powerpilot_master_intelligence_pipeline_retail() -> None:
    pipeline = PowerPilotIntelligencePipeline()

    df = pd.DataFrame(
        {
            "order_id": [101, 102, 103, 104, 105],
            "customer_id": [1, 2, 1, 3, 2],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
            "sales_amount": [150.0, 200.0, 75.0, 300.0, 120.0],
            "quantity": [2, 3, 1, 4, 2],
            "category": ["Electronics", "Clothing", "Electronics", "Home", "Clothing"],
        }
    )

    result = pipeline.run_pipeline(df, dataset_name="retail_sales.csv")

    assert isinstance(result, MasterIntelligenceResult)
    assert result.dataset_profile.dataset_name == "retail_sales.csv"
    assert result.dataset_profile.detected_domain == DatasetDomain.RETAIL
    assert len(result.detected_entities) >= 3
    assert result.business_profile is not None
    assert result.data_intelligence_report is not None
    assert result.insight_report is not None
    assert result.relationship_report is not None
    assert result.kpi_report is not None
    assert len(result.kpi_report.primary_kpis) == 3
    assert result.dashboard_report is not None
    assert len(result.dashboard_report.tabs) >= 2
    assert result.decision_report is not None
    assert len(result.decision_report.primary_decisions) >= 2


def test_powerpilot_master_intelligence_pipeline_finance() -> None:
    pipeline = PowerPilotIntelligencePipeline()

    df = pd.DataFrame(
        {
            "ledger_id": [1001, 1002, 1003, 1004],
            "posting_date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
            "gross_revenue": [50000.0, 75000.0, 60000.0, 90000.0],
            "operating_expenses": [30000.0, 45000.0, 35000.0, 50000.0],
            "ebitda": [20000.0, 30000.0, 25000.0, 40000.0],
            "account_name": ["Sales", "Services", "Sales", "Consulting"],
        }
    )

    result = pipeline.run_pipeline(df, dataset_name="ledger.csv")

    assert isinstance(result, MasterIntelligenceResult)
    assert result.dataset_profile.detected_domain == DatasetDomain.FINANCE
    assert result.kpi_report is not None
    assert result.decision_report is not None
