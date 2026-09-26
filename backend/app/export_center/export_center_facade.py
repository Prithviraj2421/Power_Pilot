import time
from typing import Optional
import pandas as pd

from app.export_center.builders.docx_builder import DocxExportBuilder
from app.export_center.builders.excel_builder import ExcelExportBuilder
from app.export_center.builders.html_builder import HtmlExportBuilder
from app.export_center.builders.json_builder import JsonExportBuilder
from app.export_center.builders.pdf_builder import PdfExportBuilder
from app.export_center.models.export_models import BrandingConfig, ExportFormat, ExportHistoryEntry
from app.export_center.services.export_history_service import ExportHistoryService
from app.models.master_intelligence_result import MasterIntelligenceResult
from app.services.powerbi_export_service import PowerBIExportService


class EnterpriseExportCenter:
    """
    Master Export & Distribution Center Facade executing multi-format report builders.
    """

    @staticmethod
    def export_cleaned_data(df: pd.DataFrame, result: MasterIntelligenceResult, fmt: str = "csv") -> bytes:
        t0 = time.time()
        if fmt.lower() == "xlsx" or fmt.lower() == "excel":
            content = ExcelExportBuilder.build_cleaned_excel(df, result)
            export_fmt = ExportFormat.CLEANED_EXCEL
        else:
            content = df.to_csv(index=False).encode("utf-8")
            export_fmt = ExportFormat.CLEANED_CSV

        duration_ms = (time.time() - t0) * 1000
        ExportHistoryService.record_export(
            dataset_name=result.dataset_profile.dataset_name,
            export_format=export_fmt,
            file_size_bytes=len(content),
            duration_ms=duration_ms,
        )
        return content

    @staticmethod
    def export_pdf_report(result: MasterIntelligenceResult, branding: BrandingConfig = BrandingConfig()) -> bytes:
        t0 = time.time()
        content = PdfExportBuilder.build_executive_pdf(result, branding=branding)
        duration_ms = (time.time() - t0) * 1000
        ExportHistoryService.record_export(
            dataset_name=result.dataset_profile.dataset_name,
            export_format=ExportFormat.EXECUTIVE_PDF,
            file_size_bytes=len(content),
            duration_ms=duration_ms,
        )
        return content

    @staticmethod
    def export_docx_report(result: MasterIntelligenceResult, branding: BrandingConfig = BrandingConfig()) -> bytes:
        t0 = time.time()
        content = DocxExportBuilder.build_executive_docx(result, branding=branding)
        duration_ms = (time.time() - t0) * 1000
        ExportHistoryService.record_export(
            dataset_name=result.dataset_profile.dataset_name,
            export_format=ExportFormat.EXECUTIVE_DOCX,
            file_size_bytes=len(content),
            duration_ms=duration_ms,
        )
        return content

    @staticmethod
    def export_html_report(result: MasterIntelligenceResult, branding: BrandingConfig = BrandingConfig()) -> bytes:
        t0 = time.time()
        content = HtmlExportBuilder.build_executive_html(result, branding=branding)
        duration_ms = (time.time() - t0) * 1000
        ExportHistoryService.record_export(
            dataset_name=result.dataset_profile.dataset_name,
            export_format=ExportFormat.INTERACTIVE_HTML,
            file_size_bytes=len(content),
            duration_ms=duration_ms,
        )
        return content

    @staticmethod
    def export_json(result: MasterIntelligenceResult) -> bytes:
        t0 = time.time()
        content = JsonExportBuilder.build_master_json(result)
        duration_ms = (time.time() - t0) * 1000
        ExportHistoryService.record_export(
            dataset_name=result.dataset_profile.dataset_name,
            export_format=ExportFormat.MASTER_JSON,
            file_size_bytes=len(content),
            duration_ms=duration_ms,
        )
        return content

    @staticmethod
    def export_data_dictionary(result: MasterIntelligenceResult) -> bytes:
        t0 = time.time()
        content = ExcelExportBuilder.build_data_dictionary(result)
        duration_ms = (time.time() - t0) * 1000
        ExportHistoryService.record_export(
            dataset_name=result.dataset_profile.dataset_name,
            export_format=ExportFormat.DATA_DICTIONARY,
            file_size_bytes=len(content),
            duration_ms=duration_ms,
        )
        return content
