"""Serveurs MCP internes - Source de vérité unique."""

from config.config import settings

INTERNAL_SERVERS = [
    {
        "id": "srv_internal_rag",
        "user_id": "__internal__",
        "name": "Internal RAG Tools",
        "description": "Internal MCP server for RAG tools (search_resources, list_resources)",
        "url": f"{settings.api_url}/api/internal/rag",
        "auth_type": "none",
        "is_system": True,
        "is_public": False,
        "status": "active",
        "enabled": True
    },
    {
        "id": "srv_internal_automation",
        "user_id": "__internal__",
        "name": "Internal Automation Tools",
        "description": "Internal MCP server for automation tools (create_automation, add_workflow_step, add_trigger, test_automation)",
        "url": f"{settings.api_url}/api/internal/automation",
        "auth_type": "none",
        "is_system": True,
        "is_public": False,
        "status": "active",
        "enabled": True
    }
]
