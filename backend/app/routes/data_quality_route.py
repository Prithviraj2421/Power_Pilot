import io
from fastapi import APIRouter, File, HTTPException, UploadFile, status
import pandas as pd

from app.common.logger import get_logger
from app.data_quality.dqpe_facade import DataQualityPreparationEngine
from app.models.data_quality_models import PreparationConfig

router = APIRouter(prefix="/api/v1/quality", tags=["Data Quality & Preparation"])
dqpe = DataQualityPreparationEngine()
logger = get_logger("QualityRoute")


@router.post("/assess")
def assess_data_quality(file: UploadFile = File(...)):
    """
    Run Phase 1 Data Quality Assessment on uploaded CSV dataset.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a valid .csv file.")

    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        quality_report = dqpe.assess_quality(df, dataset_name=file.filename)
        return {
            "status": "success",
            "quality_report": quality_report,
        }
    except Exception as e:
        logger.error(f"Error assessing data quality: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error executing Data Quality Assessment: {str(e)}")


@router.post("/prepare")
def prepare_data(file: UploadFile = File(...)):
    """
    Run Phase 2 Configurable Data Preparation & Standardization.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a valid .csv file.")

    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        cleaned_df, prep_report = dqpe.prepare_data(df, config=PreparationConfig(), dataset_name=file.filename)
        return {
            "status": "success",
            "preparation_report": prep_report,
            "cleaned_summary": {
                "rows": len(cleaned_df),
                "columns": len(cleaned_df.columns),
            },
        }
    except Exception as e:
        logger.error(f"Error preparing data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error executing Data Preparation: {str(e)}")
