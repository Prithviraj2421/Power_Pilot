from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from app.common.logger import get_logger
from app.core.config import Settings, get_settings
from app.datasets.service import get_dataset_service
from app.powerbi_live.security import TOKEN_HEADER, token_matches
from app.powerbi_live.service import ApplyItem, LiveModelService
from app.powerbi_live.tom_connector import TomAdomdConnector
from app.reverse.errors import ReportReadError
from app.reverse.service import ReportNotFoundError, ReverseService
from app.routes.reverse_route import get_reverse_service

router = APIRouter(prefix="/api/v1/powerbi-live", tags=["Power BI live model"])
logger = get_logger("PowerBILiveRoute")


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tables: Optional[list[str]] = Field(None, max_length=200)
    max_rows: Optional[int] = Field(None, ge=1_000, le=5_000_000)


class ApplyItemModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table: str = Field(min_length=1, max_length=256)
    kpi_id: str = Field(min_length=3, max_length=300)


class ApplyRequest(BaseModel):
    """KPI ids only. DAX is never accepted from a client; the server looks up the verified formula."""

    model_config = ConfigDict(extra="forbid")

    items: list[ApplyItemModel] = Field(min_length=1, max_length=50)
    dry_run: bool = False


class ReverseApplyRequest(BaseModel):
    """Measure ids only. The DAX comes from the server's own proven plan, never from the client."""

    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(min_length=3, max_length=64)
    measure_ids: list[str] = Field(min_length=1, max_length=200)
    dry_run: bool = False


def get_live_settings() -> Settings:
    return get_settings()


def require_live(
    settings: Settings = Depends(get_live_settings),
    supplied: Optional[str] = Header(None, alias=TOKEN_HEADER),
) -> Settings:
    """Only the launcher-started UI may use these endpoints: they can edit the user's report."""
    if not settings.powerbi_live_enabled:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "PowerPilot was not started from Power BI Desktop's External Tools ribbon, so there is no open model.",
        )
    if not token_matches(settings.pbi_token, supplied):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or wrong PowerPilot session token.")
    return settings


@lru_cache(maxsize=1)
def _build_service(server: str, database: str, dll_dir: str, max_rows: int) -> LiveModelService:
    connector = TomAdomdConnector(server, database, dll_dir or None)
    return LiveModelService(connector, get_dataset_service(), max_rows=max_rows)


def get_live_service(settings: Settings = Depends(require_live)) -> LiveModelService:
    try:
        return _build_service(settings.pbi_server, settings.pbi_database, settings.tom_dll_dir, settings.pbi_max_rows)
    except ValueError as exc:  # a malformed address or name in the launch environment
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/status")
def live_status(service: LiveModelService = Depends(get_live_service)) -> dict[str, Any]:
    """Whether the open model is reachable, and which tables it has."""
    return service.status()


@router.post("/analyze")
def analyze_open_model(
    request: AnalyzeRequest, service: LiveModelService = Depends(get_live_service)
) -> dict[str, Any]:
    """Read the model's tables and run the analysis pipeline on each, verifying KPIs on the model's own rows."""
    result = service.analyze(request.tables, request.max_rows)
    logger.info(f"Analysed {len(result['tables'])} table(s) of the open model")
    return result


@router.post("/apply-measures")
def apply_measures(
    request: ApplyRequest, service: LiveModelService = Depends(get_live_service)
) -> dict[str, Any]:
    """Add the chosen verified KPIs to the open model as measures, if Power BI's engine agrees with each."""
    result = service.apply([ApplyItem(i.table, i.kpi_id) for i in request.items], dry_run=request.dry_run)
    written = sum(1 for r in result["results"] if r["status"] == "written")
    logger.info(f"apply-measures dry_run={request.dry_run}: {written} written of {len(request.items)} requested")
    return result


@router.post("/reverse-engineer")
def reverse_engineer_table(
    table: str = Form(..., min_length=1, max_length=256),
    file: UploadFile = File(..., description="The legacy report: .xlsx, .csv or a PDF with tables"),
    live: LiveModelService = Depends(get_live_service),
    reverse: ReverseService = Depends(get_reverse_service),
) -> dict[str, Any]:
    """Find the formula behind every number of a legacy report, using a table of the open model as the data."""
    content = file.file.read()
    try:
        report = reverse.run_for_live(live.connector, table, content, file.filename or "report", live.max_rows)
    except ReportReadError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    s = report.summary
    logger.info(f"Reverse-engineered '{report.filename}' against '{table}': {s.reproduced}/{s.cells} reproduced in {s.seconds}s")
    return report.to_dict()


@router.post("/reverse-engineer/apply")
def apply_reverse_engineered(
    request: ReverseApplyRequest,
    live: LiveModelService = Depends(get_live_service),
    reverse: ReverseService = Depends(get_reverse_service),
) -> dict[str, Any]:
    """Add proven measures to the open model, if Power BI's engine agrees with each one's checks."""
    try:
        report = reverse.get(request.report_id)
        if not report.live:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "That report was not run against the open model, so it cannot be added to it."
            )
        measures = reverse.measures_to_add(report, request.measure_ids)
    except ReportNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    result = live.apply_migrated(measures, dry_run=request.dry_run)
    written = sum(1 for r in result["results"] if r["status"] == "written")
    logger.info(f"reverse apply dry_run={request.dry_run}: {written} written of {len(measures)} requested")
    return result
