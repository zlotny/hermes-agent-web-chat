"""Chat — AIAgent conversation with SSE streaming."""

import json
import queue as _queue
import asyncio
import io
import contextlib
import logging
import os
import time
import uuid as _uuid
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

# Per-session transient state for reload resilience.
# Keyed by real Hermes session ID. Stores the user message and live
# tool/thinking progress so the frontend can reconstruct the chat view
# after a page reload while the agent is still running.
# This is the ONLY source of truth for in-flight session state — it is
# NOT persisted to the DB or shared with Hermes internals.
_chat_transients: dict[str, dict] = {}
_chat_transients_lock = _threading.Lock()

# =========================================================================
# Clarify support — bridges the blocking clarify_callback (agent thread)
# to the async REST API (frontend). Uses Hermes' clarify_gateway module
# which provides thread-safe Event-based state management.
# =========================================================================


def _make_clarify_callback(
    stream_sid: str,
    q: _queue.Queue,
    result_holder: dict,
) -> callable:
    """Return a ``clarify_callback`` for AIAgent that works over SSE + REST.

    When the model calls the ``clarify`` tool, this callback:

    1. Generates a unique ``clarify_id`` and registers the pending request
       with ``clarify_gateway`` (thread-safe Event-based wait).
    2. Pushes a ``clarify_pending`` event into the SSE queue so the
       frontend can display a question dialog.
    3. **Blocks** the agent thread on ``wait_for_response()`` until the
       user submits an answer via ``POST /api/chat/clarify/resolve``.
    4. Returns the user's response to the agent as JSON.
    """

    def _cb(question: str, choices: list[str] | None = None) -> str:
        cid = _uuid.uuid4().hex[:12]
        try:
            from tools.clarify_gateway import register as _register_clarify
            from tools.clarify_gateway import wait_for_response as _wait_clarify
        except ImportError:
            logger.error("clarify_gateway module not available")
            return json.dumps({"error": "Clarify tool is not available in this environment."})

        # Use the real Hermes session ID if available, fall back to stream_sid
        session_key = result_holder.get("session_id", "") or stream_sid

        _register_clarify(
            clarify_id=cid,
            session_key=session_key,
            question=question,
            choices=choices,
        )
        # Notify frontend via SSE
        q.put_nowait((
            "clarify_pending",
            {
                "clarify_id": cid,
                "question": question,
                "choices": choices,
            },
        ))

        # Block agent thread until user responds (10 min timeout)
        result = _wait_clarify(clarify_id=cid, timeout=600.0)
        if result is None:
            return json.dumps({"error": "Clarify request timed out or was cancelled."})
        return json.dumps({
            "question": question,
            "choices_offered": choices,
            "user_response": result,
        }, ensure_ascii=False)

    return _cb


@router.post("/api/chat/clarify/resolve")
async def resolve_clarify(body: dict):
    """Resolve a pending clarify request with the user's answer.

    The frontend calls this when the user submits a response to a
    clarify question.  It unblocks the blocked agent thread via
    ``clarify_gateway.resolve_gateway_clarify()``.
    """
    clarify_id = (body or {}).get("clarify_id", "")
    answer = (body or {}).get("answer", "")
    if not clarify_id:
        return JSONResponse(status_code=400, content={"error": "clarify_id is required"})
    try:
        from tools.clarify_gateway import resolve_gateway_clarify
    except ImportError:
        return JSONResponse(status_code=500, content={"error": "clarify_gateway not available"})
    ok = resolve_gateway_clarify(clarify_id, answer)
    if not ok:
        return JSONResponse(
            status_code=404,
            content={"error": "Clarify request not found or already expired"},
        )
    return {"ok": True}


@router.get("/api/chat/clarify/pending/{session_id}")
async def get_pending_clarify(session_id: str):
    """Return the oldest pending clarify request for a session, or 404.

    Used by the frontend to check for pending clarify questions after a
    page reload.
    """
    try:
        from tools.clarify_gateway import get_pending_for_session
    except ImportError:
        return JSONResponse(status_code=500, content={"error": "clarify_gateway not available"})
    entry = get_pending_for_session(session_id)
    if entry is None:
        return JSONResponse(status_code=404, content={"error": "No pending clarify"})
    return {
        "clarify_id": entry.clarify_id,
        "question": entry.question,
        "choices": entry.choices,
    }


