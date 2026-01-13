from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Any, Optional
import weather_tools

app = FastAPI(title="Weather MCP Server (API Key)")

API_KEY = "test-weather-api-key-123"

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

async def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify the API key from the Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    token = authorization.replace("Bearer ", "")
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True

@app.get("/health")
async def health():
    """Health check endpoint (no auth required)."""
    return {"status": "ok"}

@app.post("/mcp", dependencies=[Depends(verify_api_key)])
async def mcp_handler(request: JsonRpcRequest):
    """Main JSON-RPC endpoint for MCP protocol (requires API key)."""

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
                    "name": "weather-apikey",
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
                        "description": "Get weather alerts for a US state",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "state": {
                                    "type": "string",
                                    "description": "Two-letter US state code (e.g. CA, NY)"
                                }
                            },
                            "required": ["state"]
                        }
                    },
                    {
                        "name": "get_forecast",
                        "description": "Get weather forecast for a location",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "latitude": {
                                    "type": "number",
                                    "description": "Latitude of the location"
                                },
                                "longitude": {
                                    "type": "number",
                                    "description": "Longitude of the location"
                                }
                            },
                            "required": ["latitude", "longitude"]
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
                state = arguments.get("state")
                if not state:
                    return JsonRpcResponse(
                        jsonrpc="2.0",
                        id=request.id,
                        error={
                            "code": -32602,
                            "message": "Missing required parameter: state"
                        }
                    )
                result = await weather_tools.get_alerts(state)
                return JsonRpcResponse(
                    jsonrpc="2.0",
                    id=request.id,
                    result={"content": [{"type": "text", "text": result}]}
                )

            elif tool_name == "get_forecast":
                latitude = arguments.get("latitude")
                longitude = arguments.get("longitude")
                if latitude is None or longitude is None:
                    return JsonRpcResponse(
                        jsonrpc="2.0",
                        id=request.id,
                        error={
                            "code": -32602,
                            "message": "Missing required parameters: latitude and/or longitude"
                        }
                    )
                result = await weather_tools.get_forecast(latitude, longitude)
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
    uvicorn.run(app, host="127.0.0.1", port=9001)
