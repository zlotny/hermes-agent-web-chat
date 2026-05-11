import json
import os
import sys
import glob
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# ---------------------------------------------------------------------------
# Hermes paths
# ---------------------------------------------------------------------------
SESSIONS_DIR = Path(os.getenv("HERMES_SESSIONS_DIR", os.path.expanduser("~/.hermes/sessions")))

HERMES_VENV = os.path.expanduser(
    "~/.hermes/hermes-agent/venv/lib/python3.11/site-packages"
)
if os.path.isdir(HERMES_VENV):
    sys.path.insert(0, HERMES_VENV)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "ndrspass")
PASSWORD_HASH = hashlib.sha256(AUTH_PASSWORD.encode()).hexdigest()
_session_tokens: dict[str, datetime] = {}
_TOKEN_EXPIRY = timedelta(hours=24)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Hermes Thin Client")


def _check_session(request: Request) -> Optional[Response]:
    token = request.cookies.get("session")
    if token and token in _session_tokens:
        if _session_tokens[token] > datetime.utcnow():
            return None
        del _session_tokens[token]
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    return HTMLResponse(status_code=302, headers={"Location": "/login"})


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    # Public paths: login API, static assets, SPA shell
    if (path in ("/login", "/api/login", "/api/logout", "/favicon.ico")
        or path.startswith("/assets/")
        or request.method == "OPTIONS"):
        return await call_next(request)
    # Everything under /api/ requires auth
    if path.startswith("/api/"):
        err = _check_session(request)
        if err:
            return err
        return await call_next(request)
    # SPA routes: serve the app (auth handled client-side via /api/* calls)
    return await call_next(request)


@app.post("/api/login")
async def api_login(request: Request):
    body = await request.json()
    pwd = body.get("password", "")
    if hashlib.sha256(pwd.encode()).hexdigest() != PASSWORD_HASH:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = secrets.token_urlsafe(32)
    _session_tokens[token] = datetime.utcnow() + _TOKEN_EXPIRY
    resp = JSONResponse(content={"ok": True})
    resp.set_cookie(
        key="session",
        value=token,
        max_age=int(_TOKEN_EXPIRY.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return resp


@app.get("/api/logout")
async def api_logout(request: Request):
    token = request.cookies.get("session")
    if token and token in _session_tokens:
        del _session_tokens[token]
    resp = JSONResponse(content={"ok": True})
    resp.delete_cookie("session")
    return resp


# ---------------------------------------------------------------------------
# Session API
# ---------------------------------------------------------------------------
def _list_sessions() -> list[dict]:
    sessions = []
    pattern = str(SESSIONS_DIR / "session_*.json")
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            continue
        title = data.get("session_id", "Untitled")
        msgs = data.get("messages", [])
        if msgs:
            first_user = next(
                (m["content"][:80] for m in msgs if m.get("role") == "user" and m.get("content")),
                None,
            )
            if first_user:
                title = first_user + ("..." if len(first_user) == 80 else "")
        sessions.append({
            "id": data.get("session_id", ""),
            "model": data.get("model", ""),
            "title": title,
            "message_count": data.get("message_count", len(msgs)),
            "last_updated": data.get("last_updated", ""),
            "started_at": data.get("session_start", ""),
        })
    sessions.sort(key=lambda s: s["last_updated"], reverse=True)
    return sessions


def _get_session(session_id: str) -> Optional[dict]:
    path = SESSIONS_DIR / f"session_{session_id}.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


@app.get("/api/sessions")
async def list_sessions():
    return _list_sessions()


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    data = _get_session(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": data.get("session_id"),
        "model": data.get("model"),
        "messages": data.get("messages", []),
    }


# ---------------------------------------------------------------------------
# Frontend static files
# ---------------------------------------------------------------------------
DIST_DIR = Path(__file__).parent / "frontend" / "dist"
if DIST_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = DIST_DIR / full_path
        if file_path.is_file() and file_path.resolve().is_relative_to(DIST_DIR.resolve()):
            return FileResponse(str(file_path))
        return FileResponse(str(DIST_DIR / "index.html"))
else:
    @app.get("/")
    async def root():
        return JSONResponse({"status": "ok", "message": "Hermes Thin Client API running. Frontend not built."})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
