"""Chat — AIAgent conversation with SSE streaming."""

import json
import queue as _queue
import asyncio
import io
import contextlib
import logging
import time
from typing import AsyncGenerator, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.dependencies import get_db
from app.utils import default_model, agent_is_available

logger = logging.getLogger(__name__)

router = APIRouter()

# Track active agents keyed by session_id (for interrupt/stop)
# For new chats the frontend sends a temp UUID so keys are always real.
_active_agents: dict[str, "AIAgent"] = {}
_active_agents_lock = asyncio.Lock()

# Track sessions with active streaming (for reload resilience)
_active_sessions: dict[str, float] = {}
_active_sessions_lock = asyncio.Lock()

# Per-session activity metadata for reload resilience.
# Keyed by real Hermes session ID. Stores the current tool/status so the
# frontend can display live activity after a page reload.
# Uses threading.Lock because callbacks run in a thread executor.
import threading as _threading
_agent_activity: dict[str, dict] = {}
_agent_activity_lock = _threading.Lock()

# Per-session stop events — set when stop is requested, checked by SSE generator
_stop_events: dict[str, asyncio.Event] = {}
_stop_events_lock = asyncio.Lock()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None


# ---------------------------------------------------------------------------
# Slash command detection — mirrors cli.py's _looks_like_slash_command()
# ---------------------------------------------------------------------------
def _looks_like_slash_command(text: str) -> bool:
    """Return True if *text* looks like a slash command, not a file path."""
    if not text or not text.startswith("/"):
        return False
    first_word = text.split()[0]
    # After stripping the leading /, a command name has no slashes.
    # A path like /Users/foo/bar.md always does.
    return "/" not in first_word[1:]


# ---------------------------------------------------------------------------
# Generic command dispatch via HermesCLI.process_command()
# ---------------------------------------------------------------------------
async def _run_cli_command(
    message_text: str,
    req: ChatRequest,
    q: _queue.Queue,
    result_holder: dict,
) -> None:
    """Dispatch a slash command through HermesCLI.process_command() generically.

    Exactly like tui_gateway/slash_worker.py — creates a lightweight
    HermesCLI, calls process_command(), captures text output, streams
    it back. Works for ALL commands: built-in, skills, plugins.
    """
    loop = asyncio.get_event_loop()
    try:
        def _run():
            import io
            import contextlib
            import cli as cli_mod
            from cli import HermesCLI
            from rich.console import Console

            sid = req.session_id
            cli = HermesCLI(
                model=req.model or default_model(),
                compact=True,
                resume=sid if sid else None,
                verbose=False,
            )

            buf = io.StringIO()
            # Rich Console captures its file handle at construction time, so
            # contextlib.redirect_stdout won't affect it. Swap the console's
            # underlying file to our buffer so self.console.print() is captured.
            cli.console = Console(file=buf, force_terminal=True, width=120)

            # Also redirect _cprint (prompt_toolkit output) to plain print()
            old = getattr(cli_mod, "_cprint", None)
            if old is not None:
                cli_mod._cprint = lambda text: print(text)  # goes to buf via redirect

            cmd = message_text
            if not cmd.startswith("/"):
                cmd = f"/{cmd}"

            try:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    cli.process_command(cmd)
            finally:
                if old is not None:
                    cli_mod._cprint = old

            output = buf.getvalue().rstrip()

            # ── Post-dispatch DB persistence ────────────────────────
            # /model <name> — persist to session DB so the model badge
            # shows the new model after the stream completes.
            if sid and cmd.startswith("/model ") and " " in cmd:
                model_name = cmd.split(None, 1)[1].strip().split()[0]
                if model_name:
                    try:
                        _db = get_db()
                        _db.set_session_model(sid, model_name)
                    except Exception:
                        pass

            return output

        output = await loop.run_in_executor(None, _run)
        if output:
            q.put_nowait(("token", output))
        result_holder["session_id"] = req.session_id or ""
    except Exception as e:
        logger.warning("Command dispatch failed: %s", e)
        q.put_nowait(("token", f"Command failed: {e}"))
    finally:
        q.put_nowait(("done", None))


