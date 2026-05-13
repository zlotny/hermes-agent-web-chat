"""API endpoints for reading/writing Hermes core memory files.

Files managed:
  - SOUL  -> {HERMES_HOME}/SOUL.md
  - MEMORY -> {HERMES_HOME}/memories/MEMORY.md
  - USER   -> {HERMES_HOME}/memories/USER.md
"""

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import HERMES_HOME

router = APIRouter()

CORE_FILES = {
    "MEMORY": "memories/MEMORY.md",
    "USER": "memories/USER.md",
    "SOUL": "SOUL.md",
}


class FileContent(BaseModel):
    content: str


@router.get("/api/core-files")
async def get_core_files():
    """Read all 3 core memory files and return their contents."""
    result = {}
    for name, rel_path in CORE_FILES.items():
        path = os.path.join(HERMES_HOME, rel_path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                result[name] = f.read()
        except FileNotFoundError:
            result[name] = ""
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error reading {name}: {e}"
            )
    return result


@router.put("/api/core-files/{name}")
async def put_core_file(name: str, body: FileContent):
    """Write content to a single core memory file."""
    if name not in CORE_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown file: {name}. Valid: {', '.join(CORE_FILES)}",
        )

    rel_path = CORE_FILES[name]
    path = os.path.join(HERMES_HOME, rel_path)

    # Ensure parent directory exists (e.g. memories/)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(body.content)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error writing {name}: {e}"
        )

    return {"ok": True, "name": name}
