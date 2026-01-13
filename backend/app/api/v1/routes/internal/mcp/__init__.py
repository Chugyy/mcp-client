"""Internal MCP routers."""

from app.api.v1.routes.internal.mcp.rag import router as rag_router
from app.api.v1.routes.internal.mcp.automation import router as automation_router

__all__ = ['rag_router', 'automation_router']
