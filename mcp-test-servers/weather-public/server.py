from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Optional
import weather_tools

app = FastAPI(title="Weather MCP Server (Public)")

class JsonRpcRequest(BaseModel):
    jsonrpc: str
    id: int
    method: str
    params: Optional[dict] = {}

class JsonRpcResponse(BaseModel):
    jsonrpc: str
    id: int
    result: Optional[Any] = None
    error: Optional[dict] = None

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/mcp/")
async def mcp_handler(request: JsonRpcRequest):
    """Main JSON-RPC endpoint for MCP protocol."""

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
                    "name": "weather",
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
                "tools": [
                    {
                        "name": "get_alerts",
                        "description": "Get random weather alerts for a major city (Paris, New York, London, Tokyo, Sydney, Berlin, Rome, Madrid, Moscow, Beijing)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "city": {
                                    "type": "string",
                                    "description": "City name (e.g. Paris, New York, London)"
                                }
                            },
                            "required": ["city"]
                        }
                    },
                    {
                        "name": "get_forecast",
                        "description": "Get random weather forecast for a major city (Paris, New York, London, Tokyo, Sydney, Berlin, Rome, Madrid, Moscow, Beijing)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "city": {
                                    "type": "string",
                                    "description": "City name (e.g. Paris, New York, London)"
                                }
                            },
                            "required": ["city"]
                        }
                    }
                ]
            }
        )

    # Handle tools/call method
    elif request.method == "tools/call":
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})

        try:
            if tool_name == "get_alerts":
                city = arguments.get("city")
                if not city:
                    return JsonRpcResponse(
                        jsonrpc="2.0",
                        id=request.id,
                        error={
                            "code": -32602,
                            "message": "Missing required parameter: city"
                        }
                    )
                result = await weather_tools.get_alerts(city)
                return JsonRpcResponse(
                    jsonrpc="2.0",
                    id=request.id,
                    result={"content": [{"type": "text", "text": result}]}
                )

            elif tool_name == "get_forecast":
                city = arguments.get("city")
                if not city:
                    return JsonRpcResponse(
                        jsonrpc="2.0",
                        id=request.id,
                        error={
                            "code": -32602,
                            "message": "Missing required parameter: city"
                        }
                    )
                result = await weather_tools.get_forecast(city)
                return JsonRpcResponse(
                    jsonrpc="2.0",
                    id=request.id,
                    result={"content": [{"type": "text", "text": result}]}
                )

            else:
                return JsonRpcResponse(
                    jsonrpc="2.0",
                    id=request.id,
                    error={
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}"
                    }
                )

        except Exception as e:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)
