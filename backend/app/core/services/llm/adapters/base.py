# app/core/llm/adapters/base.py
"""Interface de base pour tous les adapters LLM."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, List, Union
from ..types import ToolDefinition, ToolCall


class BaseAdapter(ABC):
    """Interface de base pour les adapters LLM."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        **params
    ) -> AsyncGenerator[str, None]:
        """
        Stream la réponse du LLM.

        Args:
            messages: Liste des messages au format [{"role": "user", "content": "..."}]
            **params: Paramètres spécifiques au provider (déjà transformés)

        Yields:
            str: Chunks de texte au fur et à mesure
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Liste tous les modèles disponibles pour ce provider.

        Returns:
            List[Dict]: Liste des modèles avec leurs métadonnées
        """
        pass

    @abstractmethod
    def is_retriable_error(self, exception: Exception) -> bool:
        """
        Détermine si une erreur justifie un retry.

        Args:
            exception: L'exception levée

        Returns:
            bool: True si l'erreur est retriable (429, 500, 503, etc.)
        """
        pass

    @abstractmethod
    async def stream_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[ToolDefinition],
        **params
    ) -> AsyncGenerator[Union[str, ToolCall], None]:
        """
        Stream avec support des tool calls.

        Args:
            messages: Liste des messages au format [{"role": "user", "content": "..."}]
            tools: Liste des tools disponibles
            **params: Paramètres spécifiques au provider (déjà transformés)

        Yields:
            Union[str, ToolCall]:
                - str pour les chunks de texte
                - ToolCall quand un tool est détecté (arguments complets)
        """
        pass

    def transform_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None
    ) -> List[Dict[str, str]]:
        """
        Transforme les messages au format du provider.
        Par défaut, garde le format standard.

        Args:
            messages: Messages au format unifié
            system_prompt: Prompt système optionnel

        Returns:
            List[Dict]: Messages au format du provider
        """
        if system_prompt:
            return [{"role": "system", "content": system_prompt}] + messages
        return messages
