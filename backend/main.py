import json
import os
import sys
import glob
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# ---------------------------------------------------------------------------
# Hermes paths
# ---------------------------------------------------------------------------
# Session files location. Override via HERMES_SESSIONS_DIR env var when running
# inside Docker (mount ~/.hermes/sessions to /data/sessions and set the var).
SESSIONS_DIR = Path(os.getenv("HERMES_SESSIONS_DIR", os.path.expanduser("~/.hermes/sessions")))

# Hermes venv (host dev only — Docker uses a different mechanism)
HERMES_VENV = os.path.expanduser(
    "~/.hermes/hermes-agent/venv/lib/python3.11/site-packages"
)
if os.path.isdir(HERMES_VENV):
    sys.path.insert(0, HERMES_VENV)

# ---------------------------------------------------------------------------
# Basic Auth
# ---------------------------------------------------------------------------
AUTH_USER = "ndrs"
AUTH_PASS = "ndrspass"


def _check_auth(request: Request) -> Optional[Response]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return Response(
            status_code=401,
            content="Unauthorized",
            headers={"WWW-Authenticate": 'Basic realm="Hermes Thin Client"'},
            media_type="text/plain",
        )
    try:
        decoded = base64.b64decode(auth.removeprefix("Basic ")).decode()
        user, pwd = decoded.split(":", 1)
    except Exception:
        return Response(status_code=401, content="Unauthorized", media_type="text/plain")
    if user != AUTH_USER or pwd != AUTH_PASS:
        return Response(status_code=401, content="Unauthorized", media_type="text/plain")
    return None


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Hermes Thin Client")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Require basic auth on all routes."""
    # Allow preflight / OPTIONS if needed
    if request.method == "OPTIONS":
        return await call_next(request)
    err = _check_auth(request)
    if err:
        return err
    return await call_next(request)


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
def _list_sessions() -> list[dict]:
    """Read all session_*.json files, return sorted by last_updated desc."""
    sessions = []
    pattern = str(SESSIONS_DIR / "session_*.json")
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            continue
        # Derive a title from the first user message or fallback
        title = data.get("session_id", "Untitled")
        msgs = data.get("messages", [])
        if msgs:
            first_user = next(
                (m["content"][:80] for m in msgs if m.get("role") == "user" and m.get("content")),
                None,
            )
            if first_user:
                title = first_user + ("…" if len(first_user) == 80 else "")

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
    """Load a single session file by ID."""
    path = SESSIONS_DIR / f"session_{session_id}.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Frontend HTML (embedded)
