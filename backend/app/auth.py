"""Authentication — session tokens, login/logout endpoints, session validation."""

import secrets
import hashlib
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.config import PASSWORD_HASH, TOKEN_EXPIRY

router = APIRouter()

# In-memory session token store: token → expiration datetime
_session_tokens: dict[str, datetime] = {}


def check_session(request: Request) -> bool:
    """Return True if the request has a valid session cookie."""
    token = request.cookies.get("session")
    if token and token in _session_tokens:
        if _session_tokens[token] > datetime.utcnow():
            return True
        del _session_tokens[token]
    return False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/api/login")
async def api_login(request: Request):
    body = await request.json()
    pwd = body.get("password", "")
    if hashlib.sha256(pwd.encode()).hexdigest() != PASSWORD_HASH:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = secrets.token_urlsafe(32)
    _session_tokens[token] = datetime.utcnow() + TOKEN_EXPIRY
    resp = JSONResponse(content={"ok": True})
    # Set secure=True when behind HTTPS (Traefik sets this header)
    is_secure = request.headers.get("X-Forwarded-Proto", "http") == "https"
    resp.set_cookie(
        key="session",
        value=token,
        max_age=int(TOKEN_EXPIRY.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=is_secure,
    )
    return resp


@router.get("/api/logout")
async def api_logout(request: Request):
    token = request.cookies.get("session")
    if token and token in _session_tokens:
        del _session_tokens[token]
    resp = JSONResponse(content={"ok": True})
    resp.delete_cookie("session")
    return resp
