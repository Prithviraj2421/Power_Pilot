import io
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, PlainTextResponse
import pandas as pd

from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline
from app.services.powerbi_export_service import PowerBIExportService

router = APIRouter(prefix="/api/v1/export/powerbi", tags=["Power BI Export"])
pipeline = PowerPilotIntelligencePipeline()


@router.get("/status")
def powerbi_connector_status():
    """
    Status endpoint for Power BI Desktop Web Connector GET requests.
    """
    return {
        "status": "online",
        "service": "PowerPilot Enterprise BI Platform",
        "version": "1.0.0",
        "endpoints": {
            "dax_post": "/api/v1/export/powerbi/dax",
            "bim_post": "/api/v1/export/powerbi/bim",
            "m_post": "/api/v1/export/powerbi/m",
        },
    }


@router.post("/dax", response_class=PlainTextResponse)
def export_dax_script(file: UploadFile = File(...)):
    """
    Generate and return a formatted .dax measure script for Power BI.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a valid .csv file.")

    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        result = pipeline.run_pipeline(df, dataset_name=file.filename)
        
        dax_script = PowerBIExportService.generate_dax_script(result.kpi_report, dataset_name=file.filename)
        return PlainTextResponse(content=dax_script, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating DAX script: {str(e)}")


@router.post("/bim")
def export_tabular_bim(file: UploadFile = File(...)):
    """
    Generate and return a Microsoft Analysis Services Tabular Model .bim JSON schema.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a valid .csv file.")

    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        result = pipeline.run_pipeline(df, dataset_name=file.filename)
        
        bim_data = PowerBIExportService.generate_tabular_model_bim(
            dataset_profile=result.dataset_profile,
            kpi_report=result.kpi_report,
            relationship_report=result.relationship_report,
        )
        return bim_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating BIM model: {str(e)}")


@router.post("/m", response_class=PlainTextResponse)
def export_power_query_m(file: UploadFile = File(...)):
    """
    Generate and return Power Query (M) data transformation code.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a valid .csv file.")

    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        result = pipeline.run_pipeline(df, dataset_name=file.filename)
        
        m_code = PowerBIExportService.generate_power_query_m(result.dataset_profile)
        return PlainTextResponse(content=m_code, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Power Query M script: {str(e)}")
