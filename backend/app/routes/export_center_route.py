"""Export & Distribution Center endpoints.

Every export addresses a registered dataset by id. Previously each of these
re-accepted the CSV upload and re-ran all 12 pipeline stages, so downloading a
PDF and an Excel package meant analyzing the same file twice.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from app.common.logger import get_logger
from app.datasets.service import DatasetAnalysis, DatasetService, get_dataset_service
from app.export_center.export_center_facade import EnterpriseExportCenter
from app.export_center.models.export_models import BrandingConfig
from app.export_center.services.export_history_service import ExportHistoryService

router = APIRouter(prefix="/api/v1/export-center", tags=["Export & Distribution Center"])
logger = get_logger("ExportCenterRoute")

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _stem(filename: str) -> str:
    """Filename without its .csv extension, for naming downloads."""
    return filename[:-4] if filename.lower().endswith(".csv") else filename


def _attachment(content: bytes, filename: str, media_type: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _branding(company_name: str, prepared_for: str, prepared_by: str) -> BrandingConfig:
    return BrandingConfig(
        company_name=company_name,
        prepared_for=prepared_for,
        prepared_by=prepared_by,
    )


@router.get("/history")
def get_export_history(limit: int = Query(50, ge=1, le=200)):
    """Recent export activity across all datasets."""
    return {"status": "success", "history": ExportHistoryService.get_history(limit=limit)}


@router.post("/{dataset_id}/cleaned-data")
def export_cleaned_data(
    dataset_id: str,
    format: str = Query("csv", pattern="^(csv|xlsx|excel)$"),
    service: DatasetService = Depends(get_dataset_service),
):
    """Export the post-Stage-1 cleaned dataset as CSV, or as the 8-sheet Excel audit package.

    This exports ``cleaned_dataframe`` -- the frame that actually came out of the
    Data Quality & Preparation Engine. The previous implementation passed the raw
    upload here, so a download labelled "cleaned" contained uncleaned rows and the
    workbook's "Original vs Cleaned" comparison reported wrong counts on both sides.
    """
    analysis: DatasetAnalysis = service.get_analysis(dataset_id)
    content = EnterpriseExportCenter.export_cleaned_data(
        analysis.cleaned_dataframe, analysis.result, fmt=format
    )

    is_excel = format.lower() in {"xlsx", "excel"}
    extension = "xlsx" if is_excel else "csv"
    media_type = XLSX_MEDIA_TYPE if is_excel else "text/csv"

    logger.info(
        f"Exported cleaned data ({extension}) for dataset {dataset_id}: "
        f"{len(analysis.cleaned_dataframe)} cleaned rows from "
        f"{analysis.record.original_rows} uploaded"
    )
    return _attachment(content, f"Cleaned_{_stem(analysis.record.filename)}.{extension}", media_type)


@router.post("/{dataset_id}/pdf")
def export_pdf_report(
    dataset_id: str,
    company_name: str = Query("Enterprise Organization"),
    prepared_for: str = Query("Executive Leadership Team"),
    prepared_by: str = Query("PowerPilot AI Platform"),
    service: DatasetService = Depends(get_dataset_service),
):
    """Executive magazine-style PDF report."""
    analysis = service.get_analysis(dataset_id)
    content = EnterpriseExportCenter.export_pdf_report(
        analysis.result, branding=_branding(company_name, prepared_for, prepared_by)
    )
    filename = f"PowerPilot_Executive_Report_{_stem(analysis.record.filename)}.pdf"
    logger.info(f"Exported PDF report for dataset {dataset_id} ({len(content)} bytes)")
    return _attachment(content, filename, "application/pdf")


@router.post("/{dataset_id}/docx")
def export_docx_report(
    dataset_id: str,
    company_name: str = Query("Enterprise Organization"),
    prepared_for: str = Query("Executive Leadership Team"),
    prepared_by: str = Query("PowerPilot AI Platform"),
    service: DatasetService = Depends(get_dataset_service),
):
    """Executive Word document report."""
    analysis = service.get_analysis(dataset_id)
    content = EnterpriseExportCenter.export_docx_report(
        analysis.result, branding=_branding(company_name, prepared_for, prepared_by)
    )
    filename = f"PowerPilot_Executive_Report_{_stem(analysis.record.filename)}.docx"
    logger.info(f"Exported DOCX report for dataset {dataset_id} ({len(content)} bytes)")
    return _attachment(content, filename, DOCX_MEDIA_TYPE)


@router.post("/{dataset_id}/html")
def export_html_report(
    dataset_id: str,
    company_name: str = Query("Enterprise Organization"),
    prepared_for: str = Query("Executive Leadership Team"),
    prepared_by: str = Query("PowerPilot AI Platform"),
    service: DatasetService = Depends(get_dataset_service),
):
    """Standalone interactive HTML report."""
    analysis = service.get_analysis(dataset_id)
    content = EnterpriseExportCenter.export_html_report(
        analysis.result, branding=_branding(company_name, prepared_for, prepared_by)
    )
    filename = f"PowerPilot_Interactive_Report_{_stem(analysis.record.filename)}.html"
    logger.info(f"Exported HTML report for dataset {dataset_id} ({len(content)} bytes)")
    return _attachment(content, filename, "text/html")


@router.post("/{dataset_id}/json")
def export_master_json(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """Full machine-readable analysis as JSON."""
    analysis = service.get_analysis(dataset_id)
    content = EnterpriseExportCenter.export_json(analysis.result)
    filename = f"PowerPilot_Intelligence_{_stem(analysis.record.filename)}.json"
    logger.info(f"Exported master JSON for dataset {dataset_id} ({len(content)} bytes)")
    return _attachment(content, filename, "application/json")


@router.post("/{dataset_id}/email", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def email_report_distribution(
    dataset_id: str,
    recipients: str = Query(..., description="Comma separated recipient email addresses"),
    service: DatasetService = Depends(get_dataset_service),
):
    """Email distribution -- NOT YET IMPLEMENTED.

    This endpoint previously built a PDF, called a service that did nothing but
    ``await asyncio.sleep(0.5)``, and returned ``{"status": "success"}``. No mail
    was ever sent, and the UI showed a success toast for it.

    It now fails explicitly until real SMTP delivery is wired up, because a
    silently-discarded report is worse than a visible error. The dataset id is
    still validated so the eventual implementation has the contract it needs.
    """
    analysis = service.get_analysis(dataset_id)
    recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]

    logger.warning(
        f"Rejected email distribution request for dataset {dataset_id} "
        f"({len(recipient_list)} recipient(s)): SMTP delivery is not implemented"
    )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Email distribution is not implemented yet. No message was sent. "
            f"Download the report for '{analysis.record.filename}' and attach it manually, "
            "or track this feature until SMTP delivery is configured."
        ),
    )


@router.post("/{dataset_id}/data-dictionary")
def export_data_dictionary(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """Technical data dictionary workbook."""
    analysis = service.get_analysis(dataset_id)
    content = EnterpriseExportCenter.export_data_dictionary(analysis.result)
    filename = f"PowerPilot_Data_Dictionary_{_stem(analysis.record.filename)}.xlsx"
    logger.info(f"Exported data dictionary for dataset {dataset_id} ({len(content)} bytes)")
    return _attachment(content, filename, XLSX_MEDIA_TYPE)
