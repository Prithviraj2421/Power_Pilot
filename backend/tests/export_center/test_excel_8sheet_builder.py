import io
import openpyxl
import pandas as pd
import pytest

from app.export_center.builders.excel_builder import ExcelExportBuilder
from app.export_center.builders.pdf_builder import PdfExportBuilder
from app.export_center.models.export_models import BrandingConfig, ExportFormat, PageBudgetConfig, SmartMetricFilter
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline


def test_excel_8sheet_audit_package_builder() -> None:
    df = pd.DataFrame(
        {
            "order_id": [1, 2, 3, 4],
            "customer_id": ["C101", "C102", "C103", "C104"],
            "sales": ["$150.00", "$250.00", "$350.00", "$450.00"],
            "profit": [30.0, 50.0, 70.0, 90.0],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
        }
    )
    pipeline = PowerPilotIntelligencePipeline()
    result = pipeline.run_pipeline(df, dataset_name="Retail_Sales_2024.csv")

    xlsx_bytes = ExcelExportBuilder.build_cleaned_excel(df, result)
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 0

    # Inspect Workbook Sheet Names & Structure
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    expected_sheets = [
        "Read Me",
        "Cleaned Dataset",
        "Cleaning Summary",
        "Data Quality Scorecard",
        "Original vs Cleaned",
        "Data Dictionary",
        "Audit Metadata",
        "Business Rule Validation",
    ]

    for sheet_name in expected_sheets:
        assert sheet_name in wb.sheetnames, f"Missing required sheet: {sheet_name}"


def test_smart_metric_filtering() -> None:
    cols = ["order_id", "customer_id", "Sales", "Profit", "Quantity", "row_num"]
    business_cols = SmartMetricFilter.filter_business_columns(cols)
    assert business_cols == ["Sales", "Profit", "Quantity"]


def test_pdf_page_budget_calculator() -> None:
    df = pd.DataFrame({"order_id": [1, 2], "sales": [10.0, 20.0]})
    pipeline = PowerPilotIntelligencePipeline()
    result = pipeline.run_pipeline(df, dataset_name="SmallTest.csv")

    budget = PdfExportBuilder.calculate_page_budget(result)
    assert budget.dataset_scale == "SMALL"
    assert budget.min_pages == 6
    assert budget.max_pages == 8
