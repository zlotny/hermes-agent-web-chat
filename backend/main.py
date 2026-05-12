"""Thin entrypoint — imports the app factory and runs uvicorn."""

import uvicorn

from app import create_app
from app.config import PORT

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
