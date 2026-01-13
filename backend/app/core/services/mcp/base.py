#!/usr/bin/env python3
# app/core/services/mcp/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any


class MCPClient(ABC):
    """
    Interface commune pour tous les clients MCP.

    Définit le contrat que doivent respecter les implémentations HTTP et stdio.
    """

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """
        Appelle un outil MCP.

        Args:
            tool_name: Nom de l'outil à appeler
            arguments: Arguments à passer à l'outil

        Returns:
            {
                "success": bool,
                "result": Any,
                "error": Optional[str]
            }
        """
        pass

    @abstractmethod
    async def list_tools(self) -> Dict[str, Any]:
        """
        Liste les outils disponibles sur le serveur.

        Returns:
            {
                "success": bool,
                "tools": List[dict],  # [{"name": "...", "description": "..."}]
                "count": int,
                "error": Optional[str]
            }
        """
        pass

    @abstractmethod
    async def verify(self) -> Dict[str, Any]:
        """
        Vérifie la connexion et la santé du serveur.

        Returns:
            {
                "status": str,  # 'active', 'failed', 'unreachable'
                "status_message": Optional[str],
                "tools": List[dict]
            }
        """
        pass
