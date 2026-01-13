"""Utilities pour construire la liste des tools disponibles pour un agent."""

import json
from typing import List, Optional
from app.core.services.llm.types import ToolDefinition
from app.database.crud import agents as agent_crud
from config.logger import logger


async def build_tools_for_agent(
    agent_id: str,
    user_id: str,
    resource_ids: Optional[List[str]] = None
) -> List[ToolDefinition]:
    """
    Construit la liste complète des tools disponibles pour un agent.

    Args:
        agent_id: ID de l'agent
        user_id: ID de l'utilisateur
        resource_ids: Liste optionnelle des IDs de ressources attachées

    Returns:
        Liste de ToolDefinition incluant:
        - Tools MCP des servers associés à l'agent
        - Tools internes (resources) si des resources sont disponibles
        - Tools automation si l'agent est le Builder (__system_builder_automation__)
    """
    tools = []

    try:
        # 1. Charger l'agent
        agent = await agent_crud.get_agent(agent_id)
        if not agent:
            logger.warning(f"Agent not found: {agent_id}")
            return tools

        # 2. Récupérer les tools MCP des servers associés à l'agent
        from app.database import crud
        from app.core.services.llm.types import ToolDefinition

        # Récupérer les configurations MCP de l'agent
        configs = await crud.list_configurations_by_agent(agent_id)

        for config in configs:
            if config.get("entity_type") == "server" and config.get("enabled"):
                server_id = config.get("entity_id")

                # Récupérer les tools du serveur MCP
                mcp_tools = await crud.list_tools_by_server(server_id)

                for tool_row in mcp_tools:
                    if tool_row.get("enabled"):
                        # Get input_schema from DB or use default
                        input_schema = tool_row.get("input_schema")

                        # FIX: Parser JSON string si nécessaire (asyncpg retourne JSONB comme string)
                        if isinstance(input_schema, str):
                            try:
                                input_schema = json.loads(input_schema)
                                logger.debug(f"Parsed JSON string input_schema for tool {tool_row.get('name')}")
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse input_schema for tool {tool_row.get('name')}: {e}")
                                input_schema = None

                        # Vérifier si c'est un dict valide, sinon utiliser le schema par défaut
                        if not input_schema or not isinstance(input_schema, dict):
                            logger.warning(f"Invalid or missing input_schema for tool {tool_row.get('name')}, using default")
                            input_schema = {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }

                        # Convertir en ToolDefinition
                        tool_def = ToolDefinition(
                            name=tool_row.get("name"),
                            description=tool_row.get("description") or "",
                            input_schema=input_schema,
                            server_id=server_id
                        )
                        tools.append(tool_def)

        logger.debug(f"Added {len([t for t in tools if hasattr(t, 'server_id')])} MCP tools for agent {agent_id}")

        # 3. Ajouter les tools DEFAULT (is_default=true) automatiquement
        from app.database.db import get_connection
        conn = await get_connection()
        try:
            default_tools = await conn.fetch(
                """SELECT t.*, s.id as server_id FROM mcp.tools t
                   JOIN mcp.servers s ON s.id = t.server_id
                   WHERE t.is_default = true AND t.enabled = true"""
            )

            for tool_row in default_tools:
                input_schema = tool_row.get("input_schema")

                # Parser JSON string si nécessaire
                if isinstance(input_schema, str):
                    try:
                        input_schema = json.loads(input_schema)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse input_schema for default tool {tool_row.get('name')}: {e}")
                        input_schema = None

                if not input_schema or not isinstance(input_schema, dict):
                    input_schema = {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }

                tool_def = ToolDefinition(
                    name=tool_row.get("name"),
                    description=tool_row.get("description") or "",
                    input_schema=input_schema,
                    server_id=tool_row.get("server_id")
                )
                tools.append(tool_def)

            logger.debug(f"Added {len(default_tools)} default tools")
        finally:
            await conn.close()

        logger.info(f"Built {len(tools)} tools for agent {agent_id}")
        return tools

    except Exception as e:
        logger.error(f"Error building tools for agent {agent_id}: {e}")
        return tools
