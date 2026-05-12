# Hermes Thin Client

A lightweight web chat interface for [Hermes Agent](https://github.com/NimbleArchitect/hermes-agent). Mobile-first Vue SPA with a Python/FastAPI backend — no TUI, no Node.js runtime, no exposed Hermes ports.

## Features

- **Chat** with Hermes AI Agent via SSE streaming
- **Session browser** — browse and resume past conversations
- **Tool call visualization** — inline badges with argument previews
- **Password auth** — simple cookie-based auth middleware
- **Docker** — single container, multi-stage build

## Quick start

### Prerequisites

- A working [Hermes Agent](https://github.com/NimbleArchitect/hermes-agent) installation at `~/.hermes/`
- Python 3.11+, Node.js 22+ (dev only)

### Dev

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
HERMES_HOME=$HOME/.hermes AUTH_PASSWORD=changeme uvicorn main:app --reload

# Terminal 2 — frontend
cd frontend
npm install && npm run dev
```

Open **http://localhost:5173** (Vite proxies `/api/*` to `:8000`).

### Docker

```bash
docker build -t hermes-thin-client .
docker run -d --name hermes-thin --restart unless-stopped \
  -v $HOME/.hermes:/root/.hermes \
  -e AUTH_PASSWORD=changeme \
  -e HERMES_HOME=/root/.hermes \
  -p 8000:8000 \
  hermes-thin-client
```

### Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `AUTH_PASSWORD` | `changeme` | Login password |
| `HERMES_HOME` | `~/.hermes` | Hermes Agent data directory |
| `HERMES_SRC` | `$HERMES_HOME/hermes-agent` | Hermes source path (editable install) |
| `PORT` | `8000` | HTTP listen port |

## Project structure

```
├── backend/          FastAPI app (modular package)
├── frontend/         Vue 3 + Vite + Pinia + Tailwind
└── Dockerfile
```

See [AGENTS.md](AGENTS.md) for detailed agent/developer knowledge base.
