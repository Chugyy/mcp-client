"""Tests for MCP Server Manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.services.mcp.manager import ServerManager
from app.api.v1.schemas.servers import ServerCreate
from app.core.exceptions import ValidationError, ConflictError, NotFoundError, PermissionError


@pytest.mark.asyncio
async def test_server_creation_http(mock_validators, mock_create_server):
    """Test creating HTTP MCP server."""
    dto = ServerCreate(
        name="Test HTTP Server",
        description="Test server",
        type="http",
        url="http://localhost:8080",
        auth_type="none",
        enabled=True
    )

    server_id = await ServerManager.create(dto, user_id="user-123")
    assert server_id == "test-server-id"


@pytest.mark.asyncio
async def test_server_creation_stdio(mock_validators):
    """Test creating stdio MCP server."""
    dto = ServerCreate(
        name="Test Stdio Server",
        description="Test stdio server",
        type="npx",
        args=["@modelcontextprotocol/server-example"],
        env={"TEST": "true"},
        enabled=True
    )

    with patch('app.database.crud.create_server', new_callable=AsyncMock, return_value="stdio-server-id"):
        server_id = await ServerManager.create(dto, user_id="user-123")
        assert server_id == "stdio-server-id"


@pytest.mark.asyncio
async def test_server_verification_success():
    """Test successful server verification."""
    with patch('app.core.services.mcp.manager.create_mcp_client', new_callable=AsyncMock) as mock_client_factory, \
         patch('app.database.crud.update_server_status', new_callable=AsyncMock) as mock_update_status, \
         patch('app.database.crud.delete_server_tools', new_callable=AsyncMock), \
         patch('app.database.crud.create_tool', new_callable=AsyncMock) as mock_create_tool:

        # Mock client with successful verify
        mock_client = AsyncMock()
        mock_client.verify.return_value = {
            "status": "active",
            "status_message": "Server active with 2 tools",
            "tools": [
                {"name": "test_tool", "description": "Test tool", "inputSchema": {}},
                {"name": "echo_tool", "description": "Echo tool", "inputSchema": {}}
            ]
        }
        mock_client_factory.return_value = mock_client

        await ServerManager.verify("test-server-id", timeout=30)

        # Verify calls
        mock_client.verify.assert_called_once()
        assert mock_create_tool.call_count == 2  # 2 tools created


@pytest.mark.asyncio
async def test_server_verification_timeout():
    """Test server verification timeout handling."""
    import asyncio

    with patch('app.core.services.mcp.manager.create_mcp_client', new_callable=AsyncMock) as mock_client_factory, \
         patch('app.database.crud.update_server_status', new_callable=AsyncMock) as mock_update_status:

        # Mock client that times out
        mock_client = AsyncMock()
        async def slow_verify():
            await asyncio.sleep(2)  # Longer than timeout
            return {"status": "active"}

        mock_client.verify.side_effect = slow_verify
        mock_client_factory.return_value = mock_client

        # Verify with very short timeout
        await ServerManager.verify("test-server-id", timeout=1)

        # Should have updated status to failed with timeout message
        assert mock_update_status.called
        call_args = mock_update_status.call_args[1]
        assert call_args['status'] == 'failed'
        assert 'timeout' in call_args['status_message'].lower()


@pytest.mark.asyncio
async def test_server_verification_error():
    """Test server verification error handling."""
    with patch('app.core.services.mcp.manager.create_mcp_client', new_callable=AsyncMock) as mock_client_factory, \
         patch('app.database.crud.update_server_status', new_callable=AsyncMock) as mock_update_status:

        # Mock client that raises error
        mock_client = AsyncMock()
        mock_client.verify.side_effect = Exception("Connection refused")
        mock_client_factory.return_value = mock_client

        await ServerManager.verify("test-server-id", timeout=30)

        # Should have updated status to failed
        mock_update_status.assert_called()


@pytest.mark.asyncio
async def test_server_deletion_success(db_pool_test, db_server):
    """Test successful server deletion with real DB."""
    from app.core.services.mcp.manager import ServerManager

    # db_server is a real Server row in test DB
    server_id = db_server["id"]
    user_id = db_server["user_id"]  # Will be None since db_server fixture uses NULL

    # Use real DB pool for get_pool
    with patch('app.database.db.get_pool', new_callable=AsyncMock, return_value=db_pool_test):
        # Delete
        await ServerManager.delete(server_id, user_id, force=False)

        # Verify deletion - server should no longer exist
        async with db_pool_test.acquire() as conn:
            result = await conn.fetchrow("SELECT * FROM mcp.servers WHERE id = $1", server_id)
            assert result is None


@pytest.mark.asyncio
async def test_server_deletion_with_impact_requires_force(db_pool_test, db_server, db_agent):
    """Test server deletion with impact requires force flag."""
    from app.core.services.mcp.manager import ServerManager

    server_id = db_server["id"]
    user_id = db_server["user_id"]
    agent_id = db_agent["id"]

    # Create a configuration linking agent to server to create impact
    async with db_pool_test.acquire() as conn:
        from app.core.utils.id_generator import generate_id
        config_id = generate_id('configuration')
        await conn.execute(
            """INSERT INTO agents.configurations
               (id, agent_id, entity_type, entity_id, enabled)
               VALUES ($1, $2, $3, $4, $5)""",
            config_id, agent_id, "server", server_id, True
        )

    with patch('app.database.db.get_pool', new_callable=AsyncMock, return_value=db_pool_test):
        # Should raise error without force
        with pytest.raises(RuntimeError, match="impact"):
            await ServerManager.delete(server_id, user_id, force=False)

        # Cleanup: delete config
        async with db_pool_test.acquire() as conn:
            await conn.execute("DELETE FROM agents.configurations WHERE id = $1", config_id)


@pytest.mark.asyncio
async def test_server_deletion_system_server_protected(db_pool_test):
    """Test system server deletion is prevented."""
    from app.core.services.mcp.manager import ServerManager
    from app.core.utils.id_generator import generate_id

    # Create a system server (user_id is NULL, is_system=True marks it as system server)
    server_id = generate_id('server')

    async with db_pool_test.acquire() as conn:
        await conn.execute(
            """INSERT INTO mcp.servers
               (id, name, description, type, url, auth_type, enabled, status, user_id, is_system, args, env)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb)""",
            server_id,
            "System Server",
            "System server for testing",
            "http",
            "http://localhost:8080",
            "none",
            True,
            "active",
            None,  # user_id is nullable
            True,  # is_system = True marks it as system server
            "[]",
            "{}"
        )

    # Should raise permission error when trying to delete a system server
    with pytest.raises(PermissionError, match="system server"):
        await ServerManager.delete(server_id, None, force=True)

    # Cleanup
    async with db_pool_test.acquire() as conn:
        await conn.execute("DELETE FROM mcp.servers WHERE id = $1", server_id)


@pytest.mark.asyncio
async def test_check_prerequisites():
    """Test checking system prerequisites (npx, uvx, docker)."""
    with patch('shutil.which') as mock_which:
        # Mock all tools available
        mock_which.side_effect = lambda x: f"/usr/bin/{x}" if x in ["npx", "uvx", "docker"] else None

        result = await ServerManager.check_prerequisites()

        assert result["npx"] is True
        assert result["uvx"] is True
        assert result["docker"] is True

        # Mock only npx available
        mock_which.side_effect = lambda x: f"/usr/bin/{x}" if x == "npx" else None

        result = await ServerManager.check_prerequisites()

        assert result["npx"] is True
        assert result["uvx"] is False
        assert result["docker"] is False
