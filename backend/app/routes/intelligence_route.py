import io
from fastapi import APIRouter, File, HTTPException, UploadFile, status
import pandas as pd

from app.common.logger import get_logger
from app.models.master_intelligence_result import MasterIntelligenceResult
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline

router = APIRouter(prefix="/api/v1/intelligence", tags=["Data Intelligence"])
pipeline = PowerPilotIntelligencePipeline()
logger = get_logger("IntelligenceRoute")

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB limit


@router.post("/analyze-csv")
def analyze_csv_dataset(file: UploadFile = File(...)):
    """
    Upload and analyze a CSV dataset using the 10-stage Master Intelligence Pipeline.
    """
    if not file.filename.endswith(".csv"):
        logger.warning(f"Rejected invalid file upload extension: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a valid .csv file.",
        )

    try:
        contents = file.file.read()
        if len(contents) == 0:
            logger.warning(f"Rejected empty file upload: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty. Please upload a non-empty CSV dataset.",
            )

        if len(contents) > MAX_FILE_SIZE_BYTES:
            logger.warning(f"Rejected oversized file upload: {file.filename} ({len(contents)} bytes)")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds maximum limit of 50MB.",
            )

        logger.info(f"Processing CSV analysis request for '{file.filename}' ({len(contents)} bytes)")
        df = pd.read_csv(io.BytesIO(contents))

        if df.empty or len(df.columns) == 0:
            logger.warning(f"CSV dataframe has zero rows or zero columns: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The CSV file must contain at least one column with valid data rows.",
            )

        result: MasterIntelligenceResult = pipeline.run_pipeline(df, dataset_name=file.filename)
        logger.info(f"Successfully completed intelligence analysis for '{file.filename}'")

        return {
            "status": "success",
            "dataset_name": file.filename,
            "detected_domain": result.dataset_profile.detected_domain.value,
            "domain_confidence": result.dataset_profile.domain_confidence,
            "total_rows": result.dataset_profile.total_rows,
            "total_columns": result.dataset_profile.total_columns,
            "summary": {
                "detected_entities_count": len(result.detected_entities),
                "primary_kpis_count": len(result.kpi_report.primary_kpis) if result.kpi_report else 0,
                "dashboard_tabs_count": len(result.dashboard_report.tabs) if result.dashboard_report else 0,
                "primary_decisions_count": len(result.decision_report.primary_decisions) if result.decision_report else 0,
            },
            "result": result,
        }

    except HTTPException:
        raise
    except pd.errors.EmptyDataError:
        logger.error(f"Empty data error reading CSV file '{file.filename}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV formatting: file contains no parseable columns or headers.",
        )
    except pd.errors.ParserError as pe:
        logger.error(f"CSV ParserError for '{file.filename}': {str(pe)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed CSV syntax: could not parse row records. Please verify delimiter formatting.",
        )
    except Exception as e:
        logger.error(f"Unexpected pipeline execution failure for '{file.filename}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the dataset. Please verify CSV data formatting.",
        )
