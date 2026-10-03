from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.common.logger import get_logger
from app.core.config import get_settings
from app.core.frontend import mount_frontend
from app.datasets.service import (
    DatasetNotFoundError,
    DatasetService,
    InvalidDatasetError,
    get_dataset_service,
)
from app.routes.copilot_route import router as copilot_router
from app.routes.data_quality_route import router as data_quality_router
from app.routes.datasets_route import router as datasets_router
from app.routes.export_center_route import router as export_center_router
from app.routes.intelligence_route import router as intelligence_router
from app.powerbi_live.connector import ModelConnectionError
from app.powerbi_live.launch_support import shutdown_gracefully, start_model_watchdog
from app.routes.powerbi_live_route import router as powerbi_live_router
from app.routes.powerbi_route import router as powerbi_router
from app.routes.reverse_route import router as reverse_router

logger = get_logger("PowerPilotAPI")
settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize the dataset registry on boot so the first request is not slower."""
    service = get_dataset_service()
    logger.info(
        f"{settings.app_name} v{settings.app_version} starting | "
        f"data_dir={settings.data_dir} | max_upload={settings.max_upload_mb}MB | "
        f"cache={settings.result_cache_size} entries/{settings.result_cache_ttl_seconds}s | "
        f"registered_datasets={service.count_datasets()}"
    )
    if settings.powerbi_live_enabled:
        # Started from Power BI Desktop's External Tools ribbon: stop when the model it is serving
        # goes away (the report was closed) rather than leave a server behind.
        def stop() -> None:
            logger.info(f"The Power BI model at {settings.pbi_server} is gone; shutting down")
            shutdown_gracefully()

        start_model_watchdog(
            settings.pbi_server,
            interval=settings.pbi_watch_interval_seconds,
            failures=settings.pbi_watch_failures,
            stop=stop,
        )
    yield
    logger.info(f"{settings.app_name} shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Intelligent Power BI Automation Platform",
    debug=settings.debug,
    lifespan=lifespan,
)

# An explicit origin list rather than "*": browsers reject a wildcard origin on
# credentialed requests, so allow_credentials=True requires real origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DatasetNotFoundError)
def handle_dataset_not_found(request: Request, exc: DatasetNotFoundError) -> JSONResponse:
    """An unknown dataset id is a client error, not a server failure."""
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


@app.exception_handler(ModelConnectionError)
def handle_model_connection(request: Request, exc: ModelConnectionError) -> JSONResponse:
    """The open Power BI model could not be reached or queried; the message is safe to show."""
    return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content={"detail": str(exc)})


@app.exception_handler(InvalidDatasetError)
def handle_invalid_dataset(request: Request, exc: InvalidDatasetError) -> JSONResponse:
    """Upload validation failures carry client-safe messages from the service."""
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


app.include_router(datasets_router)
app.include_router(data_quality_router)
app.include_router(intelligence_router)
app.include_router(powerbi_router)
app.include_router(powerbi_live_router)
app.include_router(reverse_router)
app.include_router(copilot_router)
app.include_router(export_center_router)


if not settings.serve_frontend:

    @app.get("/")
    def home():
        return {"message": "Welcome to PowerPilot"}


@app.get("/health")
def health(service: DatasetService = Depends(get_dataset_service)):
    """Liveness probe reporting effective configuration and registry state."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "registered_datasets": service.count_datasets(),
        "analysis_cache": service.cache_stats(),
    }


if settings.serve_frontend:
    # Last, so the catch-all that serves the single-page app cannot shadow any API route.
    mount_frontend(app, Path(settings.serve_frontend))
