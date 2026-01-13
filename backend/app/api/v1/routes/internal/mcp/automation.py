"""
Internal MCP Router - Automation Tools
Expose automation tools (create_automation, add_workflow_step, etc.) via JSON-RPC protocol.
"""

from fastapi import APIRouter, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
from config.logger import logger
from app.core.system import handler
# Import pour auto-registration des handlers
from app.core.system import handlers  # noqa: F401
from app.core.system.definitions.tools.automation import AUTOMATION_TOOLS

# Utiliser le nouveau handler
execute = handler.execute

router = APIRouter(
    prefix="/automation/mcp",
    tags=["Internal MCP - Automation"]
)


# ============================
# MODÈLES JSON-RPC
# ============================

class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 Request."""
    jsonrpc: str
    id: int
    method: str
    params: Optional[Dict[str, Any]] = {}


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 Response."""
    jsonrpc: str
    id: int
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


# ============================
# AUTHENTIFICATION
# ============================

def extract_user_from_header(
    x_internal_user_id: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Extrait le user_id depuis le header interne X-Internal-User-ID.

    Note: Pour les appels internes, le user_id est passé via ce header.
    L'authentification JWT est déjà gérée par le backend principal.
    """
    if x_internal_user_id:
        logger.debug(f"🔐 [MCP Automation] User ID: {x_internal_user_id}")
        return x_internal_user_id

    logger.warning("⚠️  [MCP Automation] No user_id provided in header")
    return None


# ============================
# TOOLS MCP
# ============================

# Convertir ToolDefinition en format MCP
AUTOMATION_TOOLS_MCP = [
    {
        "name": tool.name,
        "description": tool.description,
        "inputSchema": tool.input_schema
    }
    for tool in AUTOMATION_TOOLS
]


# ============================
# ENDPOINTS
# ============================

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "internal-mcp-automation"}


@router.post("/")
async def mcp_handler(
    request: JsonRpcRequest,
    user_id: Optional[str] = Header(None, alias="X-Internal-User-ID")
):
    """
    Main JSON-RPC endpoint for MCP protocol (Automation tools).

    Supported methods:
    - initialize: Initialize MCP connection
    - tools/list: List available automation tools
    - tools/call: Execute an automation tool
    """

    # Handle initialize method
    if request.method == "initialize":
        return JsonRpcResponse(
            jsonrpc="2.0",
            id=request.id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "internal-mcp-automation",
                    "version": "1.0.0"
                }
            }
        )

    # Handle tools/list method
    elif request.method == "tools/list":
        return JsonRpcResponse(
            jsonrpc="2.0",
            id=request.id,
            result={
                "tools": AUTOMATION_TOOLS_MCP
            }
        )

    # Handle tools/call method
    elif request.method == "tools/call":
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})

        logger.info(f"🔧 [MCP Automation] Tool call: {tool_name}")
        logger.debug(f"📦 [MCP Automation] Arguments: {arguments}")

        # Injecter le user_id pour les tools automation (ownership)
        if user_id:
            arguments["_user_id"] = user_id
            logger.debug(f"✅ [MCP Automation] _user_id injected: {user_id}")
        else:
            logger.warning(f"⚠️  [MCP Automation] No user_id for tool {tool_name}")

        try:
            # Appel au handler interne
            exec_result = await execute(tool_name, arguments)

            # Vérifier si l'exécution a réussi
            if not exec_result.get("success"):
                return JsonRpcResponse(
                    jsonrpc="2.0",
                    id=request.id,
                    error={
                        "code": -32603,
                        "message": exec_result.get("error", "Unknown error")
                    }
                )

            # Format MCP standard: result doit contenir "content"
            result_data = exec_result.get("result")

            # Formater le résultat en texte
            if isinstance(result_data, (dict, list)):
                text_result = json.dumps(result_data, indent=2, ensure_ascii=False)
            else:
                text_result = str(result_data)

            return JsonRpcResponse(
                jsonrpc="2.0",
                id=request.id,
                result={"content": [{"type": "text", "text": text_result}]}
            )

        except Exception as e:
            logger.error(f"❌ [MCP Automation] Error: {e}")
            return JsonRpcResponse(
                jsonrpc="2.0",
                id=request.id,
                error={
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            )

    # Unknown method
    else:
        return JsonRpcResponse(
            jsonrpc="2.0",
            id=request.id,
            error={
                "code": -32601,
                "message": f"Method not found: {request.method}"
            }
        )
