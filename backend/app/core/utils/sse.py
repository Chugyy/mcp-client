#!/usr/bin/env python3
# app/core/utils/sse.py
"""
Utilitaires pour Server-Sent Events (SSE).

SSE est le standard W3C pour le streaming HTTP unidirectionnel.
Format : event: <type>\ndata: <json>\n\n
"""

import json
from enum import Enum
from typing import Dict, Any


class StreamEventType(str, Enum):
    """
    Types d'events SSE supportés pour le streaming de chat.

    Attributes:
        CHUNK: Chunk de texte de la réponse LLM
        SOURCES: Sources RAG utilisées pour la réponse
        VALIDATION_REQUIRED: Validation humaine requise pour un tool call
        STOPPED: Stream arrêté par l'utilisateur
        ERROR: Erreur durant le streaming
        DONE: Stream terminé avec succès
    """
    CHUNK = "chunk"
    SOURCES = "sources"
    VALIDATION_REQUIRED = "validation_required"
    STOPPED = "stopped"
    ERROR = "error"
    DONE = "done"


def sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """
    Formate un event SSE selon le standard W3C.

    Format SSE standard:
        event: <type>
        data: <json>
        <ligne vide>

    Args:
        event_type: Type de l'event (voir StreamEventType)
        data: Données de l'event (sera sérialisé en JSON)

    Returns:
        str: Event SSE formaté avec newlines

    Example:
        >>> sse_event("chunk", {"content": "Hello"})
        'event: chunk\\ndata: {"content": "Hello"}\\n\\n'

        >>> sse_event("error", {"message": "Connection lost"})
        'event: error\\ndata: {"message": "Connection lost"}\\n\\n'

    Notes:
        - Le JSON encode automatiquement les caractères spéciaux
        - Le double newline final est obligatoire pour le parsing SSE
        - Compatible avec EventSource (navigateur) et parsers SSE standards
    """
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {json_data}\n\n"
