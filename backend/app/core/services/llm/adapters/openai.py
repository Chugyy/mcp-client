# app/core/llm/adapters/openai.py
"""Adapter pour OpenAI API."""

import asyncio
import json
from typing import AsyncGenerator, Dict, Any, List, Union, Optional
import httpx
from openai import AsyncOpenAI
from config.logger import logger
from .base import BaseAdapter
from ..registry import PROVIDERS
from ..types import ToolDefinition, ToolCall


def generate_display_name(model_id: str) -> str:
    """
    Génère un display name lisible pour un modèle OpenAI.

    Exemples:
        gpt-4o → GPT-4O
        gpt-4o-mini → GPT-4O Mini
        gpt-3.5-turbo → GPT-3.5 Turbo
        gpt-4-turbo-preview → GPT-4 Turbo Preview

    Args:
        model_id: ID du modèle OpenAI

    Returns:
        Display name formaté
    """
    # Garder les fine-tuned models inchangés (trop complexes)
    if model_id.startswith('ft:'):
        return model_id

    # Remplacer les tirets par des espaces et capitaliser
    parts = model_id.split('-')
    formatted_parts = []

    for part in parts:
        # GPT et ChatGPT en majuscules spéciales
        if part == 'gpt':
            formatted_parts.append('GPT')
        elif part == 'chatgpt':
            formatted_parts.append('ChatGPT')
        # Traiter les parties contenant des chiffres + lettres (ex: "4o" → "4O")
        elif any(c.isdigit() for c in part) and any(c.isalpha() for c in part):
            # Si c'est un pattern type "4o", garder le chiffre et mettre la lettre en majuscule
            formatted_parts.append(part.upper())
        # Garder les versions numériques pures (3.5, 4, etc.)
        elif part.replace('.', '').isdigit():
            formatted_parts.append(part)
        # Capitaliser le reste
        else:
            formatted_parts.append(part.capitalize())

    return ' '.join(formatted_parts)


class OpenAIAdapter(BaseAdapter):
    """Adapter pour l'API OpenAI."""

    def __init__(self, api_key: str, http_client: Optional[httpx.AsyncClient] = None):
        super().__init__(api_key)
        self.client = AsyncOpenAI(
            api_key=api_key,
            http_client=http_client  # Use pooled client if provided
        )

    async def stream(
        self,
        messages: List[Dict[str, str]],
        **params
    ) -> AsyncGenerator[str, None]:
        """Stream la réponse OpenAI."""
        try:
            stream = await self.client.chat.completions.create(
                messages=messages,
                stream=True,
                **params
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Liste tous les modèles disponibles via l'API OpenAI.

        Returns:
            List[Dict]: Liste des modèles avec leurs métadonnées
        """
        try:
            models_response = await self.client.models.list()

            models = []
            provider_name = PROVIDERS["openai"]["name"]  # "OpenAI" from registry
            async for model in models_response:
                models.append({
                    "id": model.id,
                    "object": model.object,
                    "created": model.created,
                    "owned_by": model.owned_by,
                    "provider": provider_name,
                    "display_name": generate_display_name(model.id)
                })

            # Filtrer pour ne garder que les modèles de chat pertinents
            chat_models = [
                m for m in models
                if any(prefix in m["id"] for prefix in ["gpt-4", "gpt-3.5"])
            ]

            return chat_models

        except Exception as e:
            logger.error(f"Error listing OpenAI models: {e}")
            raise

    def is_retriable_error(self, exception: Exception) -> bool:
        """Détermine si l'erreur OpenAI est retriable."""
        status_code = getattr(exception, 'status_code', None)

        # Rate limits, server errors, timeouts
        if status_code in [429, 500, 502, 503, 504]:
            return True

        # Rate limit dans le message d'erreur
        if 'rate_limit' in str(exception).lower():
            return True

        return False

    async def stream_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[ToolDefinition],
        **params
    ) -> AsyncGenerator[Union[str, ToolCall], None]:
        """Stream OpenAI avec détection de tool_calls."""

        # Convertir ToolDefinition → format OpenAI
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema
                }
            }
            for tool in tools
        ]

        # État pour accumuler les tool calls
        tool_calls_buffer = {}  # {index: {id, name, arguments}}

        try:
            stream = await self.client.chat.completions.create(
                messages=messages,
                tools=openai_tools,
                stream=True,
                **params
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta

                # Texte normal
                if delta.content:
                    yield delta.content

                # Tool calls
                if delta.tool_calls:
                    for tool_call_delta in delta.tool_calls:
                        idx = tool_call_delta.index

                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {
                                "id": "",
                                "name": "",
                                "arguments": ""
                            }

                        # Accumuler les morceaux
                        if tool_call_delta.id:
                            tool_calls_buffer[idx]["id"] = tool_call_delta.id
                        if tool_call_delta.function.name:
                            tool_calls_buffer[idx]["name"] = tool_call_delta.function.name
                        if tool_call_delta.function.arguments:
                            tool_calls_buffer[idx]["arguments"] += tool_call_delta.function.arguments

                # Fin du message (finish_reason = "tool_calls")
                if chunk.choices[0].finish_reason == "tool_calls":
                    # Yield tous les tool calls accumulés
                    for tool_data in tool_calls_buffer.values():
                        yield ToolCall(
                            id=tool_data["id"],
                            name=tool_data["name"],
                            arguments=json.loads(tool_data["arguments"])
                        )

                    tool_calls_buffer.clear()

        except Exception as e:
            logger.error(f"OpenAI streaming with tools error: {e}")
            raise

    def transform_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None
    ) -> List[Dict[str, str]]:
        """
        Transforme les messages pour OpenAI.
        OpenAI attend un message system séparé.
        """
        if system_prompt:
            return [{"role": "system", "content": system_prompt}] + messages
        return messages
