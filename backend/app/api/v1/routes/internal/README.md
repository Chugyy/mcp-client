# Internal MCP Endpoints - Routing Pattern

## Unified Architecture

All internal MCP services **MUST** follow this consistent pattern:

```
/api/internal/{service}/mcp/
```

## Pattern Structure

### Router Configuration

```python
router = APIRouter(
    prefix="/{service}/mcp",
    tags=["Internal MCP - {Service}"]
)
```

### Endpoint Definition

```python
@router.post("/")
async def mcp_handler(request: JsonRpcRequest, ...):
    """Main JSON-RPC endpoint for MCP protocol."""
    pass

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "internal-mcp-{service}"}
```

## Examples

### RAG Service

- **Router prefix:** `/rag/mcp`
- **JSON-RPC endpoint:** `POST /api/internal/rag/mcp/`
- **Health check:** `GET /api/internal/rag/mcp/health`

### Automation Service

- **Router prefix:** `/automation/mcp`
- **JSON-RPC endpoint:** `POST /api/internal/automation/mcp/`
- **Health check:** `GET /api/internal/automation/mcp/health`

## Server Definition

In `/app/core/system/definitions/servers.py`, define servers with **base URL only** (without `/mcp/` suffix):

```python
INTERNAL_SERVERS = [
    {
        "id": "srv_internal_{service}",
        "url": f"{settings.api_url}/api/internal/{service}",  # ← No /mcp/ here
        "auth_type": "none",
        "is_system": True,
        # ...
    }
]
```

## How It Works

The MCP protocol standard requires JSON-RPC endpoints at `/mcp/` path:

1. **Server URL defined:** `/api/internal/{service}`
2. **HTTPMCPClient auto-appends:** `/mcp/`
3. **Final URL:** `/api/internal/{service}/mcp/`
4. **FastAPI router:** `/api/internal` + `/{service}/mcp` + `/` = `/api/internal/{service}/mcp/`

**Result:** Perfect match between client and server paths.

## Benefits

- **Consistency:** All internal MCP services follow the same pattern
- **MCP Standard:** Respects JSON-RPC at `/mcp/` requirement
- **Clarity:** Service name comes before protocol identifier
- **Scalability:** Easy to add new internal MCP services
- **No Redundancy:** `/mcp/` appears exactly once

## Adding a New Internal MCP Service

1. Create router file: `/app/api/v1/routes/internal/mcp/{service}.py`
2. Set router prefix: `prefix="/{service}/mcp"`
3. Define JSON-RPC endpoint: `@router.post("/")`
4. Add health check: `@router.get("/health")`
5. Register in `main.py`: `internal_router.include_router({service}_router)`
6. Add to `servers.py`: `url = f"{settings.api_url}/api/internal/{service}"`

## Anti-Patterns (DO NOT USE)

### ❌ Protocol before service
```python
prefix="/mcp/{service}"  # Wrong order
```

### ❌ Double /mcp/ path
```python
prefix="/{service}/mcp"
@router.post("/mcp/")  # Creates redundant /api/internal/{service}/mcp/mcp/
```

### ❌ Including /mcp/ in server URL
```python
"url": f"{settings.api_url}/api/internal/{service}/mcp"  # HTTPMCPClient will add /mcp/ again
```

## Reference Files

- **Router definitions:** `/app/api/v1/routes/internal/mcp/*.py`
- **Server definitions:** `/app/core/system/definitions/servers.py`
- **HTTP MCP Client:** `/app/core/services/mcp/clients.py` (line 126)
- **Main router mount:** `/app/api/main.py` (line 169)
