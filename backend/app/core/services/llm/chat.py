# app/core/services/chat.py
"""Service de chat utilisant le LLM Gateway."""

from typing import AsyncGenerator, Optional, List, Dict
from config.logger import logger
from app.core.services.llm.gateway import llm_gateway
from app.core.services.llm.types import ToolDefinition


class ChatService:
    """Service de chat avec support multi-provider via le Gateway."""

    def __init__(self):
        self.gateway = llm_gateway

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        model: str = "gpt-4o-mini",
        api_key_id: Optional[str] = "admin",
        context: Optional[str] = None,
        **extra_params
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat avec le gateway LLM unifié.

        Args:
            messages: Historique des messages (liste de dicts avec 'role' et 'content')
            system_prompt: Prompt système
            model: Modèle à utiliser
            api_key_id: ID de la clé API (None/"admin" = settings, sinon = DB)
            context: Contexte optionnel à ajouter au dernier message utilisateur
            **extra_params: Paramètres supplémentaires (temperature, max_tokens, etc.)

        Yields:
            str: Chunks de texte
        """
        # Si contexte fourni, l'ajouter au dernier message utilisateur
        if context:
            # Copier les messages pour ne pas modifier l'original
            messages = messages.copy()
            # Trouver le dernier message utilisateur
            for i in range(len(messages) - 1, -1, -1):
                if messages[i].get("role") == "user":
                    messages[i] = {
                        "role": "user",
                        "content": f"Contexte:\n{context}\n\n{messages[i]['content']}"
                    }
                    break

        try:
            # Stream via le gateway avec retry automatique
            async for chunk in self.gateway.stream(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                api_key_id=api_key_id,
                **extra_params
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Chat streaming failed: {e}")
            raise

    async def stream_chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        tools: List[ToolDefinition],
        model: str = "gpt-4o-mini",
        api_key_id: Optional[str] = "admin",
        context: Optional[str] = None,
        **extra_params
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat avec support des tool calls MCP.

        Args:
            messages: Historique des messages (liste de dicts avec 'role' et 'content')
            system_prompt: Prompt système
            tools: Liste des tools disponibles (format ToolDefinition)
            model: Modèle à utiliser
            api_key_id: ID de la clé API
            context: Contexte optionnel à ajouter au dernier message utilisateur
            **extra_params: Paramètres supplémentaires

        Yields:
            str: Chunks de texte
        """
        # Si contexte fourni, l'ajouter au dernier message utilisateur
        if context:
            # Copier les messages pour ne pas modifier l'original
            messages = messages.copy()
            # Trouver le dernier message utilisateur
            for i in range(len(messages) - 1, -1, -1):
                if messages[i].get("role") == "user":
                    messages[i] = {
                        "role": "user",
                        "content": f"Contexte:\n{context}\n\n{messages[i]['content']}"
                    }
                    break

        try:
            # Stream via le gateway avec tools
            async for chunk in self.gateway.stream_with_tools(
                messages=messages,
                model=model,
                tools=tools,
                system_prompt=system_prompt,
                api_key_id=api_key_id,
                **extra_params
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Chat streaming with tools failed: {e}")
            raise


# Instance globale réutilisable
chat_service = ChatService()
