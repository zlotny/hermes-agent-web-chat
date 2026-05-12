"""Hermes Agent Web Chat — FastAPI Application Factory."""

import sys
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse

from app.config import HERMES_VENV, HERMES_SRC
from app.auth import router as auth_router, check_session
from app.sessions import router as sessions_router
from app.chat import router as chat_router
from app.providers import router as providers_router
from app.commands import router as commands_router
from app.static import setup_static_serving


# ---------------------------------------------------------------------------
# Ensure Hermes modules are on sys.path (must happen before any hermes import)
# ---------------------------------------------------------------------------
if os.path.isdir(HERMES_VENV):
    sys.path.insert(0, HERMES_VENV)
if os.path.isdir(HERMES_SRC):
    sys.path.insert(0, HERMES_SRC)


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(title="Hermes Agent Web Chat")

    # ------------------------------------------------------------------
    # Auth middleware — guards /api/* and SPA routes
    # ------------------------------------------------------------------
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        path = request.url.path
        # Public paths
        if (
            path in ("/login", "/api/login", "/api/logout", "/favicon.ico")
            or path.startswith("/assets/")
            or request.method == "OPTIONS"
        ):
            return await call_next(request)

        if path.startswith("/api/"):
            if not check_session(request):
                return JSONResponse(status_code=401, content={"error": "unauthorized"})
            return await call_next(request)

        # SPA routes — redirect to /login if not authenticated
        if not check_session(request):
            return HTMLResponse(status_code=302, headers={"Location": "/login"})
        return await call_next(request)

    # ------------------------------------------------------------------
    # Include routers
    # ------------------------------------------------------------------
    app.include_router(auth_router)
    app.include_router(sessions_router)
    app.include_router(chat_router)
    app.include_router(providers_router)
    app.include_router(commands_router)

    # ------------------------------------------------------------------
    # Static file serving (SPA)
    # ------------------------------------------------------------------
    setup_static_serving(app)

    return app
