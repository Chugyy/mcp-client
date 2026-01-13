"""Tests for MCP tool discovery."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.services.mcp.clients import HTTPMCPClient, StdioMCPClient


@pytest.mark.asyncio
async def test_http_list_tools_success():
    """Test listing tools from HTTP MCP server."""
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
            "tools": [
                {
                    "name": "test_tool",
                    "description": "A test tool",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "echo_tool",
                    "description": "Echo tool",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            ]
        }
    }

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await client.list_tools()

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["tools"]) == 2
        assert result["tools"][0]["name"] == "test_tool"


@pytest.mark.asyncio
async def test_http_list_tools_empty():
    """Test listing tools when server returns empty list."""
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
            "tools": []
        }
    }

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await client.list_tools()

        assert result["success"] is True
        assert result["count"] == 0
        assert result["tools"] == []


@pytest.mark.asyncio
async def test_http_list_tools_authentication_failure():
    """Test tool discovery with authentication failure."""
    client = HTTPMCPClient(
        server_id="server-123",
        url="http://localhost:8080",
        auth_type="oauth",
        api_key_id="key-123"
    )

    # Mock failed authentication
    with patch.object(client, '_get_access_token', new_callable=AsyncMock, return_value=None):
        result = await client.list_tools()

        assert result["success"] is False
        assert "Authentication failed" in result["error"]
        assert result["count"] == 0


@pytest.mark.asyncio
async def test_http_list_tools_timeout():
    """Test tool discovery timeout handling."""
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

        result = await client.list_tools()

        assert result["success"] is False
        assert "Timeout" in result["error"]
        assert result["count"] == 0


@pytest.mark.asyncio
async def test_http_list_tools_invalid_schema():
    """Test tool discovery with malformed tool schema."""
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
            "tools": [
                {
                    "name": "valid_tool",
                    "description": "Valid tool",
                    "inputSchema": {"type": "object"}
                },
                {
                    # Missing required fields
                    "name": "incomplete_tool"
                }
            ]
        }
    }

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await client.list_tools()

        # Should still succeed but include incomplete tool data
        assert result["success"] is True
        assert result["count"] == 2
