"""Chat — AIAgent conversation with SSE streaming."""

import json
import queue as _queue
import asyncio
from typing import AsyncGenerator, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.dependencies import get_db
from app.utils import default_model, agent_is_available

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None


@router.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """Start an AIAgent conversation and stream tokens via SSE."""
    if not agent_is_available():
        return JSONResponse(
            status_code=503,
            content={
                "error": "Hermes Agent is not available in this environment. "
                "Mount the Hermes venv and config to enable chat."
            },
        )

    q: _queue.Queue = _queue.Queue()
    loop = asyncio.get_event_loop()
    result_holder: dict = {}

    # ------------------------------------------------------------------
    # Callbacks (called from the AIAgent background thread)
    # ------------------------------------------------------------------
    def on_delta(delta: str) -> None:
        if delta is not None:
            q.put_nowait(("token", delta))

    def on_tool_progress(kind: str, name: str, preview: str, args: dict) -> None:
        q.put_nowait(("tool_start", {"name": name, "preview": preview}))

    def on_tool_complete(tc_id: str, name: str, args: dict, result: str) -> None:
        preview = (result or "")[:80]
        q.put_nowait(("tool_complete", {"name": name, "preview": preview}))

    def on_status(kind: str, message: str) -> None:
        if kind == "lifecycle":
            q.put_nowait(("status", {"message": message}))

    # ------------------------------------------------------------------
    # Agent runner (runs in thread executor)
    # ------------------------------------------------------------------
    async def run_agent():
        try:
            from run_agent import AIAgent

            agent = AIAgent(
                model=req.model or default_model(),
                session_id=req.session_id,
                stream_delta_callback=on_delta,
                tool_progress_callback=on_tool_progress,
                tool_complete_callback=on_tool_complete,
                status_callback=on_status,
                quiet_mode=True,
                verbose_logging=False,
                session_db=get_db(),
            )
            result = await loop.run_in_executor(
                None, lambda: agent.run_conversation(user_message=req.message)
            )
            result_holder["session_id"] = (
                result.get("session_id") or agent.session_id or ""
            )
        except Exception as e:
            q.put_nowait(("error", str(e)))
        finally:
            q.put_nowait(("done", None))

    # ------------------------------------------------------------------
    # SSE generator
    # ------------------------------------------------------------------
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
            elif kind == "tool_start":
                yield f"data: {json.dumps({'tool_start': payload['name'], 'tool_preview': payload['preview']})}\n\n"
            elif kind == "tool_complete":
                yield f"data: {json.dumps({'tool_complete': payload['name'], 'tool_result': payload['preview']})}\n\n"
            elif kind == "status":
                yield f"data: {json.dumps({'status': payload['message']})}\n\n"
            elif kind == "error":
                yield f"data: {json.dumps({'error': payload})}\n\n"
                break
            elif kind == "done":
                sid = result_holder.get("session_id", "")
                yield f"data: {json.dumps({'done': True, 'session_id': sid})}\n\n"
                break

    return StreamingResponse(generate(), media_type="text/event-stream")