@router.get("/api/chat/transient/{session_id}")
async def get_chat_transient(session_id: str):
    """Return transient in-flight state for a session, or 404 if none."""
    with _chat_transients_lock:
        state = _chat_transients.get(session_id)
        if state is None:
            return JSONResponse(status_code=404, content={"error": "No transient state"})
        return {
            "session_id": session_id,
            "user_message": state.get("user_message", ""),
            "streaming_msg": state.get("streaming_msg", ""),
            "tool_calls": state.get("tool_calls", []),
            "current_tool_name": state.get("current_tool_name", ""),
            "current_tool_preview": state.get("current_tool_preview", ""),
            "status_detail": state.get("status_detail", ""),
        }

# Per-session stop events — set when stop is requested, checked by SSE generator
_stop_events: dict[str, asyncio.Event] = {}
_stop_events_lock = asyncio.Lock()

# Per-session usage snapshots — captured when an agent finishes so that
# resumed sessions can still report token counts via /usage without
# needing the original AIAgent object (which is cleaned up after streaming).
# Keyed by real Hermes session ID.
_usage_snapshots: dict[str, dict] = {}
_usage_snapshots_lock = _threading.Lock()

# Per-session persistent HermesCLI instances — created on first slash command
# and reused for subsequent ones so commands like /usage see the real agent
# state (token counts, compressor stats, etc.) instead of a fresh one.
# Keyed by real Hermes session ID. Protected by a threading lock since
# CLI operations run in a thread executor.
_session_clis: dict[str, "HermesCLI"] = {}
_session_clis_lock = _threading.Lock()
_session_cli_timestamps: dict[str, float] = {}  # last-used time per CLI
_SESSION_CLI_TTL = 1800  # 30 minutes idle before cleanup


def _get_or_create_cli(session_id: str, model: str) -> "HermesCLI":
    """Return an existing HermesCLI for *session_id* or create a new one."""
    from cli import HermesCLI

    with _session_clis_lock:
        cli = _session_clis.get(session_id)
        if cli is not None:
            _session_cli_timestamps[session_id] = time.time()
            return cli

        cli = HermesCLI(
            model=model,
            compact=True,
            resume=session_id,
            verbose=False,
        )
        # Replace the Rich console with a dummy — we capture output via
        # io.StringIO at dispatch time, not during construction.
        from rich.console import Console
        cli.console = Console(file=io.StringIO(), force_terminal=True, width=120)
        _session_clis[session_id] = cli
        _session_cli_timestamps[session_id] = time.time()

        # Restore usage data from the session DB so commands like /usage
        # work on resumed sessions without needing to send a message first.
        # The DB stores input_tokens, output_tokens, etc. per session.
        try:
            snap = _usage_snapshots.get(session_id)
            if not snap:
                db_session = get_db().get_session(session_id)
                if db_session:
                    inp = db_session.get("input_tokens", 0) or 0
                    out = db_session.get("output_tokens", 0) or 0
                    if inp > 0 or out > 0:
                        snap = {
                            "session_api_calls": 1,
                            "session_input_tokens": inp,
                            "session_output_tokens": out,
                            "session_cache_read_tokens": db_session.get("cache_read_tokens", 0) or 0,
                            "session_cache_write_tokens": db_session.get("cache_write_tokens", 0) or 0,
                            "session_reasoning_tokens": db_session.get("reasoning_tokens", 0) or 0,
                            "model": db_session.get("model", ""),
                        }
                        _usage_snapshots[session_id] = snap
            if snap:
                cli._init_agent()
                if cli.agent:
                    logger.info(
                        "Restored usage to CLI %s: api_calls=%d inp=%d out=%d",
                        session_id, snap.get("session_api_calls", 0),
                        snap.get("session_input_tokens", 0),
                        snap.get("session_output_tokens", 0),
                    )
                    for attr in (
                        "session_api_calls", "session_input_tokens",
                        "session_output_tokens", "session_cache_read_tokens",
                        "session_cache_write_tokens", "session_reasoning_tokens",
                    ):
                        setattr(cli.agent, attr, snap.get(attr, 0))
                    if snap.get("model"):
                        cli.agent.model = snap["model"]
        except Exception as e:
            logger.warning("Failed to restore usage from DB for %s: %s", session_id, e)

        return cli


