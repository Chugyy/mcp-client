# MCP Server Management Test Suite

This directory contains tests for MCP (Model Context Protocol) server management functionality.

## Test Structure

```
tests/test_mcp/
├── __init__.py
├── test_server_manager.py      # Server lifecycle tests (9 tests)
├── test_tool_discovery.py      # Tool discovery tests (5 tests)
├── test_tool_executor.py       # Tool execution tests (7 tests)
└── test_mcp_integration.py     # Integration tests (5 tests)
```

## Current Status

**Story 1.9 Implementation:**
- ✅ 18/26 tests passing
- ⏭️ 8/26 tests skipped (31%)
- 📊 Coverage: 25% (target: 85%)
- ⏱️ Execution time: 1.39s

**Test Breakdown:**
- `test_server_manager.py`: 6/9 passing (3 skipped)
- `test_tool_discovery.py`: 5/5 passing
- `test_tool_executor.py`: 7/7 passing
- `test_mcp_integration.py`: 0/5 passing (5 skipped)

## Limitations & Known Issues

### 1. Database Integration Missing

**Issue:** 8 tests skipped due to lack of real database fixtures

**Affected Tests:**
- `test_server_deletion_success` (test_server_manager.py:129)
- `test_server_deletion_with_impact_requires_force` (test_server_manager.py:163)
- `test_server_deletion_system_server_protected` (test_server_manager.py:196)
- All tests in `test_mcp_integration.py` (5 tests)

**Why:**
- Tests require complete Server model with DB fields (created_at, updated_at, user_id, etc.)
- Mocking complete DB models adds complexity without testing real integration logic
- Cascade deletion logic requires real foreign key constraints

**Resolution:** See Story 1.9.1 for real DB integration

### 2. Mock Server Not Used

**Issue:** `tests/mocks/mock_mcp_server.py` created but never used in actual tests

**Why:**
- Current tests use mocked HTTP responses instead of real stdio transport
- StdioMCPClient and DockerMCPClient not tested with real subprocesses

**Impact:**
- Stdio transport protocol not validated
- JSON-RPC over stdio pipes not tested

**Resolution:** Story 1.9.1 will add stdio transport tests using mock_mcp_server

### 3. Coverage Gap

**Current Coverage:**
```
app/core/services/mcp/clients.py:      31%  (StdioMCPClient/DockerMCPClient not tested)
app/core/services/mcp/manager.py:      59%  (delete logic partially tested)
app/core/services/mcp/oauth_manager.py: 0%  (OAuth flows not tested)
app/core/services/mcp/validator.py:    20%  (tested indirectly only)
TOTAL:                                 25%  (target: 85%)
```

**Missing Tests:**
- Server crash recovery (AC #66)
- Zombie process cleanup (AC #67)
- Concurrent server management (AC #68)
- Tool schema validation (AC #73)
- Retry logic with exponential backoff (AC #84)
- OAuth authentication flow (AC #89)
- Server reconnection after failure (AC #91)
- Resource cleanup on agent deletion (AC #92)

**Resolution:** Story 1.9.1 targets 85%+ coverage

## Running Tests

### Run All MCP Tests
```bash
pytest tests/test_mcp/ -v
```

### Run Specific Test File
```bash
pytest tests/test_mcp/test_server_manager.py -v
```

### Run with Coverage Report
```bash
pytest tests/test_mcp/ --cov=app/core/services/mcp --cov-report=term-missing
```

### Run Only Passing Tests (exclude skipped)
```bash
pytest tests/test_mcp/ -v -k "not skip"
```

## Test Fixtures

### Available Fixtures (conftest.py)

**mock_mcp_server**
- Real subprocess running mock MCP server
- Communicates via stdio (JSON-RPC)
- Tools: test_tool, echo_tool, crash_tool, timeout_tool
- Usage: `async def test_example(mock_mcp_server):`

**sample_server_config**
- Sample stdio server configuration
- Type: npx
- Command: python tests/mocks/mock_mcp_server.py

**sample_http_server_config**
- Sample HTTP server configuration
- Type: http
- URL: http://localhost:8080

## Test Patterns

### Unit Test with Mocks (Current)
```python
@pytest.mark.asyncio
async def test_http_list_tools_success():
    """Test listing tools from HTTP MCP server."""
    client = HTTPMCPClient(
        server_id="server-123",
        url="http://localhost:8080",
        auth_type="none"
    )

    with patch('httpx.AsyncClient') as mock_client:
        # Mock HTTP response
        result = await client.list_tools()
        assert result["success"] is True
```

### Integration Test with Real DB (Planned - Story 1.9.1)
```python
@pytest.mark.asyncio
async def test_server_deletion_success(db_pool, db_server):
    """Test successful server deletion with real DB."""
    server_id = db_server["id"]

    # Real DB operations
    await ServerManager.delete(server_id, user_id, force=False)

    # Verify from DB
    server = await get_server(server_id)
    assert server is None
```

### Stdio Transport Test (Planned - Story 1.9.1)
```python
@pytest.mark.asyncio
async def test_stdio_transport(mock_mcp_server):
    """Test StdioMCPClient with real subprocess."""
    client = StdioMCPClient(
        server_id="test",
        process=mock_mcp_server
    )

    tools = await client.list_tools()
    assert tools["count"] == 2
```

## Dependencies

**Current:**
- pytest
- pytest-asyncio
- unittest.mock

**Planned (Story 1.9.1):**
- pytest-postgresql (for real DB fixtures)
- pytest-cov (for coverage reporting)

## Next Steps

See **Story 1.9.1** for:
- Real database integration
- Stdio transport tests
- Critical flow tests (crash recovery, retry logic, zombie cleanup)
- Target: 85%+ coverage, 0 skipped tests

## Related Documentation

- Story 1.9: `docs/stories/story-1.9-mcp-server-management-test-suite.md`
- Story 1.9.1: `docs/stories/story-1.9.1-mcp-integration-tests-with-real-db.md`
- MCP Services: `app/core/services/mcp/`
- Mock Server: `tests/mocks/mock_mcp_server.py`
