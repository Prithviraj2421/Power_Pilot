"""Export & Distribution Center endpoints.

Every export addresses a registered dataset by id. Previously each of these
re-accepted the CSV upload and re-ran all 12 pipeline stages, so downloading a
PDF and an Excel package meant analyzing the same file twice.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from app.common.logger import get_logger
from app.core.config import Settings, get_settings
from app.datasets.service import DatasetAnalysis, DatasetService, get_dataset_service
from app.export_center.export_center_facade import EnterpriseExportCenter
from app.export_center.models.export_models import BrandingConfig
from app.export_center.services.email_service import (
    EmailDeliveryError,
    EmailDeliveryService,
    EmailMessageSpec,
    InvalidRecipientError,
    parse_recipients,
)
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
def get_export_history(
    limit: int = Query(50, ge=1, le=200),
    dataset_id: str | None = Query(None, description="Restrict history to one dataset"),
):
    """Recent export activity, newest first.

    Persisted to SQLite, so this survives a server restart -- it was an in-process
    list that reset on every boot while being presented as an audit history.
    """
    return {
        "status": "success",
        "total": ExportHistoryService.count(dataset_id=dataset_id),
        "history": ExportHistoryService.get_history(limit=limit, dataset_id=dataset_id),
    }


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
        analysis.cleaned_dataframe, analysis.result, fmt=format, dataset_id=dataset_id
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
        analysis.result,
        branding=_branding(company_name, prepared_for, prepared_by),
        dataset_id=dataset_id,
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
        analysis.result,
        branding=_branding(company_name, prepared_for, prepared_by),
        dataset_id=dataset_id,
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
        analysis.result,
        branding=_branding(company_name, prepared_for, prepared_by),
        dataset_id=dataset_id,
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
    content = EnterpriseExportCenter.export_json(analysis.result, dataset_id=dataset_id)
    filename = f"PowerPilot_Intelligence_{_stem(analysis.record.filename)}.json"
    logger.info(f"Exported master JSON for dataset {dataset_id} ({len(content)} bytes)")
    return _attachment(content, filename, "application/json")


@router.get("/email/status")
def email_delivery_status(settings: Settings = Depends(get_settings)):
    """Whether outbound email is configured, so the UI can say so before asking.

    Credentials are never echoed -- only whether a host and sender exist.
    """
    return {
        "status": "success",
        "enabled": settings.email_enabled,
        "smtp_host": settings.smtp_host or None,
        "from_address": settings.smtp_from_address or None,
        "max_recipients": settings.max_email_recipients,
        "detail": (
            "Email delivery is configured."
            if settings.email_enabled
            else (
                "Email delivery is not configured. Set POWERPILOT_SMTP_HOST and "
                "POWERPILOT_SMTP_FROM_ADDRESS (see backend/.env.example)."
            )
        ),
    }


@router.post("/{dataset_id}/email")
def email_report_distribution(
    dataset_id: str,
    recipients: str = Query(..., description="Comma separated recipient email addresses"),
    subject: str = Query("PowerPilot Executive BI Report"),
    body_message: str = Query(
        "Please find attached the executive intelligence report generated by PowerPilot."
    ),
    attach: str = Query("pdf", pattern="^(pdf|xlsx|both)$"),
    company_name: str = Query("Enterprise Organization"),
    prepared_for: str = Query("Executive Leadership Team"),
    prepared_by: str = Query("PowerPilot AI Platform"),
    service: DatasetService = Depends(get_dataset_service),
    settings: Settings = Depends(get_settings),
):
    """Build the report and deliver it by email over SMTP.

    This reports success only when the mail server accepted at least one
    recipient. The previous implementation awaited ``asyncio.sleep(0.5)`` and
    returned success without contacting any server, so every "distributed" report
    was silently discarded.

    Returns 503 when SMTP is unconfigured, 400 for a bad recipient list, and 502
    when the mail server refused the message.
    """
    analysis = service.get_analysis(dataset_id)
    email_service = EmailDeliveryService(settings=settings)

    if not email_service.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Email delivery is not configured on this server, so no message was "
                "sent. Set POWERPILOT_SMTP_HOST and POWERPILOT_SMTP_FROM_ADDRESS "
                "(see backend/.env.example), or download the report instead."
            ),
        )

    try:
        recipient_list = parse_recipients(recipients, settings.max_email_recipients)
    except InvalidRecipientError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    branding = _branding(company_name, prepared_for, prepared_by)
    stem = _stem(analysis.record.filename)
    attachments: dict[str, bytes] = {}

    if attach in ("pdf", "both"):
        attachments[f"PowerPilot_Executive_Report_{stem}.pdf"] = (
            EnterpriseExportCenter.export_pdf_report(
                analysis.result, branding=branding, dataset_id=dataset_id
            )
        )
    if attach in ("xlsx", "both"):
        attachments[f"Cleaned_{stem}.xlsx"] = EnterpriseExportCenter.export_cleaned_data(
            analysis.cleaned_dataframe, analysis.result, fmt="xlsx", dataset_id=dataset_id
        )

    spec = EmailMessageSpec(
        recipients=recipient_list,
        subject=subject,
        body=body_message,
        attachments=attachments,
    )

    try:
        result = email_service.send(spec)
    except EmailDeliveryError as exc:
        # The mail server is upstream of this API, so its failure is a bad gateway.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return {**result, "dataset_id": dataset_id, "dataset_name": analysis.record.filename}


@router.post("/{dataset_id}/data-dictionary")
def export_data_dictionary(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """Technical data dictionary workbook."""
    analysis = service.get_analysis(dataset_id)
    content = EnterpriseExportCenter.export_data_dictionary(analysis.result, dataset_id=dataset_id)
    filename = f"PowerPilot_Data_Dictionary_{_stem(analysis.record.filename)}.xlsx"
    logger.info(f"Exported data dictionary for dataset {dataset_id} ({len(content)} bytes)")
    return _attachment(content, filename, XLSX_MEDIA_TYPE)
