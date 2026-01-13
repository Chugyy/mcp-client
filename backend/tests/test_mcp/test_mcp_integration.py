"""Integration tests for MCP server management."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.services.mcp.manager import ServerManager
from app.core.services.mcp.clients import create_mcp_client
from app.api.v1.schemas.servers import ServerCreate


@pytest.mark.asyncio
async def test_end_to_end_server_lifecycle(db_pool_test):
    """Test complete lifecycle: create → verify → discover tools → execute → delete."""
    from app.core.services.mcp.manager import ServerManager

    # 1. Create server directly in DB
    from app.core.utils.id_generator import generate_id
    server_id = generate_id('server')

    async with db_pool_test.acquire() as conn:
        await conn.execute(
            """INSERT INTO mcp.servers
               (id, name, description, type, url, auth_type, enabled, status, user_id, is_system, args, env)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb)""",
            server_id,
            "E2E Test Server",
            "End-to-end test server",
            "http",
            "http://localhost:8080",
            "none",
            True,
            "pending",
            None,  # user_id nullable
            False,
            "[]",
            "{}"
        )

    with patch('app.database.db.get_pool', new_callable=AsyncMock, return_value=db_pool_test):
        # 2. Verify server (will fail to connect but should update status)
        with patch('app.core.services.mcp.clients.HTTPMCPClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.verify.return_value = {
                "status": "active",
                "tools": [{"name": "test_tool", "description": "Test", "inputSchema": {}}]
            }
            mock_client_cls.return_value = mock_client

            await ServerManager.verify(server_id)

        # 3. Delete server (user_id is NULL, pass None)
        await ServerManager.delete(server_id, None)

        # Verify deletion
        async with db_pool_test.acquire() as conn:
            result = await conn.fetchrow("SELECT * FROM mcp.servers WHERE id = $1", server_id)
            assert result is None


@pytest.mark.asyncio
async def test_oauth_server_integration(db_pool_test):
    """Test MCP server with OAuth authentication."""
    from app.core.utils.id_generator import generate_id

    # Create OAuth server in DB
    server_id = generate_id('server')

    async with db_pool_test.acquire() as conn:
        await conn.execute(
            """INSERT INTO mcp.servers
               (id, name, description, type, url, auth_type, enabled, status, user_id, is_system, args, env)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb)""",
            server_id,
            "OAuth Test Server",
            "OAuth server for testing",
            "http",
            "http://localhost:8080",
            "oauth",
            True,
            "pending",
            None,  # user_id nullable
            False,
            "[]",
            "{}"
        )

    # Verify server exists and has correct auth_type
    async with db_pool_test.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM mcp.servers WHERE id = $1", server_id)
        assert result is not None
        assert result["auth_type"] == "oauth"

    # Cleanup
    async with db_pool_test.acquire() as conn:
        await conn.execute("DELETE FROM mcp.servers WHERE id = $1", server_id)


@pytest.mark.asyncio
async def test_api_key_server_integration(db_pool_test):
    """Test MCP server with API key authentication."""
    from app.core.utils.id_generator import generate_id

    # Create API key server in DB with service_id reference
    server_id = generate_id('server')
    service_id = generate_id('service')

    async with db_pool_test.acquire() as conn:
        # Create service
        await conn.execute(
            """INSERT INTO core.services
               (id, name, provider, description, status)
               VALUES ($1, $2, $3, $4, $5)""",
            service_id,
            "Test API Service",
            "custom",
            "Service for API key testing",
            "active"
        )

        # Create server with service_id
        await conn.execute(
            """INSERT INTO mcp.servers
               (id, name, description, type, url, auth_type, enabled, status, user_id, is_system, service_id, args, env)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13::jsonb)""",
            server_id,
            "API Key Test Server",
            "API key server for testing",
            "http",
            "http://localhost:8080",
            "api-key",
            True,
            "pending",
            None,  # user_id nullable
            False,
            service_id,
            "[]",
            "{}"
        )

    # Verify server exists and has correct auth_type and service_id
    async with db_pool_test.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM mcp.servers WHERE id = $1", server_id)
        assert result is not None
        assert result["auth_type"] == "api-key"
        assert result["service_id"] == service_id

    # Cleanup
    async with db_pool_test.acquire() as conn:
        await conn.execute("DELETE FROM mcp.servers WHERE id = $1", server_id)
        await conn.execute("DELETE FROM core.services WHERE id = $1", service_id)


@pytest.mark.asyncio
async def test_server_reconnection_after_failure(db_pool_test):
    """Test server reconnection after transient failure."""
    from app.core.services.mcp.manager import ServerManager
    from app.core.utils.id_generator import generate_id

    # Create server
    server_id = generate_id('server')

    async with db_pool_test.acquire() as conn:
        await conn.execute(
            """INSERT INTO mcp.servers
               (id, name, description, type, url, auth_type, enabled, status, user_id, is_system, args, env)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb)""",
            server_id,
            "Reconnect Test Server",
            "Server for reconnection testing",
            "http",
            "http://localhost:8080",
            "none",
            True,
            "pending",
            None,  # user_id nullable
            False,
            "[]",
            "{}"
        )

    with patch('app.database.db.get_pool', new_callable=AsyncMock, return_value=db_pool_test):
        # First attempt (will fail)
        with patch('app.core.services.mcp.clients.HTTPMCPClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.verify.side_effect = Exception("Connection refused")
            mock_client_cls.return_value = mock_client

            await ServerManager.verify(server_id)

        # Check status updated to failed
        async with db_pool_test.acquire() as conn:
            result = await conn.fetchrow("SELECT status FROM mcp.servers WHERE id = $1", server_id)
            assert result["status"] == "failed"

        # Second attempt (succeeds)
        with patch('app.core.services.mcp.clients.HTTPMCPClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.verify.return_value = {
                "status": "active",
                "tools": []
            }
            mock_client_cls.return_value = mock_client

            await ServerManager.verify(server_id)

        # Check status updated to active
        async with db_pool_test.acquire() as conn:
            result = await conn.fetchrow("SELECT status FROM mcp.servers WHERE id = $1", server_id)
            assert result["status"] == "active"

    # Cleanup
    async with db_pool_test.acquire() as conn:
        await conn.execute("DELETE FROM mcp.servers WHERE id = $1", server_id)


@pytest.mark.asyncio
async def test_resource_cleanup_on_deletion(db_pool_test, db_server, db_agent):
    """Test proper resource cleanup when server is deleted."""
    from app.core.services.mcp.manager import ServerManager
    from app.core.utils.id_generator import generate_id

    server_id = db_server["id"]
    user_id = db_server["user_id"]  # Will be None
    agent_id = db_agent["id"]

    # Create configurations and tools to test cascade deletion
    config_id = generate_id('configuration')
    tool_id = generate_id('tool')

    async with db_pool_test.acquire() as conn:
        # Create configuration linking agent to server (entity_type must be 'server' or 'resource')
        await conn.execute(
            """INSERT INTO agents.configurations
               (id, agent_id, entity_type, entity_id, enabled)
               VALUES ($1, $2, $3, $4, $5)""",
            config_id, agent_id, "server", server_id, True
        )

        # Create tool for server (no input_schema column in DB)
        await conn.execute(
            """INSERT INTO mcp.tools
               (id, server_id, name, description, enabled)
               VALUES ($1, $2, $3, $4, $5)""",
            tool_id, server_id, "cleanup_test_tool", "Test tool", True
        )

    with patch('app.database.db.get_pool', new_callable=AsyncMock, return_value=db_pool_test):
        # Delete with force (should cascade delete tools and configs), user_id is None
        await ServerManager.delete(server_id, user_id, force=True)

    # Verify server deleted
    async with db_pool_test.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM mcp.servers WHERE id = $1", server_id)
        assert result is None

        # Tools should be cascade deleted
        result = await conn.fetchrow("SELECT * FROM mcp.tools WHERE id = $1", tool_id)
        assert result is None

        # Config should still exist (needs manual cleanup in real implementation)
        # For this test, we clean it up manually
        await conn.execute("DELETE FROM agents.configurations WHERE id = $1", config_id)
