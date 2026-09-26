from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.common.logger import get_logger
from app.datasets.service import DatasetService, get_dataset_service
from app.intelligence.copilot_engine import CopilotEngine, CopilotResponse

router = APIRouter(prefix="/api/v1/copilot", tags=["AI Copilot"])
logger = get_logger("CopilotRoute")
copilot_engine = CopilotEngine()


class CopilotQuery(BaseModel):
    """A question asked against an already-registered dataset."""

    dataset_id: str = Field(..., min_length=1, description="Id returned by the analyze endpoint")
    query: str = Field(..., min_length=1, max_length=2000, description="Natural language question")


@router.post("/ask")
def ask_copilot(
    payload: CopilotQuery,
    service: DatasetService = Depends(get_dataset_service),
):
    """Answer a natural language BI question grounded in a registered dataset.

    The answer is derived entirely from that dataset's computed analysis -- the
    engine has no generative freedom, so it cannot invent a figure that is not in
    the data. Asking a follow-up costs a cache lookup, not another pipeline run.
    """
    analysis = service.get_analysis(payload.dataset_id)

    logger.info(
        f"Copilot query for dataset {payload.dataset_id} "
        f"('{analysis.record.filename}'): {payload.query[:120]}"
    )
    response: CopilotResponse = copilot_engine.ask(payload.query, analysis.result)

    return {
        "status": "success",
        "dataset_id": payload.dataset_id,
        "dataset_name": analysis.record.filename,
        "query": payload.query,
        "answer": response.answer,
        "intent": response.intent,
        "evidence": list(response.evidence),
        "recommended_actions": list(response.recommended_actions),
        "suggested_followups": list(response.suggested_followups),
    }
