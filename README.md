# hermes-agent-thin-client

Cliente web ligero para Hermes Agent. Sustituye al dashboard oficial con una UI mobile-first, sin Node.js/TUI, sin exponer puertos de Hermes.

## Dev

```bash
cd backend && pip install -r requirements.txt && python main.py
```

## Deploy

```bash
docker run -d --name hermes-thin-ndrs-es --restart unless-stopped \
  --network host \
  -l traefik.enable=true \
  -l traefik.frontend.rule=Host:hermes.ndrs.es \
  -l traefik.port=8000 \
  -l traefik.protocol=http \
  hermes-thin-client
```
