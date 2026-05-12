"""Static file serving with SPA fallback — for production when Vite is not running."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


def setup_static_serving(app: FastAPI) -> None:
    """Mount the built frontend dist directory and add an SPA catch-all route.

    If the dist directory doesn't exist (e.g. in dev), just add a simple
    health-check root.
    """
    dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"

    if not dist_dir.is_dir():
        @app.get("/")
        async def root():
            return JSONResponse(
                {
                    "status": "ok",
                    "message": "Hermes Agent Web Chat API running. Frontend not built.",
                }
            )
        return

    app.mount(
        "/assets",
        StaticFiles(directory=str(dist_dir / "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = dist_dir / full_path
        if file_path.is_file() and file_path.resolve().is_relative_to(
            dist_dir.resolve()
        ):
            return FileResponse(str(file_path))
        # index.html: never cache so the browser always picks up new JS builds
        return FileResponse(
            str(dist_dir / "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
