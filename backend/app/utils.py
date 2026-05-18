"""Pure helper functions — no FastAPI dependencies."""

import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

_SYSTEM_CONTENT_PREFIXES = (
    "[IMPORTANT:",
    "Review the conversation above",
    "Review the conversation",
    "System:",
    "You are a helpful assistant",
    "You are Hermes",
    "Hermes Agent",
    "You are an expert",
    "Today is",
    "Current date",
)
_SYSTEM_CONTENT_EXACT = frozenset({"[SILENT]"})


def is_system_content(content: str) -> bool:
    """Detect system-injected messages by content patterns."""
    if not content:
        return False
    stripped = content.strip()
    if stripped in _SYSTEM_CONTENT_EXACT:
        return True
    for prefix in _SYSTEM_CONTENT_PREFIXES:
        if stripped.startswith(prefix):
            return True
    return False


def tag_message_source(msg: dict) -> dict:
    """Add a 'source' field to a message dict."""
    msg = dict(msg)
    if "source" in msg:
        return msg
    role = msg.get("role", "")
    if role == "system":
        msg["source"] = "system"
    elif role == "user":
        msg["source"] = "system" if is_system_content(msg.get("content", "")) else "user"
    elif role == "assistant":
        msg["source"] = "assistant"
    elif role == "tool":
        msg["source"] = "tool"
    else:
        msg["source"] = "unknown"
    return msg


def ts_to_iso(ts: Optional[float]) -> str:
    """Convert a unix timestamp to ISO 8601 string."""
    if ts is None:
        return ""
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def default_model() -> str:
    """Read the default model from Hermes config.yaml."""
    import yaml
    from app.config import HERMES_HOME

    config_path = Path(HERMES_HOME) / "config.yaml"
    try:
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        if cfg and "model" in cfg:
            return cfg["model"].get("default", "")
    except Exception:
        pass
    return ""


def agent_is_available() -> bool:
    """Check if AIAgent can be imported."""
    try:
        from run_agent import AIAgent  # noqa: F401
        return True
    except ImportError:
        return False
