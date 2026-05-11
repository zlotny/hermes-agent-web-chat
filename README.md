# hermes-agent-thin-client

Lightweight web client for Hermes Agent. Replaces the official dashboard with a
mobile-first Vue SPA, no Node.js/TUI overhead, no Hermes ports exposed.

## Structure

```
├── backend/          FastAPI (API)
│   └── main.py
├── frontend/         Vue 3 + Vite (SPA)
│   └── src/
│       ├── views/
│       │   ├── LoginPage.vue
│       │   └── ChatPage.vue
│       └── main.js
├── Dockerfile        Multi-stage build (Node + Python)
└── .plan.md          (gitignored) dev notes
```

## Dev

Terminal 1 — backend:
```bash
cd backend && pip install -r requirements.txt && python main.py
```

Terminal 2 — frontend:
```bash
cd frontend && npm install && npm run dev
```

Vite proxies `/api/*` to `localhost:8000`.

## Deploy

```bash
docker build -t hermes-thin-client .
docker run -d --name hermes-thin-ndrs-es --restart unless-stopped \
  -v /home/ndrs/.hermes/sessions:/data/sessions:ro \
  -e HERMES_SESSIONS_DIR=/data/sessions \
  -e AUTH_PASSWORD=ndrspass \
  -l traefik.enable=true \
  -l traefik.frontend.rule=Host:hermes.ndrs.es \
  -l traefik.port=8000 \
  -l traefik.protocol=http \
  hermes-thin-client
```