def _remove_cli(session_id: str) -> None:
    """Remove a CLI from the registry."""
    with _session_clis_lock:
        _session_clis.pop(session_id, None)
        _session_cli_timestamps.pop(session_id, None)


async def _cleanup_stale_clis():
    """Periodically remove CLIs that haven't been touched in _SESSION_CLI_TTL."""
    while True:
        try:
            await asyncio.sleep(600)  # Every 10 minutes
            cutoff = time.time() - _SESSION_CLI_TTL
            with _session_clis_lock:
                stale = [sid for sid, ts in _session_cli_timestamps.items() if ts < cutoff]
                for sid in stale:
                    _session_clis.pop(sid, None)
                    _session_cli_timestamps.pop(sid, None)
                    _usage_snapshots.pop(sid, None)
                    _chat_transients.pop(sid, None)
                if stale:
                    logger.debug("Cleaned up %d stale CLI instances", len(stale))
        except asyncio.CancelledError:
            break
        except Exception:
            pass


# Periodic cleanup task that removes orphaned stop events
# (events older than 10 minutes with no active agent or session).
async def _cleanup_orphaned_stop_events():
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            cutoff = time.time() - 600  # 10 minutes stale
            async with _stop_events_lock:
                stale = [sid for sid in _stop_events
                         if sid not in _active_agents
                         and sid not in _active_sessions]
                for sid in stale:
                    _stop_events.pop(sid, None)
                if stale:
                    logger.debug("Cleaned up %d orphaned stop events", len(stale))
        except asyncio.CancelledError:
            break
        except Exception:
            pass


