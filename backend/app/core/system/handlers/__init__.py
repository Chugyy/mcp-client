"""
Handlers modulaires pour les tools internes.

L'import de ces modules déclenche l'auto-registration via @tool_handler.
"""

from . import automation
from . import rag
from . import discovery

__all__ = ["automation", "rag", "discovery"]
