import io
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
import pandas as pd

from app.intelligence.copilot_engine import CopilotEngine, CopilotResponse
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline

router = APIRouter(prefix="/api/v1/copilot", tags=["AI Copilot"])
pipeline = PowerPilotIntelligencePipeline()
copilot_engine = CopilotEngine()


@router.post("/ask")
def ask_copilot(query: str = Form(...), file: UploadFile = File(...)):
    """
    Process natural language BI question against uploaded dataset.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a valid .csv file.")

    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        result = pipeline.run_pipeline(df, dataset_name=file.filename)
        
        response: CopilotResponse = copilot_engine.ask(query, result)
        return {
            "status": "success",
            "query": query,
            "answer": response.answer,
            "intent": response.intent,
            "evidence": list(response.evidence),
            "recommended_actions": list(response.recommended_actions),
            "suggested_followups": list(response.suggested_followups),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing AI Copilot query: {str(e)}")
