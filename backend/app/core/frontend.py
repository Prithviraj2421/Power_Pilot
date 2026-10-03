from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Paths that belong to the API; the single-page-app fallback must never answer for them.
_API_PREFIXES = ("api/", "docs", "redoc", "openapi.json", "health")


def mount_frontend(app: FastAPI, directory: Path) -> None:
    """Serve a built single-page app (``frontend/dist``) from the backend itself.

    Lets the External Tool launcher open the UI from one process on one port, with no dev server.
    Unknown paths return ``index.html`` so client-side routes such as ``/live`` survive a reload.
    Call after every API route is registered.
    """
    root = directory.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise FileNotFoundError(f"No built frontend at {index}. Run `npm run build` in frontend/ first.")

    assets = root / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

    @app.get("/{path:path}", include_in_schema=False)
    def single_page_app(path: str) -> FileResponse:
        if path.startswith(_API_PREFIXES):
            raise HTTPException(status_code=404)
        candidate = (root / path).resolve()
        if path and candidate.is_file() and root in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)
