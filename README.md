# hermes-agent-thin-client

Lightweight web client for Hermes Agent. Replaces the official dashboard with a
mobile-first UI, no Node.js/TUI overhead, no Hermes ports exposed.

## Dev

```bash
cd backend && pip install -r requirements.txt && python main.py
```

## Deploy

```bash
docker run -d --name hermes-thin-ndrs-es --restart unless-stopped \
  -l traefik.enable=true \
  -l traefik.frontend.rule=Host:hermes.ndrs.es \
  -l traefik.port=8000 \
  -l traefik.protocol=http \
  hermes-thin-client
```
