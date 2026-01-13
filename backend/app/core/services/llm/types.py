# app/core/services/llm/types.py
"""Types de données pour le tool calling."""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ToolDefinition:
    """Format unifié d'un tool pour tous les providers."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_id: Optional[str] = None  # Pour retrouver le serveur MCP
    is_default: bool = False  # Auto-attaché à tous les agents
    is_removable: bool = True  # Peut être détaché d'un agent


@dataclass
class ToolCall:
    """Un appel de tool détecté dans le stream."""
    id: str
    name: str
    arguments: Dict[str, Any]  # Accumulé depuis les deltas


@dataclass
class ToolResult:
    """Résultat d'exécution d'un tool."""
    tool_call_id: str
    content: str
    is_error: bool = False
