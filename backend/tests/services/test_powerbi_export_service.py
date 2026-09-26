import pytest
from app.common.enums import DatasetDomain, PhysicalType, Priority, SemanticType
from app.models.column_profile import ColumnProfile
from app.models.dataset_profile import DatasetProfile
from app.models.kpi_recommendation import KPIRecommendation
from app.models.kpi_report import KPIReport
from app.models.relationship_models import EntityRelationship, RelationshipReport
from app.services.powerbi_export_service import PowerBIExportService


def test_generate_dax_script() -> None:
    kpi_report = KPIReport(
        primary_kpis=(
            KPIRecommendation(
                name="Total Sales",
                priority=Priority.CRITICAL,
                confidence=0.95,
                reason="Primary revenue metric",
                formula="SUM('Sales'[Sales_Amount])",
                target_threshold="> $100,000",
                business_impact="Direct revenue growth",
            ),
        ),
        domain=DatasetDomain.RETAIL,
        total_kpis_recommended=1,
    )

    script = PowerBIExportService.generate_dax_script(kpi_report, dataset_name="Sales.csv")
    assert isinstance(script, str)
    assert "// Dataset: Sales.csv" in script
    assert "Total_Sales = SUM('Sales'[Sales_Amount])" in script


def test_generate_tabular_model_bim() -> None:
    cols = [
        ColumnProfile(name="order_id", physical_type=PhysicalType.INTEGER, nullable=False, unique=True, identifier=True, missing_count=0, unique_count=100),
        ColumnProfile(name="sales_amount", physical_type=PhysicalType.FLOAT, nullable=False, unique=False, identifier=False, missing_count=0, unique_count=50),
    ]
    profile = DatasetProfile(dataset_name="Orders.csv", total_rows=100, total_columns=2, columns=cols)

    bim = PowerBIExportService.generate_tabular_model_bim(profile)
    assert isinstance(bim, dict)
    assert bim["compatibilityLevel"] == 1500
    assert len(bim["model"]["tables"]) == 1
    tbl = bim["model"]["tables"][0]
    assert tbl["name"] == "Orders"
    assert len(tbl["columns"]) == 2


def test_generate_power_query_m() -> None:
    cols = [
        ColumnProfile(name="order_id", physical_type=PhysicalType.INTEGER, nullable=False, unique=True, identifier=True, missing_count=0, unique_count=100),
    ]
    profile = DatasetProfile(dataset_name="Orders.csv", total_rows=100, total_columns=1, columns=cols)

    m_code = PowerBIExportService.generate_power_query_m(profile)
    assert isinstance(m_code, str)
    assert '{"order_id", Int64.Type}' in m_code
