#!/usr/bin/env python3
"""
Hybrid HTTP server for the Docker container.

Serves the Vue SPA and proxies /api/* requests to the Python backend
running on the host. This way the Hermes agent's terminal tool executes
on the real host filesystem instead of inside the container.

Usage:
    python proxy_server.py

Environment:
    BACKEND_HOST  — host backend address (default: host.docker.internal)
    BACKEND_PORT  — host backend port (default: 11300)
    PORT          — this server's port (default: 11300)
"""

import asyncio
import json
import os
from pathlib import Path
import sys

try:
    import aiohttp
    from aiohttp import web
except ImportError:
    print("aiohttp not installed. Install it with: pip install aiohttp", file=sys.stderr)
    sys.exit(1)

BACKEND_HOST = os.getenv("BACKEND_HOST", "172.17.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "11300"))
SPA_PORT = int(os.getenv("PORT", "11300"))
SPA_DIR = Path(__file__).resolve().parent / "frontend" / "dist"


async def proxy_api(request: web.Request) -> web.StreamResponse:
    """Proxy /api/* requests to the host backend."""
    path = request.match_info.get("path", "")
    qs = request.query_string
    target_url = f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/{path}"
    if qs:
        target_url += f"?{qs}"

    try:
        async with aiohttp.ClientSession() as session:
            body = await request.read()
            headers = {k: v for k, v in request.headers.items()
                       if k.lower() not in {"host", "transfer-encoding"}}

            async with session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=body,
                timeout=aiohttp.ClientTimeout(total=3600),
            ) as resp:
                ct = resp.headers.get("Content-Type", "")
                if "text/event-stream" in ct:
                    response = web.StreamResponse(
                        status=resp.status,
                        headers={
                            "Content-Type": "text/event-stream",
                            "Cache-Control": "no-cache",
                            "X-Accel-Buffering": "no",
                        },
                    )
                    await response.prepare(request)
                    async for chunk in resp.content.iter_chunked(8192):
                        try:
                            await response.write(chunk)
                        except (ConnectionResetError, ConnectionAbortedError):
                            break
                    await response.write_eof()
                    return response

                body_bytes = await resp.read()
                out = {k: v for k, v in resp.headers.items()
                       if k.lower() not in {"transfer-encoding", "content-encoding", "content-length"}}
                return web.Response(status=resp.status, body=body_bytes, headers=out)

    except aiohttp.ClientConnectorError as e:
        return web.json_response({"error": f"Backend unreachable: {e}"}, status=502)
    except asyncio.TimeoutError:
        return web.json_response({"error": "Backend timed out"}, status=504)


async def serve_spa(request: web.Request) -> web.FileResponse:
    """Serve SPA static files with index.html fallback."""
    path = request.match_info.get("path", "")
    file_path = SPA_DIR / path if path else SPA_DIR / "index.html"
    try:
        resolved = file_path.resolve()
        if not resolved.is_relative_to(SPA_DIR.resolve()):
            file_path = SPA_DIR / "index.html"
    except (ValueError, OSError):
        file_path = SPA_DIR / "index.html"
    if file_path.is_file() and file_path != SPA_DIR / "index.html":
        return web.FileResponse(str(file_path))
    return web.FileResponse(
        str(SPA_DIR / "index.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def main():
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_route("*", "/api/{path:.*}", proxy_api)
    app.router.add_get("/{path:.*}", serve_spa)
    web.run_app(app, host="0.0.0.0", port=SPA_PORT)


if __name__ == "__main__":
    main()
