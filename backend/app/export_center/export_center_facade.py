import time
from typing import Callable, Optional

import pandas as pd

from app.export_center.builders.docx_builder import DocxExportBuilder
from app.export_center.builders.excel_builder import ExcelExportBuilder
from app.export_center.builders.html_builder import HtmlExportBuilder
from app.export_center.builders.json_builder import JsonExportBuilder
from app.export_center.builders.pdf_builder import PdfExportBuilder
from app.export_center.models.export_models import BrandingConfig, ExportFormat
from app.export_center.services.export_history_service import ExportHistoryService
from app.models.master_intelligence_result import MasterIntelligenceResult


class EnterpriseExportCenter:
    """
    Master Export & Distribution Center Facade executing multi-format report builders.
    """

    @staticmethod
    def _build_and_record(
        build: Callable[[], bytes],
        result: MasterIntelligenceResult,
        export_format: ExportFormat,
        dataset_id: Optional[str] = None,
    ) -> bytes:
        """Run a builder, time it, and record the export in history.

        Every public method below shared this identical timing-and-recording
        preamble; it lives in one place so a change to how exports are audited
        cannot drift between formats.
        """
        started = time.perf_counter()
        content = build()
        duration_ms = (time.perf_counter() - started) * 1000

        ExportHistoryService.record_export(
            dataset_name=result.dataset_profile.dataset_name,
            export_format=export_format,
            file_size_bytes=len(content),
            duration_ms=duration_ms,
            dataset_id=dataset_id,
        )
        return content

    @staticmethod
    def export_cleaned_data(
        df: pd.DataFrame,
        result: MasterIntelligenceResult,
        fmt: str = "csv",
        dataset_id: Optional[str] = None,
    ) -> bytes:
        """Export the cleaned dataset.

        ``df`` must be the post-Stage-1 cleaned frame. ExcelExportBuilder derives
        the original row count as ``len(df) + rows_removed``, so handing it the raw
        upload makes both sides of the "Original vs Cleaned" comparison wrong.
        """
        is_excel = fmt.lower() in {"xlsx", "excel"}
        export_format = ExportFormat.CLEANED_EXCEL if is_excel else ExportFormat.CLEANED_CSV

        def build() -> bytes:
            if is_excel:
                return ExcelExportBuilder.build_cleaned_excel(df, result)
            return df.to_csv(index=False).encode("utf-8")

        return EnterpriseExportCenter._build_and_record(
            build, result, export_format, dataset_id
        )

    @staticmethod
    def export_pdf_report(
        result: MasterIntelligenceResult,
        branding: BrandingConfig = BrandingConfig(),
        dataset_id: Optional[str] = None,
    ) -> bytes:
        return EnterpriseExportCenter._build_and_record(
            lambda: PdfExportBuilder.build_executive_pdf(result, branding=branding),
            result,
            ExportFormat.EXECUTIVE_PDF,
            dataset_id,
        )

    @staticmethod
    def export_docx_report(
        result: MasterIntelligenceResult,
        branding: BrandingConfig = BrandingConfig(),
        dataset_id: Optional[str] = None,
    ) -> bytes:
        return EnterpriseExportCenter._build_and_record(
            lambda: DocxExportBuilder.build_executive_docx(result, branding=branding),
            result,
            ExportFormat.EXECUTIVE_DOCX,
            dataset_id,
        )

    @staticmethod
    def export_html_report(
        result: MasterIntelligenceResult,
        branding: BrandingConfig = BrandingConfig(),
        dataset_id: Optional[str] = None,
    ) -> bytes:
        return EnterpriseExportCenter._build_and_record(
            lambda: HtmlExportBuilder.build_executive_html(result, branding=branding),
            result,
            ExportFormat.INTERACTIVE_HTML,
            dataset_id,
        )

    @staticmethod
    def export_json(
        result: MasterIntelligenceResult, dataset_id: Optional[str] = None
    ) -> bytes:
        return EnterpriseExportCenter._build_and_record(
            lambda: JsonExportBuilder.build_master_json(result),
            result,
            ExportFormat.MASTER_JSON,
            dataset_id,
        )

    @staticmethod
    def export_data_dictionary(
        result: MasterIntelligenceResult, dataset_id: Optional[str] = None
    ) -> bytes:
        return EnterpriseExportCenter._build_and_record(
            lambda: ExcelExportBuilder.build_data_dictionary(result),
            result,
            ExportFormat.DATA_DICTIONARY,
            dataset_id,
        )
