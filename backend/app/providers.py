"""Provider and model discovery — lists available providers and their models."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/providers")
async def list_providers():
    """Discover providers that have credentials and list their available models.

    Uses Hermes' ``list_authenticated_providers()`` which scans env vars,
    auth stores, credential pools, and probes LM Studio's local API.
    """
    try:
        # Import Hermes model switch utilities (already on sys.path)
        from hermes_cli.model_switch import list_authenticated_providers
        from hermes_cli.config import load_config

        cfg = load_config()

        # Determine the current provider from config
        model_section = cfg.get("model", {}) or {}
        current_provider = model_section.get("provider", "")
        current_base_url = model_section.get("base_url", "")
        current_model = model_section.get("default", "")

        # Load custom_providers and user_providers from config
        custom_providers = cfg.get("custom_providers") or None
        user_providers = cfg.get("providers") or None

        providers = list_authenticated_providers(
            current_provider=current_provider,
            current_base_url=current_base_url,
            user_providers=user_providers,
            custom_providers=custom_providers,
            max_models=200,     # Return up to 200 models per provider
            current_model=current_model,
        )

        return {"providers": providers}

    except ImportError as e:
        logger.warning("Hermes provider discovery unavailable: %s", e)
        return JSONResponse(
            status_code=503,
            content={"error": "Provider discovery not available", "providers": []},
        )
    except Exception as e:
        logger.error("Provider discovery failed: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": f"Provider discovery failed: {str(e)}", "providers": []},
        )


@router.post("/api/sessions/{session_id}/model")
async def update_session_model(session_id: str, body: dict):
    """Update the model for a specific session.

    This writes to the ``sessions.model`` column — same as the CLI's
    ``/model`` command. The change is scoped to this session only and
    does NOT affect the global config.
    """
    try:
        model = body.get("model", "").strip()
        if not model:
            return JSONResponse(
                status_code=400,
                content={"error": "model is required"},
            )

        db = get_db()

        # Check session exists
        session = db.get_session(session_id)
        if session is None:
            return JSONResponse(
                status_code=404,
                content={"error": "Session not found"},
            )

        # Update the model via SessionDB's write mechanism
        def _do(conn):
            conn.execute(
                "UPDATE sessions SET model = ? WHERE id = ?",
                (model, session_id),
            )

        db._execute_write(_do)

        # Return updated session
        updated = db.get_session(session_id)
        return {
            "id": updated.get("id"),
            "model": updated.get("model"),
        }

    except Exception as e:
        logger.error("Failed to update session model: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to update model: {str(e)}"},
        )


@router.get("/api/config/model-default")
async def get_model_default():
    """Return the global default model from Hermes config.yaml.

    This is the model set in ``model.default`` — used for new chat sessions.
    """
    try:
        from hermes_cli.config import load_config

        cfg = load_config()
        model_section = cfg.get("model", {}) or {}
        return {"model": model_section.get("default", "")}
    except Exception as e:
        logger.error("Failed to read default model: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to read default model", "model": ""},
        )


@router.get("/api/providers/{provider_id}/models")
async def list_provider_models(provider_id: str, search: str = "", limit: int = 50):
    """List all models for a provider from the full models.dev catalog.

    Supports optional ``search`` substring filtering and ``limit`` pagination.
    Unlike the curated provider list, this queries the complete catalog.
    """
    try:
        from agent.models_dev import list_provider_models as _list_all_models

        all_models = _list_all_models(provider_id)

        # Filter by search substring
        if search:
            q = search.strip().lower()
            all_models = [m for m in all_models if q in m.lower()]

        total = len(all_models)
        if limit > 0:
            all_models = all_models[:limit]

        return {"models": all_models, "total": total}

    except Exception as e:
        logger.error("Failed to list provider models: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to list models: {str(e)}", "models": []},
        )
