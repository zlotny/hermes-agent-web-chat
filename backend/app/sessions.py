"""Session listing and retrieval via Hermes' SQLite SessionDB."""

import asyncio

from fastapi import APIRouter, HTTPException

from app.dependencies import get_db
from app.utils import tag_message_source, ts_to_iso

router = APIRouter()


@router.get("/api/sessions")
async def list_sessions(limit: int = 0, offset: int = 0, show_crons: bool = False):
    """List sessions via Hermes' SessionDB — same as `hermes sessions browse`.

    Always fetches a large batch from the DB to compute the true total,
    then returns the requested slice. Supports offset-based pagination.
    """
    db = get_db()
    loop = asyncio.get_event_loop()

    # Always fetch a generous batch so we can compute the true total
    # after Python-side filtering (cron exclusion, etc.)
    BATCH_SIZE = 9999
    exclude = None if show_crons else ["cron"]
    rows = await loop.run_in_executor(
        None,
        lambda: db.list_sessions_rich(
            exclude_sources=exclude,
            limit=BATCH_SIZE,
            offset=0,
            order_by_last_active=True,
        ),
    )

    sessions = []
    for row in rows:
        sid = row.get("id", "")
        source = row.get("source", "")
        # Safety net: filter cron by ID prefix even with exclude_sources
        if not show_crons and sid.startswith("cron_"):
            continue
        preview = (row.get("preview") or "").strip()
        title = (
            preview[:60] + ("..." if len(preview) > 60 else "")
            if preview
            else (row.get("title") or sid)
        )
        sessions.append(
            {
                "id": sid,
                "model": row.get("model") or "",
                "title": title,
                "message_count": row.get("message_count") or 0,
                "last_updated": ts_to_iso(row.get("last_active")),
                "started_at": ts_to_iso(row.get("started_at")),
                "is_cron": sid.startswith("cron_") or source == "cron",
            }
        )
    total = len(sessions)
    # Apply offset and limit for the response page
    start = offset
    end = offset + limit if limit > 0 else total
    page = sessions[start:end]
    return {"sessions": page, "total": total}


@router.get("/api/debug/db")
async def debug_db():
    """Debug endpoint to check SessionDB state using public API."""
    db = get_db()
    loop = asyncio.get_event_loop()

    def _query_stats():
        # Use list_sessions_rich to get total count, source breakdown, etc.
        all_sessions = db.list_sessions_rich(limit=9999, include_children=True)
        return {
            "total_sessions": len(all_sessions),
            "by_source": {},
            "total_messages": sum(s.get("message_count", 0) for s in all_sessions),
            "recent_sessions": [
                {
                    "id": s["id"],
                    "source": s.get("source", ""),
                    "parent": s.get("parent_session_id"),
                    "msgs": s.get("message_count", 0),
                }
                for s in all_sessions[:5]
            ],
            "db_path": str(db.db_path),
        }

    return await loop.run_in_executor(None, _query_stats)


@router.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a session with messages via Hermes' SessionDB."""
    db = get_db()
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = db.get_messages(session_id)
    messages = [tag_message_source(m) for m in messages]
    return {
        "id": session.get("id"),
        "model": session.get("model"),
        "messages": messages,
    }
