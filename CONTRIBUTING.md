# Contributing

Hermes Agent Web Chat is a minimal web UI for [Hermes Agent](https://github.com/NousResearch/hermes-agent). Keep it simple.

## Dev environment

You need a working Hermes Agent installation at `~/.hermes/` and Python 3.11+.

### Two-terminal workflow

```bash
# Terminal 1 — backend (hot-reload on Python changes)
cd backend
HERMES_HOME=$HOME/.hermes \
HERMES_SRC=$HOME/.hermes/hermes-agent \
AUTH_PASSWORD=changeme \
uvicorn main:app --host 0.0.0.0 --port 11300 --reload

# Terminal 2 — frontend (Vite HMR, proxies /api/* to backend)
cd frontend
npm install && npm run dev
```

Open **http://localhost:5173** — Vite proxies `/api/*` requests to `localhost:11300`.

## Code conventions

### Backend (Python / FastAPI)

- **No direct Hermes DB access** — use `SessionDB` public API only (`get_session()`, `get_messages()`, `list_sessions_rich()`, etc.). Never use `db._conn.execute()` or `db._execute_write()`.
- Use the `get_db()` dependency from `app.dependencies` for `SessionDB` access.
- Use `asyncio.get_event_loop().run_in_executor()` for blocking Hermes calls.
- Keep routes thin — model logic in route handlers, pure helpers in `utils.py`.

### Frontend (Vue 3 / Options API)

- Use **Options API** (not Composition API) for consistency with the existing codebase.
- Use **Pinia stores** for shared state — no `provide/inject` or event bus.
- One component per file. Keep templates under ~200 lines.
- CSS: Tailwind utility classes for layout/spacing, CSS custom properties for theme colors.
- No TypeScript — plain JS only.

### Slash commands

- Command discovery happens server-side via `hermes_cli.commands` and `agent.skill_commands`.
- The frontend fetches available commands from `/api/commands` and displays them in the command selector popup.
- To add a new slash command, add it to Hermes Agent itself — no frontend changes needed.

## Before submitting

1. Run `npm run build` in `frontend/` to make sure the SPA builds cleanly.
2. The backend serves the built SPA — test via `http://localhost:11300` (no Vite proxy).
3. If you changed the systemd service or Dockerfile, test the deploy flow:

   ```bash
   sudo systemctl restart hermes-agent-web-chat-backend.service
   docker rm -f hermes-ndrs-es 2>/dev/null; docker build --no-cache-filter=frontend -t hermes-agent-web-chat . && docker run -d --name hermes-ndrs-es ...
   ```

## Philosophy

> **"Just a damn chat."** — No feature creep. No changes to how Hermes works. No multi-user, no OAuth, no file upload, no MCP tool integration. If it changes the Hermes installation or wastes tokens, it doesn't belong here.
