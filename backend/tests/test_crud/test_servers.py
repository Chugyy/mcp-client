"""Integration tests for servers (MCP) CRUD module."""

import pytest
from app.database.crud import servers



@pytest.fixture
async def sample_server(clean_db, sample_user, mock_pool_for_crud):
    """Create a sample MCP server for testing."""
    server_id = await servers.create_server(
        name="Test Server",
        url="https://test.mcp.server",
        auth_type="none",
        description="A test MCP server",
        user_id=sample_user["id"]
    )
    server = await servers.get_server(server_id)
    return server


@pytest.mark.asyncio
async def test_create_server(clean_db, sample_user, mock_pool_for_crud):
    """Test creating an MCP server."""
    server_id = await servers.create_server(
        name="New MCP Server",
        url="https://example.mcp.com",
        auth_type="api-key",
        description="Test server",
        user_id=sample_user["id"]
    )

    assert server_id is not None
    assert server_id.startswith("srv_")

    server = await servers.get_server(server_id)
    assert server["name"] == "New MCP Server"
    assert server["url"] == "https://example.mcp.com"


@pytest.mark.asyncio
async def test_get_server_by_id(clean_db, sample_server, mock_pool_for_crud):
    """Test getting server by ID."""
    server = await servers.get_server(sample_server["id"])

    assert server is not None
    assert server["id"] == sample_server["id"]


@pytest.mark.asyncio
async def test_update_server_config(clean_db, sample_server, mock_pool_for_crud):
    """Test updating server configuration."""
    success = await servers.update_server(
        sample_server["id"],
        name="Updated Server Name",
        url="https://updated.url.com"
    )
    assert success is True

    server = await servers.get_server(sample_server["id"])
    assert server["name"] == "Updated Server Name"
    assert server["url"] == "https://updated.url.com"


@pytest.mark.asyncio
async def test_delete_server(clean_db, sample_server, mock_pool_for_crud):
    """Test deleting a server."""
    success = await servers.delete_server(sample_server["id"])
    assert success is True

    server = await servers.get_server(sample_server["id"])
    assert server is None


@pytest.mark.asyncio
async def test_list_servers_with_filters(clean_db, sample_user, mock_pool_for_crud):
    """Test listing servers with enabled filter."""
    # Create enabled and disabled servers
    enabled_id = await servers.create_server(
        name="Enabled Server",
        url="https://enabled.com",
        auth_type="none",
        user_id=sample_user["id"],
        enabled=True
    )
    await servers.create_server(
        name="Disabled Server",
        url="https://disabled.com",
        auth_type="none",
        user_id=sample_user["id"],
        enabled=False
    )

    enabled_servers = await servers.list_servers_by_user(sample_user["id"], enabled_only=True)
    assert all(s["enabled"] is True for s in enabled_servers)
    assert any(s["id"] == enabled_id for s in enabled_servers)
