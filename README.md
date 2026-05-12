# Hermes Agent Web Chat

A web chat interface for [Hermes Agent](https://github.com/NousResearch/hermes-agent). A **drop-in replacement for the TUI** (`hermes chat`) — same agent, same session database, same tools — but accessible from a web browser.

No terminal quirks. No overengineering. No weird over-scoping. Just a clean chat UI that works on desktop and mobile.

## Motivation

I created this project for myself, really. After trying different frontends I found that they don't solve what was for me the most basic thing: Usability.

- `hermes-webui`: forced workspace prompt wastes tokens, too slow & clunky, runs as a standalone hermes install with different values that I have on telegram or chat.  - hermes dashboard: no auth, just proxies the terminal, unusable theme on mobile, bad contrast...
- Open WebUI: Uses hermes-agent OpenAPI-like api -> can't swap model
- etc...

## How it works

The Python backend uses the **exact same Hermes Agent classes** (`AIAgent`, `SessionDB`) that `hermes chat` uses. When you send a message:

1. The backend creates `AIAgent` with your configured model and session
2. The agent runs on the **host machine** — filesystem access, terminal commands, and tools work exactly as if you ran `hermes chat` in a terminal
3. Streaming responses arrive via Server-Sent Events (SSE) — real-time token streaming
4. Sessions are stored in the **same SQLite database** (`~/.hermes/state.db`) — CLI and web sessions coexist seamlessly. You can start something in the web UI and resume it in the terminal, or vice versa

No Hermes ports exposed. No config changes needed. The only difference is the UI.

## Quick start

### Prerequisites

- A working [Hermes Agent](https://github.com/NousResearch/hermes-agent) installation at `~/.hermes/` with a configured provider (run `hermes setup` first)
- Python 3.11+

### Run locally

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
HERMES_HOME=$HOME/.hermes \
HERMES_SRC=$HOME/.hermes/hermes-agent \
AUTH_PASSWORD=changeme \
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — frontend (dev server)
cd frontend
npm install && npm run dev
```

Open **http://localhost:5173** and log in.

### Deploy with Docker + reverse proxy

The Vue SPA runs in Docker, but the Python backend runs **directly on the host** so the agent's terminal tool sees your real filesystem.

#### 1 — Host backend (systemd)

```bash
sudo cp deploy/hermes-thin-client-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-thin-client-backend.service
```

Backend listens on port **8001** (not exposed to the internet).

#### 2 — Container (SPA + API proxy)

```bash
docker build --no-cache-filter=frontend -t hermes-thin-client .
docker run -d --name hermes-ndrs-es --restart unless-stopped \
  -e BACKEND_HOST=172.17.0.1 \
  -e BACKEND_PORT=8001 \
  -l traefik.enable=true \
  -l traefik.frontend.rule=Host=hermes.yourdomain.com \
  -l traefik.port=8000 \
  -l traefik.protocol=http \
  hermes-thin-client
```

The container serves the SPA and proxies `/api/*` to the host. Traefik terminates TLS.

> `BACKEND_HOST` is typically `172.17.0.1` (Docker gateway). On macOS/Windows use `host.docker.internal`.

### Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `AUTH_PASSWORD` | `changeme` | Login password (required) |
| `HERMES_HOME` | `~/.hermes` | Hermes Agent data directory |
| `HERMES_SRC` | `$HERMES_HOME/hermes-agent` | Hermes Agent source path |
| `PORT` | `8000` | HTTP listen port |

---

## Dev

```bash
# Backend (hot-reload on Python changes)
cd backend
HERMES_HOME=$HOME/.hermes \
HERMES_SRC=$HOME/.hermes/hermes-agent \
AUTH_PASSWORD=changeme \
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (HMR, access via localhost:5173)
cd frontend
npm run dev

# Container rebuild (when frontend changes)
docker build -t hermes-thin-client .
docker run -d --name hermes-ndrs-es --restart unless-stopped \
  -e BACKEND_HOST=172.17.0.1 \
  -e BACKEND_PORT=8001 \
  -l traefik.enable=true \
  -l traefik.frontend.rule=Host=hermes.yourdomain.com \
  -l traefik.port=8000 \
  -l traefik.protocol=http \
  hermes-thin-client
```
