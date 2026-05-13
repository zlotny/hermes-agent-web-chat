# Security

## Authentication model

Hermes Agent Web Chat uses **single-password authentication** with server-side session tokens.

1. The operator sets `AUTH_PASSWORD` (env var or `.env` file).
2. The client sends the password once via POST `/api/login`.
3. The server hashes the password, compares against the stored hash, and returns a cryptographically random session token (`secrets.token_urlsafe(32)`) as an `httponly` cookie.
4. Session tokens expire after 24 hours. Tokens are stored **in memory only** — restarting the backend invalidates all sessions.

## Known tradeoffs

| Concern | Status | Notes |
|---------|--------|-------|
| Multi-user | ❌ Not supported | Shared password, no user isolation |
| Rate limiting | ❌ Not implemented | A single-user tool; add a reverse-proxy rate limit if exposed |
| CSRF | ✅ Mitigated | `samesite="lax"` on session cookie |
| XSS | ✅ Partially mitigated | `httponly` cookie prevents JS access to session token |
| HTTPS | ⚠️ Optional | Set up behind Traefik/Caddy/Nginx with TLS. The session cookie sets `secure=True` automatically when behind HTTPS |
| Brute force | ❌ Not protected | No login throttling. Put behind a VPN or fail2ban if exposed to the internet |
| Session persistence | ❌ Memory-only | Restart = all users logged out. Acceptable for a personal tool |

## Recommendations

- **Always use HTTPS** in production. The container + Traefik setup in the README does this.
- **Change the default password** — the codebase ships with `changeme` as the fallback.
- **Put it behind a VPN or SSO proxy** if you need more than one user or stronger auth.
- **Do NOT expose the backend port (11300) directly to the internet** — the Docker container acts as a proxy, and Traefik terminates TLS.

## Reporting issues

This is a personal project. Report security concerns by opening a GitHub issue. There is no bug bounty program.
