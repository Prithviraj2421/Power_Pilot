"""Dataset registry endpoints: upload once, then address the analysis by id.

Everything downstream -- exports, Power BI assets, the copilot -- takes a
``dataset_id`` issued here instead of re-uploading the CSV and re-running the
pipeline.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.common.logger import get_logger
from app.datasets.service import DatasetService, get_dataset_service

router = APIRouter(prefix="/api/v1/datasets", tags=["Dataset Registry"])
logger = get_logger("DatasetsRoute")


# NOTE: static paths must be declared before the parameterized "/{dataset_id}"
# route below, otherwise FastAPI matches "stats" as a dataset id.
@router.get("/stats/cache")
def cache_statistics(service: DatasetService = Depends(get_dataset_service)):
    """Analysis cache diagnostics: size, hit rate, evictions, expirations."""
    return {
        "status": "success",
        "registered_datasets": service.count_datasets(),
        "analysis_cache": service.cache_stats(),
    }


@router.post("", status_code=201)
def register_dataset(
    file: UploadFile = File(...),
    service: DatasetService = Depends(get_dataset_service),
):
    """Upload a CSV, run the 12-stage pipeline once, and register the result.

    Re-uploading byte-identical content returns the existing dataset rather than
    recomputing it.
    """
    payload = file.file.read()
    analysis = service.register(payload, file.filename or "dataset.csv")

    return {
        "status": "success",
        "dataset": analysis.record.to_dict(),
        "result": analysis.result,
    }


@router.get("")
def list_datasets(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: DatasetService = Depends(get_dataset_service),
):
    """Analysis history, newest first."""
    records = service.list_datasets(limit=limit, offset=offset)
    return {
        "status": "success",
        "total": service.count_datasets(),
        "limit": limit,
        "offset": offset,
        "datasets": [record.to_dict() for record in records],
    }


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """Dataset metadata only -- cheap, and never triggers a pipeline run."""
    record = service.get_record(dataset_id)
    return {
        "status": "success",
        "dataset": record.to_dict(),
        "analysis_cached": service.is_cached(dataset_id),
    }


@router.get("/{dataset_id}/result")
def get_dataset_result(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """The full analysis for a dataset.

    Served from cache when warm, recomputed from the stored CSV when not. This is
    what lets a client restore a workspace after a refresh without re-uploading.
    """
    analysis = service.get_analysis(dataset_id)
    return {
        "status": "success",
        "dataset": analysis.record.to_dict(),
        "result": analysis.result,
    }


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    """Permanently remove a dataset's stored CSV, metadata row and cached analysis."""
    service.delete(dataset_id)
    return {"status": "success", "dataset_id": dataset_id, "message": "Dataset deleted."}
