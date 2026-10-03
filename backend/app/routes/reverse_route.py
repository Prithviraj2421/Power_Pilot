"""Prove-It Migration for uploaded datasets: explain a legacy report's numbers, then export what was proven."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse

from app.common.logger import get_logger
from app.datasets.service import DatasetService, get_dataset_service
from app.reverse.errors import ReportReadError
from app.reverse.service import ReportNotFoundError, ReverseService
from app.services.powerbi_export_service import PowerBIExportService

router = APIRouter(prefix="/api/v1", tags=["Report reverse-engineering"])
logger = get_logger("ReverseRoute")


def get_reverse_service() -> ReverseService:
    return ReverseService()


@router.post("/datasets/{dataset_id}/reverse-engineer")
def reverse_engineer(
    dataset_id: str,
    file: UploadFile = File(..., description="The legacy report: .xlsx, .csv or a PDF with tables"),
    datasets: DatasetService = Depends(get_dataset_service),
    service: ReverseService = Depends(get_reverse_service),
) -> dict[str, Any]:
    """Find the formula behind every number in a legacy report, prove it on the dataset, and flag what cannot be reproduced."""
    content = file.file.read()
    try:
        report = service.run_for_dataset(datasets, dataset_id, content, file.filename or "report")
    except ReportReadError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    s = report.summary
    logger.info(f"Reverse-engineered '{report.filename}' against {dataset_id}: {s.reproduced}/{s.cells} reproduced in {s.seconds}s")
    return report.to_dict()


@router.get("/reverse/{report_id}")
def get_report(report_id: str, service: ReverseService = Depends(get_reverse_service)) -> dict[str, Any]:
    """A finished analysis, by id (kept in memory for a while)."""
    return _found(service, report_id).to_dict()


@router.get("/reverse/{report_id}/dax", response_class=PlainTextResponse)
def export_dax(report_id: str, service: ReverseService = Depends(get_reverse_service)) -> PlainTextResponse:
    """A .dax script of only the measures proven from the report."""
    report = _found(service, report_id)
    script = PowerBIExportService.generate_migrated_dax_script(
        report.plan, report.filename, "the raw rows of the data you provided (not the cleaned copy)"
    )
    return PlainTextResponse(script, media_type="text/plain")


@router.get("/reverse/{report_id}/bim")
def export_bim(
    report_id: str,
    datasets: DatasetService = Depends(get_dataset_service),
    service: ReverseService = Depends(get_reverse_service),
) -> dict[str, Any]:
    """A Tabular Model .bim holding only the measures proven from the report."""
    report = _found(service, report_id)
    if report.dataset_id is None or report.live:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This report was run against the open Power BI model, which already holds the table. Use 'Add proven measures to Power BI' instead.",
        )
    analysis = datasets.get_analysis(report.dataset_id)
    measures = [
        {"name": m.name, "expression": m.dax, "description": m.description, "displayFolder": m.display_folder}
        for m in report.plan.measures
    ]
    notes = [
        {"name": "PowerPilot_MigratedFrom", "value": report.filename},
        {
            "name": "PowerPilot_MigrationBasis",
            "value": "Proven on the raw uploaded rows. This model's Power Query loads the cleaned copy, so a figure can differ if cleaning changed those rows.",
        },
    ]
    return PowerBIExportService.generate_tabular_model_bim(
        dataset_profile=analysis.result.dataset_profile,
        extra_measures=measures,
        extra_annotations=notes,
    )


def _found(service: ReverseService, report_id: str):
    try:
        return service.get(report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
