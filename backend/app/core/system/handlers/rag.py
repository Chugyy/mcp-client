"""Handlers pour les tools RAG (Retrieval-Augmented Generation)."""

from typing import Dict, Any
from app.core.system.handler import tool_handler
from config.logger import logger


@tool_handler("search_resources")
async def handle_search_resources(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Recherche dans les ressources attachées à l'agent."""
    from app.core.services.resources.rag import search

    query = arguments.get("query")
    top_k = arguments.get("top_k", 5)
    resource_ids = arguments.get("_resource_ids", [])

    # Si aucune query fournie, utiliser une query générique pour obtenir un aperçu
    if not query:
        query = "summary overview main topics content information"
        # Augmenter top_k pour un meilleur aperçu
        if top_k == 5:
            top_k = 10
        logger.info(f"No query provided, using generic query for document overview with top_k={top_k}")

    results = await search.search(query, resource_ids, top_k)

    return {
        "success": True,
        "result": results,
        "error": None
    }


@tool_handler("list_resources")
async def handle_list_resources(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Liste toutes les ressources attachées à l'agent."""
    from app.core.services.resources.rag import search

    resource_ids = arguments.get("_resource_ids", [])
    resources = await search.list_resources(resource_ids)

    return {
        "success": True,
        "result": resources,
        "error": None
    }
