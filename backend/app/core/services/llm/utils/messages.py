# app/core/services/llm/utils/messages.py
"""Utilitaires pour formater les messages selon les providers."""

import json
from typing import List, Dict, Any
from ..types import ToolCall, ToolResult


def append_tool_call_for_anthropic(
    messages: List[Dict[str, Any]],
    tool_calls: List[ToolCall]
) -> List[Dict[str, Any]]:
    """
    Ajoute un message assistant avec tool_use pour Anthropic.

    Args:
        messages: Liste des messages existants
        tool_calls: Liste des tool calls à ajouter

    Returns:
        Liste des messages mise à jour
    """
    content_blocks = [
        {
            "type": "tool_use",
            "id": tc.id,
            "name": tc.name,
            "input": tc.arguments
        }
        for tc in tool_calls
    ]

    messages.append({
        "role": "assistant",
        "content": content_blocks
    })

    return messages


def append_tool_results_for_anthropic(
    messages: List[Dict[str, Any]],
    results: List[ToolResult]
) -> List[Dict[str, Any]]:
    """
    Ajoute les résultats des tools pour Anthropic.

    Args:
        messages: Liste des messages existants
        results: Liste des résultats de tools

    Returns:
        Liste des messages mise à jour
    """
    content_blocks = [
        {
            "type": "tool_result",
            "tool_use_id": result.tool_call_id,
            "content": result.content,
            "is_error": result.is_error
        }
        for result in results
    ]

    messages.append({
        "role": "user",
        "content": content_blocks
    })

    return messages


def append_tool_call_for_openai(
    messages: List[Dict[str, Any]],
    tool_calls: List[ToolCall]
) -> List[Dict[str, Any]]:
    """
    Ajoute un message assistant avec tool_calls pour OpenAI.

    Args:
        messages: Liste des messages existants
        tool_calls: Liste des tool calls à ajouter

    Returns:
        Liste des messages mise à jour
    """
    tool_calls_formatted = [
        {
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.name,
                "arguments": json.dumps(tc.arguments)
            }
        }
        for tc in tool_calls
    ]

    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": tool_calls_formatted
    })

    return messages


def append_tool_results_for_openai(
    messages: List[Dict[str, Any]],
    results: List[ToolResult]
) -> List[Dict[str, Any]]:
    """
    Ajoute les résultats des tools pour OpenAI.

    Args:
        messages: Liste des messages existants
        results: Liste des résultats de tools

    Returns:
        Liste des messages mise à jour
    """
    for result in results:
        messages.append({
            "role": "tool",
            "tool_call_id": result.tool_call_id,
            "content": result.content
        })

    return messages