@router.get("/api/chat/active")
async def get_active_sessions():
    """Return session IDs that currently have an agent streaming."""
    async with _active_sessions_lock:
        cutoff = time.time() - 300
        stale = [sid for sid, ts in _active_sessions.items() if ts < cutoff]
        for sid in stale:
            del _active_sessions[sid]
        return {"active_sessions": list(_active_sessions.keys())}


@router.get("/api/chat/active/{session_id}/status")
async def get_session_active_status(session_id: str):
    """Return the current agent activity for a session (for reload resilience).

    Returns the latest tool name, preview, and token snippet being streamed.
    """
    with _agent_activity_lock:
        activity = _agent_activity.get(session_id)
        if activity is None:
            # Check if the session is still tracked as active
            async with _active_sessions_lock:
                is_active = session_id in _active_sessions
            if not is_active:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Session not active"},
                )
            activity = {}
        return {
            "session_id": session_id,
            "tool_name": activity.get("tool_name", ""),
            "tool_preview": activity.get("tool_preview", ""),
            "token_snippet": activity.get("token_snippet", ""),
            "status_detail": activity.get("status_detail", ""),
        }


@router.post("/api/chat/stop/{session_id}")
async def stop_chat(session_id: str):
    """Interrupt a running agent for the given session.

    1) Signals the SSE stop event so the stream exits immediately.
    2) Interrupts the agent threads via Hermes' set_interrupt.
    """
    # 1) Signal the SSE stop event FIRST
    async with _stop_events_lock:
        stop_event = _stop_events.get(session_id)
        if stop_event is None:
            stop_event = asyncio.Event()
            _stop_events[session_id] = stop_event
        stop_event.set()

    # 2) Interrupt agent threads — get() without pop() so we can signal it
    #    multiple times without losing the reference.
    async with _active_agents_lock:
        agent = _active_agents.get(session_id)
    if agent is not None:
        # Set the agent's instance-level interrupt flags — this is what
        # run_conversation() checks between iterations to stop the main loop.
        agent._interrupt_requested = True
        agent._interrupt_thread_signal_pending = True
        try:
            from tools.interrupt import set_interrupt

            if agent._execution_thread_id is not None:
                set_interrupt(True, agent._execution_thread_id)
            with agent._tool_worker_threads_lock:
                for tid in list(agent._tool_worker_threads):
                    set_interrupt(True, tid)
        except Exception:
            pass

    # 3) Clear active-session tracking and activity
    async with _active_sessions_lock:
        _active_sessions.pop(session_id, None)
    with _agent_activity_lock:
        _agent_activity.pop(session_id, None)

    return {"ok": True, "session_id": session_id}


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
            # Track latest token snippet for reload resilience
            snippet = delta.strip()[:120]
            if snippet:
                with _agent_activity_lock:
                    _real = result_holder.get("session_id", "")
                    if _real:
                        act = _agent_activity.setdefault(_real, {})
                        act["token_snippet"] = snippet

    def on_tool_progress(kind: str, name: str, preview: str, args: dict) -> None:
        q.put_nowait(("tool_start", {"name": name, "preview": preview}))
        with _agent_activity_lock:
            _real = result_holder.get("session_id", "")
            if _real:
                act = _agent_activity.setdefault(_real, {})
                act["tool_name"] = name
                act["tool_preview"] = preview
                act["status_detail"] = f"running tool: {name}"

    def on_tool_complete(tc_id: str, name: str, args: dict, result: str) -> None:
        preview = (result or "")[:80]
        q.put_nowait(("tool_complete", {"name": name, "preview": preview, "args": args}))
        with _agent_activity_lock:
            _real = result_holder.get("session_id", "")
            if _real:
                act = _agent_activity.setdefault(_real, {})
                act["tool_name"] = ""
                act["tool_preview"] = ""
                act["status_detail"] = ""

    def on_status(kind: str, message: str) -> None:
        if kind == "lifecycle":
            q.put_nowait(("status", {"message": message}))

    # ------------------------------------------------------------------
    # Resolve model: explicit > session-stored > config default
    # ------------------------------------------------------------------
    if not req.model and req.session_id:
        try:
            session = get_db().get_session(req.session_id)
            if session and session.get("model"):
                req.model = session["model"]
        except Exception:
            pass  # Fall through to default_model()

    effective_model = req.model or default_model()

    # Determine if this is a new chat (temp ID) or existing session.
    # For new chats, we do NOT pass session_id to AIAgent — let it
    # auto-generate the Hermes-native ID (YYYYMMDD_HHMMSS_XXXXXX).
    # For existing chats, pass the real session ID through.
    frontend_key = req.session_id or ""
    # Check DB first: if the frontend_key exists in the session DB, use it
    # (handles legacy sessions that may have non-standard IDs).
    is_new_chat = True
    if frontend_key:
        try:
            existing = get_db().get_session(frontend_key)
            if existing is not None:
                is_new_chat = False
        except Exception:
            pass
    if is_new_chat:
        is_new_chat = not frontend_key or frontend_key.startswith("new_") or frontend_key.startswith("tmp_")
    agent_session_id = None if is_new_chat else req.session_id

    # Create stop event for this stream session (keyed by frontend_key)
    stream_sid = frontend_key or ("tmp_" + str(int(time.time() * 1000)))
    async with _stop_events_lock:
        stop_event = _stop_events.get(stream_sid)
        if stop_event is None:
            stop_event = asyncio.Event()
            _stop_events[stream_sid] = stop_event
        else:
            stop_event.clear()

    # ------------------------------------------------------------------
    # Slash command interception — if it looks like a command, resolve it
    # and dispatch through HermesCLI.process_command() generically.
    # Only unrecognized text reaches the LLM.
    # ------------------------------------------------------------------
    message_text = req.message or ""
    if _looks_like_slash_command(message_text):
        cmd_name = message_text.split()[0].lstrip("/").lower()
        # Try resolving via COMMAND_REGISTRY or skill commands
        is_command = False
        try:
            from hermes_cli.commands import resolve_command
            is_command = resolve_command(cmd_name) is not None
        except Exception:
            pass
        if not is_command:
            try:
                from agent.skill_commands import get_skill_commands
                is_command = f"/{cmd_name}" in get_skill_commands()
            except Exception:
                pass

        if is_command:
            asyncio.create_task(_run_cli_command(
                message_text, req, q, result_holder,
            ))
            async def command_generate() -> AsyncGenerator[str, None]:
                try:
                    while True:
                        try:
                            kind, payload = await loop.run_in_executor(
                                None, lambda: q.get(timeout=1.0)
                            )
                        except (_queue.Empty, asyncio.TimeoutError):
                            continue
                        if kind == "token":
                            yield f"data: {json.dumps({'token': payload})}\n\n"
                        elif kind == "done":
                            sid = result_holder.get("session_id", "") or stream_sid
                            yield f"data: {json.dumps({'done': True, 'session_id': sid})}\n\n"
                            break
                        elif kind == "error":
                            yield f"data: {json.dumps({'error': payload})}\n\n"
                            break
                finally:
                    async with _stop_events_lock:
                        _stop_events.pop(stream_sid, None)
            return StreamingResponse(command_generate(), media_type="text/event-stream")

    # ------------------------------------------------------------------
    # Agent runner (runs in thread executor)
    # ------------------------------------------------------------------
    async def run_agent():
        agent = None
        try:
            from run_agent import AIAgent

            agent = AIAgent(
                model=effective_model,
                session_id=agent_session_id,  # None for new chats → auto-generate Hermes ID
                stream_delta_callback=on_delta,
                tool_progress_callback=on_tool_progress,
                tool_complete_callback=on_tool_complete,
                status_callback=on_status,
                quiet_mode=True,
                verbose_logging=False,
                session_db=get_db(),
                platform="web",  # Tag sessions as "web" source
            )

            # Track under BOTH keys: the frontend's temp key AND the
            # real Hermes session ID the agent generated.
            real_sid = agent.session_id or ""
            async with _active_agents_lock:
                if real_sid:
                    _active_agents[real_sid] = agent
                if stream_sid and stream_sid != real_sid:
                    _active_agents[stream_sid] = agent
            async with _active_sessions_lock:
                if real_sid:
                    _active_sessions[real_sid] = time.time()
                if stream_sid and stream_sid != real_sid:
                    _active_sessions[stream_sid] = time.time()

            # Save the real Hermes session ID immediately and register activity tracking.
            result_holder["session_id"] = real_sid
            if real_sid:
                with _agent_activity_lock:
                    _agent_activity[real_sid] = {}

            # Check if stop was already requested while we were setting up
            async with _stop_events_lock:
                existing_stop = _stop_events.get(stream_sid)
                if existing_stop and existing_stop.is_set():
                    return

            result = await loop.run_in_executor(
                None, lambda: agent.run_conversation(user_message=req.message)
            )
            new_sid = result.get("session_id") or real_sid or ""
            result_holder["session_id"] = new_sid
        except Exception as e:
            q.put_nowait(("error", str(e)))
        finally:
            if agent:
                real_sid = agent.session_id or ""
                async with _active_agents_lock:
                    if real_sid:
                        _active_agents.pop(real_sid, None)
                    if stream_sid and stream_sid != real_sid:
                        _active_agents.pop(stream_sid, None)
                async with _active_sessions_lock:
                    if real_sid:
                        _active_sessions.pop(real_sid, None)
                    if stream_sid and stream_sid != real_sid:
                        _active_sessions.pop(stream_sid, None)
                with _agent_activity_lock:
                    if real_sid:
                        _agent_activity.pop(real_sid, None)
            q.put_nowait(("done", None))

    # ------------------------------------------------------------------
    # SSE generator
    # ------------------------------------------------------------------
    async def generate() -> AsyncGenerator[str, None]:
        asyncio.create_task(run_agent())
        _session_id_emitted = False
        try:
            while True:
                # Emit the real Hermes session ID as soon as it becomes
                # available — lets the frontend update the sidebar and
                # map streaming state before the stream completes.
                if not _session_id_emitted:
                    real_sid = result_holder.get("session_id", "")
                    if real_sid and real_sid != stream_sid:
                        _session_id_emitted = True
                        yield f"data: {json.dumps({'session_id': real_sid})}\n\n"

                async with _stop_events_lock:
                    current_stop = _stop_events.get(stream_sid)
                    if current_stop and current_stop.is_set():
                        sid = result_holder.get("session_id", "") or stream_sid
                        yield f"data: {json.dumps({'done': True, 'session_id': sid, 'interrupted': True})}\n\n"
                        return

                try:
                    kind, payload = await loop.run_in_executor(
                        None, lambda: q.get(timeout=1.0)
                    )
                except (_queue.Empty, asyncio.TimeoutError):
                    continue

                if kind == "token":
                    yield f"data: {json.dumps({'token': payload})}\n\n"
                elif kind == "tool_start":
                    yield f"data: {json.dumps({'tool_start': payload['name'], 'tool_preview': payload['preview']})}\n\n"
                elif kind == "tool_complete":
                    yield f"data: {json.dumps({'tool_complete': payload['name'], 'tool_result': payload['preview'], 'tool_args': payload['args']})}\n\n"
                elif kind == "status":
                    yield f"data: {json.dumps({'status': payload['message']})}\n\n"
                elif kind == "error":
                    yield f"data: {json.dumps({'error': payload})}\n\n"
                    break
                elif kind == "done":
                    sid = result_holder.get("session_id", "")
                    yield f"data: {json.dumps({'done': True, 'session_id': sid})}\n\n"
                    break
        finally:
            # Clean up stop event
            async with _stop_events_lock:
                _stop_events.pop(stream_sid, None)
            async with _active_sessions_lock:
                _active_sessions.pop(stream_sid, None)
            with _agent_activity_lock:
                real_sid = result_holder.get("session_id", "")
                if real_sid:
                    _agent_activity.pop(real_sid, None)

    return StreamingResponse(generate(), media_type="text/event-stream")