# Start cleanup on import (the asyncio loop must be running — safe for FastAPI)
_threading.Thread(target=lambda: asyncio.run(_cleanup_orphaned_stop_events()), daemon=True).start()
_threading.Thread(target=lambda: asyncio.run(_cleanup_stale_clis()), daemon=True).start()


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

    Uses a persistent HermesCLI per session (created lazily) so commands
    like /usage see the real agent state instead of a fresh one.
    """
    loop = asyncio.get_event_loop()
    try:
        def _run():
            import io
            import contextlib
            import cli as cli_mod
            from rich.console import Console

            sid = req.session_id
            cli = _get_or_create_cli(sid, req.model or default_model())

            buf = io.StringIO()
            # Swap the CLI's console to our buffer for output capture
            old_console = cli.console
            cli.console = Console(file=buf, force_terminal=True, width=120)

            # Also redirect _cprint (prompt_toolkit output) to plain print()
            old = getattr(cli_mod, "_cprint", None)
            if old is not None:
                cli_mod._cprint = lambda text: print(text)  # goes to buf via redirect

            cmd = message_text
            if not cmd.startswith("/"):
                cmd = f"/{cmd}"

            # Ensure the agent is initialized before dispatching
            try:
                cli._init_agent()
            except Exception:
                pass  # Non-fatal — some commands work fine without an agent

            # If the CLI's agent has no usage data and we have a snapshot
            # (e.g. this is a resumed session after restart), inject it.
            cmd_lower = cmd.lstrip("/").lower()
            if sid and cmd_lower in ("usage", "insights") and cli.agent:
                if not getattr(cli.agent, "session_api_calls", 0):
                    with _usage_snapshots_lock:
                        snap = _usage_snapshots.get(sid)
                    if snap:
                        for attr in (
                            "session_api_calls", "session_input_tokens",
                            "session_output_tokens", "session_cache_read_tokens",
                            "session_cache_write_tokens", "session_reasoning_tokens",
                            "session_prompt_tokens", "session_completion_tokens",
                            "session_total_tokens",
                        ):
                            setattr(cli.agent, attr, snap.get(attr, 0))
                        if snap.get("session_api_calls", 0) > 0 and not cli.agent.session_api_calls:
                            cli.agent.session_api_calls = snap["session_api_calls"]
                        if snap.get("model"):
                            cli.agent.model = snap["model"]
                        compressor = getattr(cli.agent, "context_compressor", None)
                        if compressor:
                            compressor.last_prompt_tokens = snap.get("last_prompt_tokens", 0)
                            compressor.context_length = snap.get("context_length", 0)
                            compressor.compression_count = snap.get("compression_count", 0)

            try:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    cli.process_command(cmd)
            finally:
                # Restore the CLI's console
                cli.console = old_console
                if old is not None:
                    cli_mod._cprint = old

            output = buf.getvalue().rstrip()

            # ── Post-dispatch DB persistence ────────────────────────
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
            "user_message": activity.get("user_message", ""),
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

    # 4) Resolve any pending clarify — unblock the agent thread
    try:
        from tools.clarify_gateway import get_pending_for_session, resolve_gateway_clarify
        entry = get_pending_for_session(session_id)
        if entry is not None:
            resolve_gateway_clarify(entry.clarify_id, "")
    except Exception:
        pass

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
            with _chat_transients_lock:
                _real = result_holder.get("session_id", "")
                if _real and _real in _chat_transients:
                    _chat_transients[_real]["streaming_msg"] += delta

    def on_tool_progress(kind: str, name: str, preview: str, args: dict) -> None:
        q.put_nowait(("tool_start", {"name": name, "preview": preview}))
        with _chat_transients_lock:
            _real = result_holder.get("session_id", "")
            if _real and _real in _chat_transients:
                t = _chat_transients[_real]
                t["current_tool_name"] = name
                t["current_tool_preview"] = preview
                t["status_detail"] = f"running tool: {name}"
                # Append to tool_calls list so we can show the chain
                t["tool_calls"].append({
                    "name": name,
                    "preview": preview,
                    "args": args or {},
                    "status": "running",
                })

    def on_tool_complete(tc_id: str, name: str, args: dict, result: str) -> None:
        preview = (result or "")[:80]
        q.put_nowait(("tool_complete", {"name": name, "preview": preview, "args": args}))
        with _chat_transients_lock:
            _real = result_holder.get("session_id", "")
            if _real and _real in _chat_transients:
                t = _chat_transients[_real]
                t["current_tool_name"] = ""
                t["current_tool_preview"] = ""
                t["status_detail"] = ""
                # Mark the most recent matching tool as complete
                for tc in reversed(t["tool_calls"]):
                    if tc["name"] == name and tc["status"] == "running":
                        tc["status"] = "complete"
                        tc["result_preview"] = preview
                        break

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

            # Set TERMINAL_CWD so context file scanning, file tools, and
            # terminal tools use the correct working directory.  Also
            # chdir() there so build_environment_hints() (which calls
            # os.getcwd()) shows the right path in the system prompt.
            # Configurable via HERMES_TERMINAL_CWD env var; defaults to
            # the user's home directory instead of the backend's
            # systemd WorkingDirectory.
            _default_cwd = os.path.expanduser("~")
            _target_cwd = os.environ.get("HERMES_TERMINAL_CWD", _default_cwd)
            os.environ["TERMINAL_CWD"] = _target_cwd
            try:
                os.chdir(_target_cwd)
            except OSError:
                logger.warning("Could not chdir to %s, using current dir", _target_cwd)

            # Set HERMES_INTERACTIVE so gated tools (cronjob, approval)

            # Resolve enabled toolsets from config (same as CLI does),
            # so the web chat doesn't show tools that are off by default
            # (e.g. mixture_of_agents, feishu_*, spotify, discord, etc.).
            _enabled_toolsets = None
            try:
                from hermes_cli.tools_config import _get_platform_tools
                from hermes_cli.config import load_config
                _cfg = load_config()
                _enabled = _get_platform_tools(_cfg, "cli")
                if _enabled:
                    _enabled_toolsets = sorted(_enabled)
            except Exception:
                pass

            agent = AIAgent(
                model=effective_model,
                session_id=agent_session_id,  # None for new chats → auto-generate Hermes ID
                stream_delta_callback=on_delta,
                tool_progress_callback=on_tool_progress,
                tool_complete_callback=on_tool_complete,
                status_callback=on_status,
                clarify_callback=_make_clarify_callback(stream_sid, q, result_holder),
                enabled_toolsets=_enabled_toolsets,
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
                # Save transient state so the frontend can find the chat on reload
                with _chat_transients_lock:
                    _chat_transients[real_sid] = {
                        "user_message": req.message,
                        "streaming_msg": "",
                        "tool_calls": [],
                        "current_tool_name": "",
                        "current_tool_preview": "",
                        "status_detail": "starting…",
                    }

            # Check if stop was already requested while we were setting up
            async with _stop_events_lock:
                existing_stop = _stop_events.get(stream_sid)
                if existing_stop and existing_stop.is_set():
                    return

            # ── Load conversation history for existing sessions ──────────
            # Without this, every turn starts with an empty message list and
            # the agent has no memory of the prior conversation. The session
            # ID is passed so new messages ARE persisted to the DB — but
            # existing messages were never loaded back as input context.
            conversation_history = None
            if not is_new_chat and agent_session_id:
                try:
                    existing_msgs = get_db().get_messages(agent_session_id)
                    if existing_msgs:
                        conversation_history = existing_msgs
                except Exception:
                    pass  # Non-fatal — agent runs with empty history

            result = await loop.run_in_executor(
                None, lambda: agent.run_conversation(
                    user_message=req.message,
                    conversation_history=conversation_history,
                )
            )
            new_sid = result.get("session_id") or real_sid or ""
            result_holder["session_id"] = new_sid
        except Exception as e:
            q.put_nowait(("error", str(e)))
        finally:
            if agent:
                real_sid = agent.session_id or ""
                # ── Sync the real agent into the persistent CLI ──────────
                # So commands like /usage see real token counts, compressor
                # stats, conversation history, etc. without snapshot hacks.
                if real_sid:
                    try:
                        api_calls = getattr(agent, "session_api_calls", 0) or 0
                        # ── Snapshot usage for backend restarts ──────────
                        compressor = getattr(agent, "context_compressor", None)
                        with _usage_snapshots_lock:
                            _usage_snapshots[real_sid] = {
                                "session_api_calls": api_calls,
                                "session_input_tokens": getattr(agent, "session_input_tokens", 0) or 0,
                                "session_output_tokens": getattr(agent, "session_output_tokens", 0) or 0,
                                "session_cache_read_tokens": getattr(agent, "session_cache_read_tokens", 0) or 0,
                                "session_cache_write_tokens": getattr(agent, "session_cache_write_tokens", 0) or 0,
                                "session_reasoning_tokens": getattr(agent, "session_reasoning_tokens", 0) or 0,
                                "session_prompt_tokens": getattr(agent, "session_prompt_tokens", 0) or 0,
                                "session_completion_tokens": getattr(agent, "session_completion_tokens", 0) or 0,
                                "session_total_tokens": getattr(agent, "session_total_tokens", 0) or 0,
                                "model": getattr(agent, "model", ""),
                                "last_prompt_tokens": getattr(compressor, "last_prompt_tokens", 0) or 0,
                                "context_length": getattr(compressor, "context_length", 0) or 0,
                                "compression_count": getattr(compressor, "compression_count", 0) or 0,
                            }
                        logger.info(
                            "Usage sync: session=%s api_calls=%d model=%s",
                            real_sid, api_calls, getattr(agent, "model", "?")
                        )
                        with _session_clis_lock:
                            cli = _session_clis.get(real_sid)
                            if cli is None:
                                # No CLI exists yet — create one eagerly so
                                # the real agent is available for future
                                # slash commands like /usage.
                                from cli import HermesCLI
                                cli = HermesCLI(
                                    model=getattr(agent, "model", ""),
                                    compact=True,
                                    resume=real_sid,
                                    verbose=False,
                                )
                                from rich.console import Console
                                cli.console = Console(
                                    file=io.StringIO(),
                                    force_terminal=True,
                                    width=120,
                                )
                                _session_clis[real_sid] = cli
                            cli.agent = agent
                            cli.conversation_history = getattr(
                                agent, "conversation_history", []
                            ) or []
                            _session_cli_timestamps[real_sid] = time.time()
                    except Exception:
                        pass
                # Clear transient state — agent is done
                if real_sid:
                    with _chat_transients_lock:
                        _chat_transients.pop(real_sid, None)
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
            # Resolve any leftover pending clarify for this session
            try:
                from tools.clarify_gateway import get_pending_for_session, resolve_gateway_clarify
                entry = get_pending_for_session(real_sid or stream_sid)
                if entry is not None:
                    resolve_gateway_clarify(entry.clarify_id, "")
            except Exception:
                pass
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
                elif kind == "clarify_pending":
                    yield f"data: {json.dumps({'clarify_pending': payload})}\n\n"
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
