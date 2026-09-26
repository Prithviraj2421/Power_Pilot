"""Legacy upload + quality-plan endpoint.

Predates the dataset registry and duplicates a slice of it through a separate
``DatasetWorkflow``. Nothing in the frontend calls it. Kept working for now, but
``POST /api/v1/datasets`` supersedes it and this should be removed once no
external caller depends on it.
"""

from dataclasses import asdict
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder

from app.common.logger import get_logger
from app.core.config import Settings, get_settings
from app.models.dataset_context import DatasetContext
from app.workflows import DatasetWorkflow

router = APIRouter(prefix="/upload", tags=["Upload"])
logger = get_logger("UploadRoute")

UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}


# Declared with `def`, not `async def`. The body is entirely blocking -- a disk
# write plus a pandas parse -- and FastAPI runs a sync handler in its worker
# threadpool. As `async def` it ran that blocking work directly on the event loop,
# freezing every other in-flight request for the duration.
@router.post("/")
def upload_file(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if not filename or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV and Excel files are allowed.",
        )

    contents = file.file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )
    if len(contents) > settings.max_upload_bytes:
        # Previously unbounded: the body was written to disk before any size check.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum limit of {settings.max_upload_mb}MB.",
        )

    filepath = UPLOAD_FOLDER / filename
    filepath.write_bytes(contents)

    try:
        if extension == ".csv":
            dataframe = pd.read_csv(filepath)
        else:
            dataframe = pd.read_excel(filepath)
    except Exception as exc:
        logger.error(f"Could not read uploaded file '{filename}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {exc}",
        ) from exc

    context = DatasetContext(filename=filename, dataframe=dataframe)
    context = DatasetWorkflow().process(context)

    return jsonable_encoder(
        {
            "report": context.report,
            "cleaning_plan": asdict(context.cleaning_plan) if context.cleaning_plan else None,
        }
    )
