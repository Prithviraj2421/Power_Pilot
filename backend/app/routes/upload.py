from dataclasses import asdict
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder

from app.models.dataset_context import DatasetContext
from app.workflows import DatasetWorkflow

router = APIRouter(prefix="/upload", tags=["Upload"])

UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if not filename or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only CSV and Excel files are allowed."
        )

    filepath = UPLOAD_FOLDER / filename

    with open(filepath, "wb") as buffer:
        buffer.write(await file.read())

    try:
        if extension == ".csv":
            dataframe = pd.read_csv(filepath)
        else:
            dataframe = pd.read_excel(filepath)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read uploaded file: {exc}"
        ) from exc

    context = DatasetContext(
        filename=filename,
        dataframe=dataframe
    )
    context = DatasetWorkflow().process(context)

    return jsonable_encoder({
        "report": context.report,
        "cleaning_plan": asdict(context.cleaning_plan)
        if context.cleaning_plan
        else None
    })