# ---------------------------------------------------------------------------
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Hermes</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --fg: #c9d1d9;
    --fg-muted: #8b949e;
    --accent: #58a6ff;
    --accent-hover: #79c0ff;
    --user-msg: #1f6feb;
    --assistant-msg: #161b22;
    --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    --mono: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
    --radius: 8px;
  }
  html, body { height: 100%; }
  body {
    font-family: var(--font);
    background: var(--bg);
    color: var(--fg);
    display: flex;
    overflow: hidden;
  }

  /* Sidebar */
  .sidebar {
    width: 280px;
    min-width: 280px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .sidebar-header {
    padding: 16px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .sidebar-header h2 {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--fg);
  }
  .btn-new {
    background: var(--accent);
    color: #fff;
    border: none;
    padding: 4px 12px;
    border-radius: var(--radius);
    font-size: 0.8rem;
    cursor: pointer;
    font-weight: 500;
  }
  .btn-new:hover { background: var(--accent-hover); }
  .session-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }
  .session-item {
    padding: 10px 12px;
    border-radius: var(--radius);
    cursor: pointer;
    margin-bottom: 2px;
    transition: background 0.15s;
  }
  .session-item:hover { background: #1c2333; }
  .session-item.active { background: #1c2333; border-left: 3px solid var(--accent); }
  .session-item .s-title {
    font-size: 0.82rem;
    color: var(--fg);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 2px;
  }
  .session-item .s-meta {
    font-size: 0.72rem;
    color: var(--fg-muted);
  }
  .session-item .s-meta span { margin-right: 8px; }

  /* Main chat area */
  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 24px 16px;
    max-width: 800px;
    margin: 0 auto;
    width: 100%;
  }
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
    color: var(--fg-muted);
  }
  .empty-state h1 { font-size: 1.5rem; margin-bottom: 8px; color: var(--fg); }
  .empty-state p { font-size: 0.9rem; max-width: 360px; line-height: 1.5; }

  .msg {
    margin-bottom: 20px;
    display: flex;
    flex-direction: column;
  }
  .msg .role {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--fg-muted);
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .msg .bubble {
    padding: 12px 16px;
    border-radius: var(--radius);
    line-height: 1.6;
    font-size: 0.9rem;
    white-space: pre-wrap;
    word-wrap: break-word;
    max-width: 100%;
  }
  .msg.user .bubble {
    background: var(--user-msg);
    align-self: flex-end;
    border-bottom-right-radius: 2px;
  }
  .msg.assistant .bubble {
    background: var(--assistant-msg);
    border: 1px solid var(--border);
    border-bottom-left-radius: 2px;
  }
  .msg .bubble pre {
    background: #0d1117;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 8px 12px;
    overflow-x: auto;
    font-family: var(--mono);
    font-size: 0.82rem;
    margin: 8px 0;
  }
  .msg .bubble code {
    font-family: var(--mono);
    font-size: 0.82rem;
    background: #0d1117;
    padding: 1px 4px;
    border-radius: 3px;
  }

  /* Input area */
  .input-area {
    border-top: 1px solid var(--border);
    padding: 16px;
    background: var(--surface);
  }
  .input-row {
    max-width: 800px;
    margin: 0 auto;
    display: flex;
    gap: 8px;
  }
  .input-row textarea {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--fg);
    padding: 10px 14px;
    font-family: var(--font);
    font-size: 0.9rem;
    resize: none;
    outline: none;
    min-height: 44px;
    max-height: 200px;
    line-height: 1.4;
  }
  .input-row textarea:focus {
    border-color: var(--accent);
  }
  .input-row button {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: var(--radius);
    padding: 0 20px;
    font-size: 0.9rem;
    cursor: pointer;
    font-weight: 500;
    white-space: nowrap;
  }
  .input-row button:hover { background: var(--accent-hover); }
  .input-row button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* Loading spinner */
  .typing {
    color: var(--fg-muted);
    font-size: 0.85rem;
    padding: 8px 0;
    font-style: italic;
  }

  @media (max-width: 640px) {
    .sidebar { display: none; }
    .messages { padding: 16px 12px; }
    .input-area { padding: 12px; }
  }
</style>
</head>
<body>

<!-- Sidebar -->
<div class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <h2>Sessions</h2>
    <button class="btn-new" onclick="newChat()">+ New</button>
  </div>
  <div class="session-list" id="sessionList"></div>
</div>

<!-- Main -->
<div class="main">
  <div class="messages" id="messages">
    <div class="empty-state" id="emptyState">
      <h1>Hermes</h1>
      <p>Type a message below to start a new conversation.</p>
    </div>
  </div>

  <div class="input-area">
    <div class="input-row">
      <textarea id="chatInput" rows="1" placeholder="Type a message…"
        oninput="this.style.height='auto';this.style.height=Math.min(this.scrollHeight, 200)+'px'"
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage()}"></textarea>
      <button id="sendBtn" onclick="sendMessage()">Send</button>
    </div>
  </div>
</div>

<script>
let currentSessionId = null;
let loadingSessions = false;

// Load session list
async function loadSessions() {
  if (loadingSessions) return;
  loadingSessions = true;
  try {
    const res = await fetch('/api/sessions');
    const sessions = await res.json();
    const list = document.getElementById('sessionList');
    list.innerHTML = sessions.map(s => {
      const lastUp = s.last_updated ? new Date(s.last_updated + 'Z').toLocaleString() : '';
      return '<div class="session-item' + (s.id === currentSessionId ? ' active' : '') + '" onclick="loadSession(\'' + s.id + '\')">' +
        '<div class="s-title">' + escapeHtml(s.title) + '</div>' +
        '<div class="s-meta"><span>' + s.message_count + ' msgs</span><span>' + (s.model || '') + '</span><span>' + lastUp + '</span></div>' +
        '</div>';
    }).join('');
  } catch (e) {
    console.error('Failed to load sessions', e);
  } finally {
    loadingSessions = false;
  }
}

