import pandas as pd
import pytest

from app.export_center.export_center_facade import EnterpriseExportCenter
from app.export_center.models.export_models import BrandingConfig, ExportFormat
from app.export_center.services.export_history_service import ExportHistoryService
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline


def test_excel_export_builder() -> None:
    df = pd.DataFrame(
        {
            "order_id": [1, 2, 3],
            "sales": ["$100.00", "$200.00", "$300.00"],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        }
    )
    pipeline = PowerPilotIntelligencePipeline()
    result = pipeline.run_pipeline(df, dataset_name="TestExport.csv")

    xlsx_bytes = EnterpriseExportCenter.export_cleaned_data(df, result, fmt="xlsx")
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 0


def test_pdf_export_builder() -> None:
    df = pd.DataFrame(
        {
            "order_id": [1, 2, 3],
            "sales": ["$100.00", "$200.00", "$300.00"],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        }
    )
    pipeline = PowerPilotIntelligencePipeline()
    result = pipeline.run_pipeline(df, dataset_name="TestExport.csv")

    branding = BrandingConfig(company_name="Acme Corp", prepared_for="Board of Directors")
    pdf_bytes = EnterpriseExportCenter.export_pdf_report(result, branding=branding)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_docx_export_builder() -> None:
    df = pd.DataFrame(
        {
            "order_id": [1, 2, 3],
            "sales": ["$100.00", "$200.00", "$300.00"],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        }
    )
    pipeline = PowerPilotIntelligencePipeline()
    result = pipeline.run_pipeline(df, dataset_name="TestExport.csv")

    docx_bytes = EnterpriseExportCenter.export_docx_report(result)
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 0


def test_html_export_builder() -> None:
    df = pd.DataFrame(
        {
            "order_id": [1, 2, 3],
            "sales": ["$100.00", "$200.00", "$300.00"],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        }
    )
    pipeline = PowerPilotIntelligencePipeline()
    result = pipeline.run_pipeline(df, dataset_name="TestExport.csv")

    html_bytes = EnterpriseExportCenter.export_html_report(result)
    assert b"<!DOCTYPE html>" in html_bytes


def test_json_and_dictionary_builders() -> None:
    df = pd.DataFrame(
        {
            "order_id": [1, 2, 3],
            "sales": ["$100.00", "$200.00", "$300.00"],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        }
    )
    pipeline = PowerPilotIntelligencePipeline()
    result = pipeline.run_pipeline(df, dataset_name="TestExport.csv")

    json_bytes = EnterpriseExportCenter.export_json(result)
    assert b"dataset_name" in json_bytes

    dict_bytes = EnterpriseExportCenter.export_data_dictionary(result)
    assert isinstance(dict_bytes, bytes)
    assert len(dict_bytes) > 0


def test_export_history_recording() -> None:
    history = ExportHistoryService.get_history()
    assert len(history) >= 3
    assert history[0].status == "SUCCESS"
