from fastapi import APIRouter, Depends, File, UploadFile

from app.common.logger import get_logger
from app.datasets.service import DatasetService, get_dataset_service

router = APIRouter(prefix="/api/v1/intelligence", tags=["Data Intelligence"])
logger = get_logger("IntelligenceRoute")


@router.post("/analyze-csv")
def analyze_csv_dataset(
    file: UploadFile = File(...),
    service: DatasetService = Depends(get_dataset_service),
):
    """Upload and analyze a CSV dataset using the 12-stage Master Intelligence Pipeline.

    The analysis is registered in the dataset registry and the response carries a
    ``dataset_id``. Every downstream operation -- exports, Power BI assets, the
    copilot -- takes that id instead of re-uploading the file, so the pipeline runs
    exactly once per dataset.

    Validation failures raise InvalidDatasetError and unknown ids raise
    DatasetNotFoundError; both are mapped to 400/404 by handlers in app.main.
    """
    payload = file.file.read()
    filename = file.filename or "dataset.csv"

    logger.info(f"Processing CSV analysis request for '{filename}' ({len(payload)} bytes)")
    analysis = service.register(payload, filename)
    result = analysis.result
    logger.info(
        f"Completed intelligence analysis for '{filename}' "
        f"(dataset_id={analysis.dataset_id})"
    )

    return {
        "status": "success",
        "dataset_id": analysis.dataset_id,
        "dataset": analysis.record.to_dict(),
        "dataset_name": analysis.record.filename,
        "detected_domain": result.dataset_profile.detected_domain.value,
        "domain_confidence": result.dataset_profile.domain_confidence,
        "total_rows": result.dataset_profile.total_rows,
        "total_columns": result.dataset_profile.total_columns,
        "summary": {
            "detected_entities_count": len(result.detected_entities),
            "primary_kpis_count": len(result.kpi_report.primary_kpis) if result.kpi_report else 0,
            "dashboard_tabs_count": len(result.dashboard_report.tabs) if result.dashboard_report else 0,
            "primary_decisions_count": (
                len(result.decision_report.primary_decisions) if result.decision_report else 0
            ),
        },
        "result": result,
    }
