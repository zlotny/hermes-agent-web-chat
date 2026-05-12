"""Commands — lists available slash commands from the Hermes COMMAND_REGISTRY.

This endpoint replicates the terminal CLI's command discovery so the web
frontend can show the same set of slash commands the user would see in the
TUI — built-in commands, skill commands, and plugin commands — all populated
via the same internal Hermes classes and methods.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _collect_commands() -> list[dict]:
    """Collect all available slash commands for the web platform.

    Mirrors the terminal CLI's discovery:
      1. Built-in commands from COMMAND_REGISTRY (filtered by _is_gateway_available)
      2. Skill commands from scan_skill_commands()
      3. Plugin commands from _iter_plugin_command_entries()

    Returns a list of dicts, one per command.
    """
    commands: list[dict] = []
    seen_names: set[str] = set()

    # ── 1. Built-in commands ────────────────────────────────────────────
    try:
        from hermes_cli.commands import COMMAND_REGISTRY, _is_gateway_available

        overrides = None
        try:
            from hermes_cli.commands import _resolve_config_gates
            overrides = _resolve_config_gates()
        except Exception:
            pass

        for cmd in COMMAND_REGISTRY:
            if not _is_gateway_available(cmd, overrides):
                continue
            entry = {
                "name": cmd.name,
                "description": cmd.description,
                "category": cmd.category,
                "aliases": list(cmd.aliases),
                "args_hint": cmd.args_hint,
                "subcommands": list(cmd.subcommands),
                "type": "builtin",
            }
            commands.append(entry)
            seen_names.add(cmd.name)
    except Exception as e:
        logger.warning("Failed to load built-in commands: %s", e)

    # ── 2. Skill commands ───────────────────────────────────────────────
    try:
        from agent.skill_commands import get_skill_commands

        skill_cmds = get_skill_commands()
        for cmd_key, info in skill_cmds.items():
            name = cmd_key.lstrip("/")
            if name in seen_names:
                continue
            commands.append({
                "name": name,
                "description": info.get("description", ""),
                "category": "Skills",
                "aliases": [],
                "args_hint": "",
                "subcommands": [],
                "type": "skill",
            })
            seen_names.add(name)
    except Exception as e:
        logger.warning("Failed to load skill commands: %s", e)

    # ── 3. Plugin commands ──────────────────────────────────────────────
    try:
        from hermes_cli.commands import _iter_plugin_command_entries

        for name, description, args_hint in _iter_plugin_command_entries():
            if name in seen_names:
                continue
            commands.append({
                "name": name,
                "description": description,
                "category": "Plugins",
                "aliases": [],
                "args_hint": args_hint,
                "subcommands": [],
                "type": "plugin",
            })
            seen_names.add(name)
    except Exception as e:
        logger.warning("Failed to load plugin commands: %s", e)

    return commands


@router.get("/api/commands")
async def list_commands():
    """Return all available slash commands for the web UI.

    Returns built-in, skill, and plugin commands — same discovery as the
    terminal CLI, but filtered to web-available commands only.
    """
    try:
        cmds = _collect_commands()
        return {"commands": cmds}
    except Exception as e:
        logger.error("Command discovery failed: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": f"Command discovery failed: {str(e)}", "commands": []},
        )
