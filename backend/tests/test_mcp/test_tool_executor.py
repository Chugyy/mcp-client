"""Tests for MCP tool execution."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.services.mcp.clients import HTTPMCPClient, StdioMCPClient


@pytest.mark.asyncio
async def test_http_call_tool_success():
    """Test successful HTTP tool execution."""
    client = HTTPMCPClient(
        server_id="server-123",
        url="http://localhost:8080",
        auth_type="none"
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {"type": "text", "text": "Processed: test input"}
            ]
        }
    }

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await client.call_tool("test_tool", {"input": "test input"})

        assert result["success"] is True
        assert result["result"]["content"][0]["text"] == "Processed: test input"
        assert result["error"] is None


@pytest.mark.asyncio
async def test_http_call_tool_with_parameters():
    """Test tool execution with complex parameters."""
    client = HTTPMCPClient(
        server_id="server-123",
        url="http://localhost:8080",
        auth_type="none"
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {"type": "text", "text": "Success"}
            ]
        }
    }

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Complex parameters
        params = {
            "query": "test query",
            "options": {
                "limit": 10,
                "filters": ["tag1", "tag2"]
            },
            "metadata": True
        }

        result = await client.call_tool("search_tool", params)

        assert result["success"] is True
        # Verify parameters were sent correctly
        call_args = mock_client.post.call_args
        sent_payload = call_args.kwargs["json"]
        assert sent_payload["params"]["arguments"] == params


@pytest.mark.asyncio
async def test_http_call_tool_error_response():
    """Test tool execution with error response from server."""
    client = HTTPMCPClient(
        server_id="server-123",
        url="http://localhost:8080",
        auth_type="none"
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {
            "code": -32601,
            "message": "Unknown tool: invalid_tool"
        }
    }

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await client.call_tool("invalid_tool", {})

        assert result["success"] is False
        assert "Unknown tool" in result["error"]


@pytest.mark.asyncio
async def test_http_call_tool_timeout():
    """Test tool execution timeout handling."""
    import httpx

    client = HTTPMCPClient(
        server_id="server-123",
        url="http://localhost:8080",
        auth_type="none"
    )

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await client.call_tool("slow_tool", {})

        assert result["success"] is False
        assert "Timeout" in result["error"]


@pytest.mark.asyncio
async def test_http_call_tool_http_error():
    """Test tool execution HTTP error handling (non-200 status)."""
    client = HTTPMCPClient(
        server_id="server-123",
        url="http://localhost:8080",
        auth_type="none"
    )

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await client.call_tool("test_tool", {})

        assert result["success"] is False
        assert "HTTP 500" in result["error"]


@pytest.mark.asyncio
async def test_http_call_tool_authentication_failure():
    """Test tool execution with authentication failure."""
    client = HTTPMCPClient(
        server_id="server-123",
        url="http://localhost:8080",
        auth_type="oauth",
        api_key_id="key-123"
    )

    # Mock failed authentication
    with patch.object(client, '_get_access_token', new_callable=AsyncMock, return_value=None):
        result = await client.call_tool("test_tool", {"input": "test"})

        assert result["success"] is False
        assert "Authentication failed" in result["error"]


@pytest.mark.asyncio
async def test_http_call_tool_multiple_concurrent():
    """Test concurrent tool execution."""
    import asyncio

    client = HTTPMCPClient(
        server_id="server-123",
        url="http://localhost:8080",
        auth_type="none"
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [{"type": "text", "text": "Success"}]
        }
    }

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Execute 5 tools concurrently
        tasks = [
            client.call_tool(f"tool_{i}", {"input": f"test_{i}"})
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r["success"] for r in results)
        assert len(results) == 5
