# app/core/services/contextualizer.py
"""Service de construction de contexte pour les chats."""

import json
from typing import Dict, Any, Optional, List
from config.logger import logger
from app.database import crud
from app.database.models import Configuration, Server, Resource, Message
from app.core.services.llm.types import ToolDefinition


class Contextualizer:
    """Construit le contexte complet pour un chat."""

    async def build_context(
        self,
        chat_id: str,
        agent_id: Optional[str] = None,
        team_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Construit le contexte complet pour un chat.

        Args:
            chat_id: ID du chat
            agent_id: ID de l'agent (optionnel)
            team_id: ID de l'équipe (optionnel)

        Returns:
            Dict contenant:
            - messages: historique de la conversation
            - servers: liste des serveurs MCP avec leurs outils
            - resources: liste des ressources disponibles
        """
        logger.debug(f"Building context for chat_id={chat_id}, agent_id={agent_id}, team_id={team_id}")

        context = {
            "messages": [],
            "servers": [],
            "resources": []
        }

        # 1. Récupérer les messages de la conversation
        messages_rows = await crud.get_messages_by_chat(chat_id, limit=50)
        context["messages"] = [
            Message.from_row(m).to_dict() for m in messages_rows
        ]
        logger.debug(f"Retrieved {len(context['messages'])} messages from chat")

        # 2. Si agent_id est fourni, récupérer ses configurations
        if agent_id:
            logger.debug(f"Fetching configurations for agent_id={agent_id}")
            configs = await crud.list_configurations_by_agent(agent_id)

            for config_row in configs:
                if not config_row['enabled']:
                    continue

                config = Configuration.from_row(config_row)

                if config.entity_type == "server":
                    # Récupérer le serveur MCP
                    server_row = await crud.get_server(config.entity_id)
                    if server_row and server_row['enabled']:
                        server = Server.from_row(server_row)

                        # Récupérer les outils du serveur
                        tools_rows = await crud.list_tools_by_server(server.id)
                        tools = [t for t in tools_rows if t['enabled']]

                        context["servers"].append({
                            "server": server.to_dict(),
                            "tools": tools,
                            "config_data": config.config_data
                        })
                    else:
                        logger.warning(f"Server {config.entity_id} not found or disabled")

                elif config.entity_type == "resource":
                    # Récupérer la ressource
                    resource_row = await crud.get_resource(config.entity_id)
                    if resource_row and resource_row['enabled']:
                        resource = Resource.from_row(resource_row)
                        context["resources"].append(resource.to_dict())
                    else:
                        logger.warning(f"Resource {config.entity_id} not found or disabled")

        # 🆕 AUTO-ATTACH RAG SERVER SI L'AGENT A DES RESSOURCES ACTIVES
        # Si l'agent a des ressources ready, ajouter automatiquement le serveur RAG interne
        if agent_id and context["resources"]:
            # Compter les ressources ready
            ready_resources = [r for r in context["resources"] if r.get('status') == 'ready']

            if ready_resources:
                logger.info(f"Agent has {len(ready_resources)} ready resource(s), checking for RAG server auto-attach")

                # Récupérer le serveur RAG interne
                rag_server_row = await crud.get_server('srv_internal_rag')

                if rag_server_row and rag_server_row['enabled']:
                    rag_server = Server.from_row(rag_server_row)

                    # Récupérer les tools RAG
                    rag_tools_rows = await crud.list_tools_by_server(rag_server.id)
                    rag_tools = [t for t in rag_tools_rows if t['enabled']]

                    # Vérifier que le serveur RAG n'est pas déjà dans les servers
                    # (au cas où l'utilisateur l'aurait configuré manuellement)
                    has_rag_server = any(
                        s['server']['id'] == 'srv_internal_rag'
                        for s in context["servers"]
                    )

                    if not has_rag_server and rag_tools:
                        context["servers"].append({
                            "server": rag_server.to_dict(),
                            "tools": rag_tools,
                            "config_data": {}  # Pas de config spécifique
                        })
                        logger.info(f"✅ RAG server auto-attached with {len(rag_tools)} tools: {[t['name'] for t in rag_tools]}")
                    elif has_rag_server:
                        logger.debug("RAG server already manually configured, skipping auto-attach")
                    elif not rag_tools:
                        logger.warning("RAG server found but has no enabled tools")
                else:
                    logger.warning("RAG server (srv_internal_rag) not found or disabled in database")

        logger.info(f"Context: {len(context['messages'])} messages, {len(context['servers'])} servers, {len(context['resources'])} resources")

        return context

    def get_tools_for_llm(self, context_data: Dict[str, Any]) -> List[ToolDefinition]:
        """
        Extrait les tools MCP + internal tools.

        Args:
            context_data: Contexte retourné par build_context()

        Returns:
            List[ToolDefinition]: Tools prêts à être passés au LLM
        """
        tools = []

        # Tools MCP
        for server_data in context_data.get("servers", []):
            server = server_data["server"]
            server_id = server["id"]

            for tool_dict in server_data.get("tools", []):
                # FIX: Parser JSON string si nécessaire (asyncpg retourne JSONB comme string)
                input_schema = tool_dict.get("input_schema", {})
                if isinstance(input_schema, str):
                    try:
                        input_schema = json.loads(input_schema)
                        logger.debug(f"Parsed JSON string input_schema for tool {tool_dict['name']}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse input_schema for tool {tool_dict['name']}: {e}")
                        input_schema = {"type": "object", "properties": {}, "required": []}

                tools.append(ToolDefinition(
                    name=tool_dict["name"],
                    description=tool_dict.get("description", ""),
                    input_schema=input_schema,
                    server_id=server_id
                ))

        # Tools internes (RAG)
        resource_ids = [
            r['id'] for r in context_data.get("resources", [])
            if r.get('status') == 'ready'
        ]

        logger.info(f"Resources in context: {len(context_data.get('resources', []))}")
        logger.info(f"Ready resources: {len(resource_ids)} - IDs: {resource_ids}")

        # Note: Les tools RAG (search_resources, list_resources) sont maintenant
        # définis dans app.core.system.definitions.tools.rag et automatiquement
        # attachés à tous les agents via is_default=True.
        # Ils sont récupérés via les serveurs MCP internes, pas ici directement.

        logger.info(f"Total tools for LLM: {len(tools)} - Names: {[t.name for t in tools]}")
        return tools

    def format_context_for_llm(self, context_data: Dict[str, Any]) -> str:
        """
        Formate le contexte pour le LLM (ressources uniquement).
        Les tools sont maintenant passés nativement via l'API.

        Args:
            context_data: Contexte retourné par build_context()

        Returns:
            Texte formaté contenant les ressources disponibles
        """
        parts = []

        # Ressources disponibles
        if context_data.get("resources"):
            parts.append("=== RESSOURCES DISPONIBLES ===\n")

            for resource in context_data["resources"]:
                parts.append(f"Ressource: {resource['name']}")
                if resource.get('description'):
                    parts.append(f"Description: {resource['description']}")
                if resource.get('status'):
                    parts.append(f"Status: {resource['status']}")
                if resource.get('chunk_count'):
                    parts.append(f"Chunks: {resource['chunk_count']}")
                parts.append("")

        formatted = "\n".join(parts)

        if formatted.strip():
            logger.debug(f"Context formatted for LLM ({len(formatted)} chars)")
            return formatted
        else:
            return ""


# Instance globale
contextualizer = Contextualizer()
