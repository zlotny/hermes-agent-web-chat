# ---- Build frontend ----
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# ---- Proxy server (serves SPA, forwards /api/* to host) ----
FROM python:3.11-slim
WORKDIR /app

# Install aiohttp for the proxy server
RUN pip install --no-cache-dir aiohttp

# Copy proxy server and built frontend
COPY proxy_server.py .
COPY --from=frontend /build/dist /app/frontend/dist

EXPOSE 11300
CMD ["python3", "proxy_server.py"]
