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


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all its messages via Hermes' SessionDB."""
    db = get_db()
    loop = asyncio.get_event_loop()
    try:
        deleted = await loop.run_in_executor(
            None, lambda: db.delete_session(session_id)
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"ok": True, "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from app.config import DEBUG


@router.get("/api/debug/db")
async def debug_db():
    """Debug endpoint to check SessionDB state using public API.

    Only available when DEBUG=1 is set.
    """
    if not DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

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

    # If the session has a stored system prompt, inject it as a synthetic
    # message at the beginning (role=system, source=system) so the frontend
    # can display it when "show system messages" is toggled on.
    system_prompt = session.get("system_prompt", "")
    if system_prompt:
        messages.insert(0, {
            "role": "system",
            "source": "system",
            "content": system_prompt,
        })

    # Build title for sidebar display.
    # db.get_session() doesn't include preview — only list_sessions_rich does.
    # So compute title from the first user message content.
    raw_title = (session.get("title") or "").strip()
    raw_id = session.get("id", "")
    # If title is still the raw Hermes auto-generated ID, derive from messages
    if not raw_title or raw_title == raw_id:
        first_user = next(
            (m["content"][:60] for m in messages
             if m.get("role") == "user" and m.get("content")),
            None
        )
        title = first_user or raw_id
    else:
        title = raw_title[:60] + ("..." if len(raw_title) > 60 else "")
    return {
        "id": session.get("id"),
        "model": session.get("model"),
        "title": title,
        "message_count": session.get("message_count") or len(messages),
        "last_updated": ts_to_iso(session.get("last_active")),
        "messages": messages,
    }