// Load a session's messages
async function loadSession(id) {
  currentSessionId = id;
  document.getElementById('emptyState').style.display = 'none';
  const msgsDiv = document.getElementById('messages');
  msgsDiv.innerHTML = '<div class="typing">Loading…</div>';

  try {
    const res = await fetch('/api/sessions/' + encodeURIComponent(id));
    const data = await res.json();
    renderMessages(data.messages || []);
    document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
    const item = document.querySelector('.session-item[data-session-id="' + id + '"]');
    if (item) item.classList.add('active');
  } catch (e) {
    msgsDiv.innerHTML = '<div class="typing">Failed to load session</div>';
  }
  loadSessions(); // refresh sidebar
}

// Render message bubbles
function renderMessages(messages) {
  const div = document.getElementById('messages');
  if (!messages || messages.length === 0) {
    document.getElementById('emptyState').style.display = 'flex';
    return;
  }
  document.getElementById('emptyState').style.display = 'none';
  div.innerHTML = messages.map(m => {
    const role = m.role === 'user' ? 'user' : 'assistant';
    const content = m.content || '';
    return '<div class="msg ' + role + '">' +
      '<div class="role">' + (role === 'user' ? 'You' : 'Hermes') + '</div>' +
      '<div class="bubble">' + renderContent(content) + '</div>' +
      '</div>';
  }).join('');
  div.scrollTop = div.scrollHeight;
}

// Basic markdown-like rendering (code blocks, bold, etc)
function renderContent(text) {
  if (!text) return '';
  // Code blocks first
  let html = text.replace(/```(\w*)\\n([\\s\\S]*?)```/g, '<pre><code>$2</code></pre>');
  // Inline code
  html = html.replace(/\`([^`]+)\`/g, '<code>$1</code>');
  // Double line breaks -> paragraphs
  html = html.replace(/\\n\\n/g, '</p><p>');
  // Single line breaks within paragraphs
  html = html.replace(/\\n/g, '<br>');
  return '<p>' + html + '</p>';
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

// New chat
function newChat() {
  currentSessionId = null;
  document.getElementById('messages').innerHTML = '';
  document.getElementById('emptyState').style.display = 'flex';
  document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
  document.getElementById('chatInput').value = '';
  document.getElementById('chatInput').focus();
}

// Send message (stub for now - will connect to AIAgent later)
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  input.style.height = 'auto';

  // Add user message to UI
  const msgsDiv = document.getElementById('messages');
  document.getElementById('emptyState').style.display = 'none';
  msgsDiv.insertAdjacentHTML('beforeend',
    '<div class="msg user"><div class="role">You</div><div class="bubble">' + escapeHtml(text) + '</div></div>');
  msgsDiv.insertAdjacentHTML('beforeend', '<div class="typing" id="typingIndicator">Thinking…</div>');
  msgsDiv.scrollTop = msgsDiv.scrollHeight;
  document.getElementById('sendBtn').disabled = true;

  // TODO: connect to AIAgent streaming API
  // For now, just a placeholder response
  setTimeout(() => {
    document.getElementById('typingIndicator')?.remove();
    msgsDiv.insertAdjacentHTML('beforeend',
      '<div class="msg assistant"><div class="role">Hermes</div><div class="bubble"><p>Chat not yet connected to Hermes Agent.</p></div></div>');
    msgsDiv.scrollTop = msgsDiv.scrollHeight;
    document.getElementById('sendBtn').disabled = false;
  }, 500);

  loadSessions();
}

// Load sessions on page load
loadSessions();
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return HTMLResponse(HTML)


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


@app.post("/api/chat")
async def chat_stub():
    """Placeholder — will connect to AIAgent later."""
    return JSONResponse(content={"message": "Chat endpoint not implemented yet"})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
