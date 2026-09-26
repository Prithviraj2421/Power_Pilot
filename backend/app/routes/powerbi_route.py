from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.common.logger import get_logger
from app.core.config import get_settings
from app.datasets.service import DatasetService, get_dataset_service
from app.services.powerbi_export_service import PowerBIExportService

router = APIRouter(prefix="/api/v1/export/powerbi", tags=["Power BI Export"])
logger = get_logger("PowerBIRoute")


@router.get("/status")
def powerbi_connector_status():
    """Status endpoint for Power BI Desktop Web Connector GET requests."""
    settings = get_settings()
    return {
        "status": "online",
        "service": "PowerPilot Enterprise BI Platform",
        "version": settings.app_version,
        "endpoints": {
            "dax": "/api/v1/export/powerbi/{dataset_id}/dax",
            "bim": "/api/v1/export/powerbi/{dataset_id}/bim",
            "m": "/api/v1/export/powerbi/{dataset_id}/m",
        },
    }


@router.post("/{dataset_id}/dax", response_class=PlainTextResponse)
def export_dax_script(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """Generate a formatted .dax measure script for Power BI from a registered dataset."""
    analysis = service.get_analysis(dataset_id)
    script = PowerBIExportService.generate_dax_script(
        analysis.result.kpi_report, dataset_name=analysis.record.filename
    )
    logger.info(f"Generated DAX script for dataset {dataset_id}")
    return PlainTextResponse(content=script, media_type="text/plain")


@router.post("/{dataset_id}/bim")
def export_tabular_bim(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """Generate a Microsoft Analysis Services Tabular Model .bim JSON schema."""
    analysis = service.get_analysis(dataset_id)
    bim = PowerBIExportService.generate_tabular_model_bim(
        dataset_profile=analysis.result.dataset_profile,
        kpi_report=analysis.result.kpi_report,
        relationship_report=analysis.result.relationship_report,
    )
    logger.info(f"Generated Tabular Model BIM for dataset {dataset_id}")
    return bim


@router.post("/{dataset_id}/m", response_class=PlainTextResponse)
def export_power_query_m(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """Generate Power Query M transformation code for a registered dataset."""
    analysis = service.get_analysis(dataset_id)
    script = PowerBIExportService.generate_power_query_m(analysis.result.dataset_profile)
    logger.info(f"Generated Power Query M script for dataset {dataset_id}")
    return PlainTextResponse(content=script, media_type="text/plain")
