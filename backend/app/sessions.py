"""Session listing and retrieval via Hermes' SQLite SessionDB."""

from fastapi import APIRouter, HTTPException

from app.dependencies import get_db
from app.utils import tag_message_source, ts_to_iso

router = APIRouter()


@router.get("/api/sessions")
async def list_sessions(limit: int = 0, show_crons: bool = False):
    """List sessions via Hermes' SessionDB — same as `hermes sessions browse`."""
    db = get_db()
    effective_limit = limit if limit > 0 else 9999

    # Fetch many more rows before LIMIT so cron filtering doesn't starve results
    fetch_limit = effective_limit * 5 + 100
    rows = db._conn.execute(
        """
        SELECT s.id, s.source, s.model, s.title, s.message_count,
               s.started_at, s.ended_at,
               COALESCE((SELECT MAX(m.timestamp) FROM messages m WHERE m.session_id = s.id), s.started_at) AS last_active,
               COALESCE((SELECT SUBSTR(REPLACE(REPLACE(m.content, X'0A', ' '), X'0D', ' '), 1, 63)
                        FROM messages m
                        WHERE m.session_id = s.id AND m.role = 'user' AND m.content IS NOT NULL
                        ORDER BY m.timestamp, m.id LIMIT 1), '') AS preview
        FROM sessions s
        ORDER BY last_active DESC
        LIMIT ?
    """,
        (fetch_limit,),
    ).fetchall()

    sessions = []
    for row in rows:
        sid = row["id"]
        source = row["source"]
        if not show_crons and (sid.startswith("cron_") or source == "cron"):
            continue
        raw_preview = (row["preview"] or "").strip()
        title = (
            raw_preview[:60] + ("..." if len(raw_preview) > 60 else "")
            if raw_preview
            else (row["title"] or sid)
        )
        sessions.append(
            {
                "id": sid,
                "model": row["model"] or "",
                "title": title,
                "message_count": row["message_count"] or 0,
                "last_updated": ts_to_iso(row["last_active"]),
                "started_at": ts_to_iso(row["started_at"]),
                "is_cron": sid.startswith("cron_") or source == "cron",
            }
        )
    total = len(sessions)
    if limit > 0:
        sessions = sessions[:limit]
    return {"sessions": sessions, "total": total}


@router.get("/api/debug/db")
async def debug_db():
    """Debug endpoint to check SessionDB state."""
    db = get_db()
    cursor = db._conn.execute("SELECT COUNT(*) FROM sessions")
    total = cursor.fetchone()[0]
    cursor = db._conn.execute("SELECT source, COUNT(*) FROM sessions GROUP BY source")
    by_source = {r[0]: r[1] for r in cursor}
    cursor = db._conn.execute("SELECT COUNT(*) FROM messages")
    msgs = cursor.fetchone()[0]
    cursor = db._conn.execute(
        "SELECT id, source, parent_session_id, message_count FROM sessions ORDER BY started_at DESC LIMIT 5"
    )
    recent = [
        {"id": r[0], "source": r[1], "parent": r[2], "msgs": r[3]} for r in cursor
    ]
    return {
        "total_sessions": total,
        "by_source": by_source,
        "total_messages": msgs,
        "recent_sessions": recent,
        "db_path": str(get_db().db_path),
    }


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
