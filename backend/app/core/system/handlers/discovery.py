"""Handlers pour les tools de découverte MCP."""

from typing import Dict, Any
from app.core.system.handler import tool_handler
from config.logger import logger


@tool_handler("list_user_mcp_servers")
async def handle_list_user_mcp_servers(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Liste tous les serveurs MCP de l'utilisateur."""
    from app.database import crud

    user_id = arguments.get("_user_id")
    if not user_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: _user_id"
        }

    # Récupérer tous les serveurs MCP de l'utilisateur
    servers = await crud.list_servers_by_user(user_id)

    # Formater pour une meilleure lisibilité
    formatted_servers = []
    for server in servers:
        formatted_servers.append({
            "id": server.get("id"),
            "name": server.get("name"),
            "description": server.get("description"),
            "url": server.get("url"),
            "status": server.get("status"),
            "enabled": server.get("enabled")
        })

    return {
        "success": True,
        "result": {
            "servers": formatted_servers,
            "total": len(formatted_servers)
        },
        "error": None
    }


@tool_handler("list_server_tools")
async def handle_list_server_tools(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Liste tous les tools disponibles sur un serveur MCP."""
    from app.database import crud

    server_id = arguments.get("server_id")
    if not server_id:
        return {
            "success": False,
            "result": None,
            "error": "Missing required parameter: server_id"
        }

    # Récupérer tous les tools du serveur
    tools = await crud.list_tools_by_server(server_id)

    # Formater pour une meilleure lisibilité
    formatted_tools = []
    for tool in tools:
        formatted_tools.append({
            "name": tool.get("name"),
            "description": tool.get("description"),
            "input_schema": tool.get("input_schema"),
            "enabled": tool.get("enabled")
        })

    return {
        "success": True,
        "result": {
            "server_id": server_id,
            "tools": formatted_tools,
            "total": len(formatted_tools)
        },
        "error": None
    }
