import os
import sys

# Add hermes-agent to path so we can import AIAgent later
HERMES_VENV = os.path.expanduser("~/.hermes/hermes-agent/venv/lib/python3.11/site-packages")
if os.path.isdir(HERMES_VENV):
    sys.path.insert(0, HERMES_VENV)

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Hermes Thin Client")

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hermes Thin Client</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0d1117; color: #c9d1d9;
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh;
  }
  .card {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 12px; padding: 2rem; text-align: center;
    max-width: 400px;
  }
  h1 { font-size: 1.5rem; margin-bottom: 0.5rem; color: #58a6ff; }
  p { color: #8b949e; font-size: 0.9rem; }
  .status { margin-top: 1rem; font-family: monospace; font-size: 0.85rem; }
  .ok { color: #3fb950; }
  .loading { color: #d29922; }
</style>
</head>
<body>
<div class="card">
  <h1>Hermes Thin Client</h1>
  <p>Cliente ligero para Hermes Agent</p>
  <div class="status" id="status">Conectando…</div>
</div>
<script>
fetch('/api/ping')
  .then(r => r.json())
  .then(d => {
    document.getElementById('status').innerHTML =
      '<span class="ok">' + d.message + '</span>';
  })
  .catch(e => {
    document.getElementById('status').innerHTML =
      '<span class="loading">Error: ' + e.message + '</span>';
  });
</script>
</body>
</html>"""

@app.get("/")
async def root():
    return HTMLResponse(HTML)

@app.get("/api/ping")
async def ping():
    return {"message": "it works!", "status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
