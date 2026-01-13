"""Tools internes pour la recherche de ressources (RAG)."""

from app.core.services.llm.types import ToolDefinition

RAG_TOOLS = [
    ToolDefinition(
        name="search_resources",
        description="Search through user resources using semantic search (RAG). Returns relevant chunks from documents.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 5
                }
            },
            "required": []
        },
        is_default=True,
        is_removable=False
    ),
    ToolDefinition(
        name="list_resources",
        description="List all available resources for the current context",
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        },
        is_default=True,
        is_removable=False
    )
]
