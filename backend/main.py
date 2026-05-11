import json
import os
import sys
import glob
import hashlib
import secrets
import queue as _queue
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
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
# Editable install: source code at HERMES_SRC or the repo root
HERMES_SRC = os.getenv("HERMES_SRC", os.path.expanduser("~/.hermes/hermes-agent"))
if os.path.isdir(HERMES_SRC):
    sys.path.insert(0, HERMES_SRC)

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
    if (path in ("/login", "/api/login", "/api/logout", "/favicon.ico")
        or path.startswith("/assets/")
        or request.method == "OPTIONS"):
        return await call_next(request)
    if path.startswith("/api/"):
        err = _check_session(request)
        if err:
            return err
        return await call_next(request)
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
    resp.set_cookie(key="session", value=token,
                    max_age=int(_TOKEN_EXPIRY.total_seconds()),
                    httponly=True, samesite="lax", secure=False)
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
def _is_cron_session(data: dict) -> bool:
    """Detect if a session belongs to a cron job."""
    sid = data.get("session_id", "")
    source = data.get("source") or data.get("platform", "")
    if sid.startswith("cron_") or source == "cron":
        return True
    msgs = data.get("messages", [])
    if msgs:
        first_content = msgs[0].get("content", "")
        if "[IMPORTANT: You are running as a scheduled cron job" in first_content:
            return True
    return False


def _list_sessions(show_crons: bool = False) -> list[dict]:
    sessions = []
    pattern = str(SESSIONS_DIR / "session_*.json")
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            continue
        if not show_crons and _is_cron_session(data):
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
            "is_cron": _is_cron_session(data),
        })
    sessions.sort(key=lambda s: s["last_updated"], reverse=True)
    seen_titles: set[str] = set()
    deduped: list[dict] = []
    for s in sessions:
        key = s["title"]
        if key not in seen_titles:
            seen_titles.add(key)
            deduped.append(s)
    return deduped


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
async def list_sessions(limit: int = 0, show_crons: bool = False):
    """List sessions. Pass ?limit=N and/or ?show_crons=true."""
    all_sessions = _list_sessions(show_crons=show_crons)
    total = len(all_sessions)
    if limit > 0:
        return {"sessions": all_sessions[:limit], "total": total}
    return {"sessions": all_sessions, "total": total}


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
# Chat (AIAgent)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None


def _default_model() -> str:
    """Read default model from Hermes config.yaml."""
    import yaml
    config_path = Path(os.getenv("HERMES_HOME", os.path.expanduser("~/.hermes"))) / "config.yaml"
    try:
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        if cfg and "model" in cfg:
            return cfg["model"].get("default", "")
    except Exception:
        pass
    return ""


def _agent_is_available() -> bool:
    """Check if AIAgent can be imported."""
    try:
        from run_agent import AIAgent
        return True
    except ImportError:
        return False


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    if not _agent_is_available():
        return JSONResponse(
            status_code=503,
            content={"error": "Hermes Agent is not available in this environment. "
                     "Mount the Hermes venv and config to enable chat."}
        )

    q: _queue.Queue = _queue.Queue()
    loop = asyncio.get_event_loop()
    result_holder = {}

    def on_delta(delta: str) -> None:
        """Called by AIAgent from a background thread."""
        if delta is not None:
            q.put_nowait(("token", delta))

    async def run_agent():
        try:
            from run_agent import AIAgent

            agent = AIAgent(
                model=req.model or _default_model(),
                session_id=req.session_id,
                stream_delta_callback=on_delta,
                quiet_mode=True,
                verbose_logging=False,
            )
            result = await loop.run_in_executor(
                None, lambda: agent.run_conversation(user_message=req.message)
            )
            result_holder["session_id"] = result.get("session_id") or agent.session_id or ""
        except Exception as e:
            q.put_nowait(("error", str(e)))
        finally:
            q.put_nowait(("done", None))

    async def generate() -> AsyncGenerator[str, None]:
        asyncio.create_task(run_agent())
        while True:
            try:
                kind, payload = await loop.run_in_executor(
                    None, lambda: q.get(timeout=60)
                )
            except (_queue.Empty, asyncio.TimeoutError):
                continue
            if kind == "token":
                yield f"data: {json.dumps({'token': payload})}\n\n"
            elif kind == "error":
                yield f"data: {json.dumps({'error': payload})}\n\n"
                break
            elif kind == "done":
                sid = result_holder.get("session_id", "")
                yield f"data: {json.dumps({'done': True, 'session_id': sid})}\n\n"
                break

    return StreamingResponse(generate(), media_type="text/event-stream")


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
