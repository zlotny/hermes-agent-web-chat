"""Shared FastAPI dependencies — mainly the SessionDB singleton."""

import sys
import threading
from typing import Optional


_SESSION_DB: Optional["SessionDB"] = None
_SESSION_DB_LOCK = threading.Lock()


def get_db():
    """Lazy-init the Hermes SessionDB singleton (thread-safe).

    Returns the same SQLite-backed SessionDB instance used by the Hermes CLI,
    ensuring sessions are shared between CLI and web.
    """
    global _SESSION_DB
    if _SESSION_DB is None:
        with _SESSION_DB_LOCK:
            if _SESSION_DB is None:  # double-checked locking
                try:
                    from hermes_state import SessionDB

                    _SESSION_DB = SessionDB()
                except Exception as e:
                    print(f"[FATAL] SessionDB init failed: {e}", file=sys.stderr)
                    import traceback

                    traceback.print_exc(file=sys.stderr)
                    raise
    return _SESSION_DB
