"""Application configuration from environment variables."""

import os
import hashlib
from pathlib import Path
from datetime import timedelta

# ---------------------------------------------------------------------------
# Hermes paths
# ---------------------------------------------------------------------------
HERMES_HOME = os.path.expanduser(
    os.getenv("HERMES_HOME", "~/.hermes")
)
HERMES_VENV = os.path.expanduser(
    os.getenv(
        "HERMES_VENV",
        os.path.join(HERMES_HOME, "hermes-agent/venv/lib/python3.11/site-packages"),
    )
)
HERMES_SRC = os.path.expanduser(
    os.getenv("HERMES_SRC", os.path.join(HERMES_HOME, "hermes-agent"))
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "lWDe0pYPJAvzGrGi")
PASSWORD_HASH = hashlib.sha256(AUTH_PASSWORD.encode()).hexdigest()
TOKEN_EXPIRY = timedelta(hours=24)

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
PORT = int(os.getenv("PORT", "11300"))
