# app/core/llm/adapters/anthropic.py
"""Adapter pour Anthropic Claude API."""

import asyncio
import json
from typing import AsyncGenerator, Dict, Any, List, Union, Optional
import httpx
from anthropic import AsyncAnthropic
from config.logger import logger
from .base import BaseAdapter
from ..registry import PROVIDERS
from ..types import ToolDefinition, ToolCall


class AnthropicAdapter(BaseAdapter):
    """Adapter pour l'API Anthropic Claude."""

    def __init__(self, api_key: str, http_client: Optional[httpx.AsyncClient] = None):
        super().__init__(api_key)
        self.client = AsyncAnthropic(
            api_key=api_key,
            http_client=http_client  # Use pooled client if provided
        )

    async def stream(
        self,
        messages: List[Dict[str, str]],
        **params
    ) -> AsyncGenerator[str, None]:
        """Stream la réponse Claude avec retry automatique."""

        # Configuration du retry
        max_retries = 3
        base_delay = 2  # secondes

        # Extraire system_prompt si présent dans params
        system_prompt = params.pop("system", None)

        # Défense en profondeur : garantir max_tokens
        if "max_tokens" not in params:
            params["max_tokens"] = PROVIDERS["anthropic"]["max_tokens"]["default"]

        # Log pour debug
        if system_prompt:
            logger.info(f"🎯 Anthropic API call with system: {system_prompt[:80]}")
        else:
            logger.warning("⚠️ Anthropic API call WITHOUT system prompt!")

        logger.debug(f"Model: {params.get('model')}, Messages count: {len(messages)}")

        # FIX: Ne passer 'system' que s'il existe (SDK 0.75+ refuse None)
        stream_params = {
            "messages": messages,
            **params
        }
        if system_prompt:
            stream_params["system"] = system_prompt

        # Boucle de retry avec backoff exponentiel
        for attempt in range(max_retries):
            try:
                async with self.client.messages.stream(**stream_params) as stream:
                    async for text in stream.text_stream:
                        yield text

                # Si on arrive ici, succès ! Sortir de la boucle de retry
                break

            except Exception as e:
                # Vérifier si l'erreur est retriable
                is_retriable = self.is_retriable_error(e)
                is_last_attempt = attempt == max_retries - 1

                if is_retriable and not is_last_attempt:
                    # Calcul du délai avec backoff exponentiel
                    wait_time = base_delay ** (attempt + 1)
                    error_type = getattr(e, 'type', 'unknown')
                    status_code = getattr(e, 'status_code', 'N/A')

                    logger.warning(
                        f"🔄 Anthropic API error (retriable): {error_type} (status={status_code}). "
                        f"Retry {attempt + 1}/{max_retries} after {wait_time}s... Error: {str(e)[:100]}"
                    )

                    # Attendre avant de retry
                    await asyncio.sleep(wait_time)
                else:
                    # Erreur non-retriable OU dernière tentative → lever l'exception
                    if is_last_attempt:
                        logger.error(
                            f"❌ Anthropic API error after {max_retries} attempts. "
                            f"Giving up. Error: {e}"
                        )
                    else:
                        logger.error(f"❌ Anthropic API error (non-retriable): {e}")

                    raise

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Liste tous les modèles disponibles via l'API Anthropic.

        Returns:
            List[Dict]: Liste des modèles avec leurs métadonnées
        """
        try:
            # L'API Anthropic expose un endpoint /v1/models
            models_response = await self.client.models.list()

            models = []
            provider_name = PROVIDERS["anthropic"]["name"]  # "Anthropic" from registry
            for model in models_response.data:
                models.append({
                    "id": model.id,
                    "type": model.type,
                    "display_name": model.display_name,
                    "created_at": model.created_at,
                    "provider": provider_name
                })

            return models

        except Exception as e:
            logger.error(f"Error listing Anthropic models: {e}")
            # Fallback sur la liste hardcodée si l'API ne répond pas
            logger.warning("Falling back to hardcoded Anthropic models list")
            provider_name = PROVIDERS["anthropic"]["name"]
            return [
                {
                    "id": "claude-sonnet-4-5-20250929",
                    "display_name": "Claude Sonnet 4.5",
                    "provider": provider_name,
                    "type": "model"
                },
                {
                    "id": "claude-opus-4-5",
                    "display_name": "Claude Opus 4.5",
                    "provider": provider_name,
                    "type": "model"
                },
                {
                    "id": "claude-haiku-3-5",
                    "display_name": "Claude Haiku 3.5",
                    "provider": provider_name,
                    "type": "model"
                },
            ]

    def is_retriable_error(self, exception: Exception) -> bool:
        """Détermine si l'erreur Anthropic est retriable."""
        status_code = getattr(exception, 'status_code', None)

        # Rate limits, server errors, timeouts
        if status_code in [429, 500, 502, 503, 504]:
            return True

        # Overloaded errors
        if status_code == 529:
            return True

        return False

    async def stream_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[ToolDefinition],
        **params
    ) -> AsyncGenerator[Union[str, ToolCall], None]:
        """Stream Anthropic avec détection de tool_use et retry automatique."""

        # Convertir ToolDefinition → format Anthropic
        # FIX: Ajouter type="custom" pour les outils personnalisés (requis par SDK 0.75+)
        anthropic_tools = [
            {
                "type": "custom",  # Required for custom tools in SDK 0.75+
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            }
            for tool in tools
        ]

        # DEBUG: Log détaillé des tools envoyés à Anthropic
        logger.info(f"🔧 Anthropic tools count: {len(anthropic_tools)}")
        for i, tool in enumerate(anthropic_tools):
            logger.info(f"Tool [{i}]:")
            logger.info(f"  - type: {tool.get('type')} (type: {type(tool.get('type'))})")
            logger.info(f"  - name: {tool.get('name')} (type: {type(tool.get('name'))})")
            logger.info(f"  - description: {tool.get('description')[:50]}... (type: {type(tool.get('description'))})")
            logger.info(f"  - input_schema type: {type(tool.get('input_schema'))}")
            if isinstance(tool.get('input_schema'), dict):
                logger.info(f"    - schema.type: {tool['input_schema'].get('type')}")
                logger.info(f"    - schema.properties count: {len(tool['input_schema'].get('properties', {}))}")
                logger.info(f"    - schema.required: {tool['input_schema'].get('required')}")
            else:
                logger.error(f"    ❌ input_schema is NOT a dict! Value: {tool.get('input_schema')}")
            logger.debug(f"  - Full tool: {json.dumps(tool, indent=2)}")

        # Configuration du retry
        max_retries = 3
        base_delay = 2  # secondes

        # Extraire system_prompt si présent dans params
        system_prompt = params.pop("system", None)

        # Défense en profondeur : garantir max_tokens
        if "max_tokens" not in params:
            params["max_tokens"] = PROVIDERS["anthropic"]["max_tokens"]["default"]

        # Log pour debug
        if system_prompt:
            logger.info(f"🎯 Anthropic API call (with tools) with system: {system_prompt[:80]}")
        else:
            logger.warning("⚠️ Anthropic API call (with tools) WITHOUT system prompt!")

        # FIX: Ne passer 'system' que s'il existe (SDK 0.75+ refuse None)
        stream_params = {
            "messages": messages,
            "tools": anthropic_tools,
            **params
        }
        if system_prompt:
            stream_params["system"] = system_prompt

        # Boucle de retry avec backoff exponentiel
        for attempt in range(max_retries):
            # État pour accumuler les tool calls (reset à chaque tentative)
            current_tool_use = None
            tool_input_buffer = ""

            try:
                async with self.client.messages.stream(**stream_params) as stream:
                    async for event in stream:
                        # Début d'un bloc tool_use
                        if event.type == "content_block_start":
                            if event.content_block.type == "tool_use":
                                current_tool_use = {
                                    "id": event.content_block.id,
                                    "name": event.content_block.name
                                }
                                tool_input_buffer = ""

                        # Delta des arguments JSON ou texte
                        elif event.type == "content_block_delta":
                            if event.delta.type == "input_json_delta":
                                tool_input_buffer += event.delta.partial_json
                            elif event.delta.type == "text_delta":
                                # Texte normal
                                yield event.delta.text

                        # Fin du bloc tool_use
                        elif event.type == "content_block_stop":
                            if current_tool_use:
                                # Parser les arguments accumulés (ou utiliser {} si vide)
                                if tool_input_buffer.strip():
                                    try:
                                        arguments = json.loads(tool_input_buffer)
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"Failed to parse tool arguments: {e}. Buffer: {tool_input_buffer}")
                                        arguments = {}
                                else:
                                    # Outil sans paramètres
                                    arguments = {}

                                # Yield le ToolCall complet
                                yield ToolCall(
                                    id=current_tool_use["id"],
                                    name=current_tool_use["name"],
                                    arguments=arguments
                                )

                                current_tool_use = None
                                tool_input_buffer = ""

                # Si on arrive ici, succès ! Sortir de la boucle de retry
                break

            except Exception as e:
                # Vérifier si l'erreur est retriable
                is_retriable = self.is_retriable_error(e)
                is_last_attempt = attempt == max_retries - 1

                if is_retriable and not is_last_attempt:
                    # Calcul du délai avec backoff exponentiel
                    wait_time = base_delay ** (attempt + 1)
                    error_type = getattr(e, 'type', 'unknown')
                    status_code = getattr(e, 'status_code', 'N/A')

                    logger.warning(
                        f"🔄 Anthropic API error (retriable): {error_type} (status={status_code}). "
                        f"Retry {attempt + 1}/{max_retries} after {wait_time}s... Error: {str(e)[:100]}"
                    )

                    # Attendre avant de retry
                    await asyncio.sleep(wait_time)
                else:
                    # Erreur non-retriable OU dernière tentative → lever l'exception
                    if is_last_attempt:
                        logger.error(
                            f"❌ Anthropic API error after {max_retries} attempts. "
                            f"Giving up. Error: {e}"
                        )
                    else:
                        logger.error(f"❌ Anthropic API error (non-retriable): {e}")

                    raise

    def transform_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None
    ) -> tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        Transforme les messages pour Anthropic.
        Anthropic utilise un paramètre 'system' séparé.

        Returns:
            tuple: (messages, extra_params avec system si présent)
        """
        extra_params = {}
        if system_prompt:
            extra_params["system"] = system_prompt
            logger.info(f"🔧 Anthropic adapter: System prompt set ({len(system_prompt)} chars): {system_prompt[:80]}")
        else:
            logger.warning("⚠️ Anthropic adapter: No system prompt provided!")

        # Anthropic n'accepte pas de message system dans la liste
        filtered_messages = [m for m in messages if m.get("role") != "system"]

        return filtered_messages, extra_params
