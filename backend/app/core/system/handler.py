"""
Gestionnaire d'exécution des tools internes avec Registry Pattern.

Architecture :
- Registry global avec décorateurs @tool_handler
- Handlers modulaires dans handlers/
- Auto-registration au démarrage
"""

from typing import Dict, Any, Callable
from functools import wraps
from config.logger import logger

# Registry global des handlers
_TOOL_HANDLERS: Dict[str, Callable] = {}


def tool_handler(tool_name: str):
    """
    Décorateur pour enregistrer un handler de tool interne.

    Usage:
        @tool_handler("my_tool")
        async def handle_my_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
            return {"success": True, "result": ..., "error": None}

    Args:
        tool_name: Nom du tool à enregistrer
    """
    def decorator(func: Callable):
        _TOOL_HANDLERS[tool_name] = func
        logger.debug(f"Registered internal tool handler: {tool_name}")

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def execute(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Point d'entrée principal pour l'exécution des tools internes.

    Args:
        tool_name: Nom du tool à exécuter
        arguments: Arguments du tool

    Returns:
        {"success": bool, "result": Any, "error": Optional[str]}
    """
    handler = _TOOL_HANDLERS.get(tool_name)

    if not handler:
        logger.warning(f"Unknown internal tool: {tool_name}")
        return {
            "success": False,
            "result": None,
            "error": f"Unknown internal tool: {tool_name}"
        }

    try:
        logger.debug(f"Executing internal tool: {tool_name}")
        return await handler(arguments)
    except Exception as e:
        logger.error(f"Internal tool execution error for {tool_name}: {e}", exc_info=True)
        return {
            "success": False,
            "result": None,
            "error": str(e)
        }


def get_registered_tools() -> list[str]:
    """Retourne la liste des tools enregistrés (utile pour debug)."""
    return list(_TOOL_HANDLERS.keys())
