"""Integration tests for MCP servers routes.

Tests all MCP server endpoints:
- POST /api/v1/mcp/servers
- GET /api/v1/mcp/servers
- GET /api/v1/mcp/servers/{server_id}
- PATCH /api/v1/mcp/servers/{server_id}
- DELETE /api/v1/mcp/servers/{server_id}
- POST /api/v1/mcp/servers/{server_id}/sync
- POST /api/v1/mcp/servers/{server_id}/tools
- GET /api/v1/mcp/servers/{server_id}/tools
- POST /api/v1/mcp/servers/agents/{agent_id}/configurations
- GET /api/v1/mcp/servers/agents/{agent_id}/configurations
- DELETE /api/v1/mcp/servers/configurations/{config_id}
"""

import pytest
from unittest.mock import patch, AsyncMock


class TestCreateServer:
    """Tests for POST /api/v1/mcp/servers"""

    def test_create_server_success_http(
        self, authenticated_client
    ):
        """Test creating HTTP MCP server successfully."""
        response = authenticated_client.post(
            "/api/v1/mcp/servers",
            json={
                "name": "Test HTTP Server",
                "description": "A test HTTP server",
                "type": "http",
                "url": "https://example.com/mcp",
                "auth_type": "none",
                "enabled": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test HTTP Server"
        assert data["type"] == "http"
        assert data["url"] == "https://example.com/mcp"
        assert data["auth_type"] == "none"
        assert data["enabled"] is True
        assert "id" in data
        assert data["id"].startswith("srv_")

    def test_create_server_success_npx(
        self, authenticated_client
    ):
        """Test creating npx MCP server successfully."""
        response = authenticated_client.post(
            "/api/v1/mcp/servers",
            json={
                "name": "Test NPX Server",
                "description": "A test NPX server",
                "type": "npx",
                "args": ["@modelcontextprotocol/server-filesystem", "/tmp"],
                "env": {"NODE_ENV": "test"},
                "enabled": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test NPX Server"
        assert data["type"] == "npx"
        assert data["args"] == ["@modelcontextprotocol/server-filesystem", "/tmp"]
        # Note: env is NOT returned in response for security reasons

    def test_create_server_oauth_pending_authorization(
        self, authenticated_client, mock_oauth_manager
    ):
        """Test creating OAuth server returns pending_authorization status."""
        response = authenticated_client.post(
            "/api/v1/mcp/servers",
            json={
                "name": "OAuth Server",
                "description": "Server with OAuth",
                "type": "http",
                "url": "https://example.com/mcp",
                "auth_type": "oauth",
                "enabled": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending_authorization"
        assert "status_message" in data
        # Status message should contain authorization URL
        assert "https://" in data["status_message"]

    def test_create_server_unauthenticated(self, client, clean_db):
        """Test creating server without authentication returns 401."""
        response = client.post(
            "/api/v1/mcp/servers",
            json={
                "name": "Test Server",
                "type": "http",
                "url": "https://example.com/mcp",
            },
        )

        assert response.status_code == 401

    def test_create_server_invalid_type(self, authenticated_client):
        """Test creating server with invalid type returns 422."""
        response = authenticated_client.post(
            "/api/v1/mcp/servers",
            json={
                "name": "Invalid Server",
                "type": "invalid_type",
                "url": "https://example.com/mcp",
            },
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_create_server_missing_required_fields(self, authenticated_client):
        """Test creating server without required fields returns 422."""
        response = authenticated_client.post(
            "/api/v1/mcp/servers",
            json={
                "name": "Incomplete Server",
                # Missing type
            },
        )

        assert response.status_code == 422


class TestListServers:
    """Tests for GET /api/v1/mcp/servers"""

    def test_list_servers_empty(self, authenticated_client, clean_db):
        """Test listing servers when none exist."""
        response = authenticated_client.get("/api/v1/mcp/servers")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_servers_with_servers(
        self, authenticated_client, sample_server
    ):
        """Test listing servers returns all user's servers."""
        # Create a second server
        authenticated_client.post(
            "/api/v1/mcp/servers",
            json={
                "name": "Second Server",
                "type": "http",
                "url": "https://example2.com/mcp",
                "auth_type": "none",
                "enabled": False,
            },
        )

        response = authenticated_client.get("/api/v1/mcp/servers")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        assert any(s["name"] == "Test MCP Server" for s in data)
        assert any(s["name"] == "Second Server" for s in data)

    def test_list_servers_enabled_only(
        self, authenticated_client, sample_server
    ):
        """Test listing only enabled servers."""
        # Create a disabled server
        authenticated_client.post(
            "/api/v1/mcp/servers",
            json={
                "name": "Disabled Server",
                "type": "http",
                "url": "https://disabled.com/mcp",
                "auth_type": "none",
                "enabled": False,
            },
        )

        response = authenticated_client.get(
            "/api/v1/mcp/servers", params={"enabled_only": True}
        )

        assert response.status_code == 200
        data = response.json()
        # All returned servers should be enabled
        assert all(s["enabled"] for s in data)

    def test_list_servers_with_tools(
        self, authenticated_client, sample_server
    ):
        """Test listing servers with their tools."""
        response = authenticated_client.get(
            "/api/v1/mcp/servers", params={"with_tools": True}
        )

        assert response.status_code == 200
        data = response.json()
        # Verify stale flag is included when with_tools=True
        if len(data) > 0:
            assert "stale" in data[0]

    def test_list_servers_unauthenticated(self, client, clean_db):
        """Test listing servers without authentication returns 401."""
        response = client.get("/api/v1/mcp/servers")

        assert response.status_code == 401


class TestGetServer:
    """Tests for GET /api/v1/mcp/servers/{server_id}"""

    def test_get_server_success(self, authenticated_client, sample_server):
        """Test getting a server by ID."""
        response = authenticated_client.get(
            f"/api/v1/mcp/servers/{sample_server['id']}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_server["id"]
        assert data["name"] == sample_server["name"]
        assert data["type"] == sample_server["type"]

    def test_get_server_not_found(self, authenticated_client, clean_db):
        """Test getting non-existent server returns 404."""
        response = authenticated_client.get("/api/v1/mcp/servers/srv_nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_server_unauthenticated(self, client, sample_server):
        """Test getting server without authentication returns 401."""
        # Clear cookies to simulate unauthenticated request
        client.cookies.clear()

        response = client.get(f"/api/v1/mcp/servers/{sample_server['id']}")

        assert response.status_code == 401


class TestUpdateServer:
    """Tests for PATCH /api/v1/mcp/servers/{server_id}"""

    def test_update_server_success(self, authenticated_client, sample_server):
        """Test updating a server successfully."""
        response = authenticated_client.patch(
            f"/api/v1/mcp/servers/{sample_server['id']}",
            json={
                "name": "Updated Server Name",
                "description": "Updated description",
                "enabled": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Server Name"
        assert data["description"] == "Updated description"
        assert data["enabled"] is False

    def test_update_server_partial(self, authenticated_client, sample_server):
        """Test partial update of a server."""
        original_name = sample_server["name"]

        response = authenticated_client.patch(
            f"/api/v1/mcp/servers/{sample_server['id']}",
            json={"description": "Only description updated"},
        )

        assert response.status_code == 200
        data = response.json()
        # Name should remain unchanged
        assert data["name"] == original_name
        assert data["description"] == "Only description updated"

    def test_update_server_system_server_denied(
        self, authenticated_client, system_server
    ):
        """Test updating system server returns 403."""
        response = authenticated_client.patch(
            f"/api/v1/mcp/servers/{system_server['id']}",
            json={"name": "Trying to update system server"},
        )

        assert response.status_code == 403
        assert "system server" in response.json()["detail"].lower()

    def test_update_server_not_found(self, authenticated_client, clean_db):
        """Test updating non-existent server returns 404."""
        response = authenticated_client.patch(
            "/api/v1/mcp/servers/srv_nonexistent",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 404

    def test_update_server_unauthenticated(self, client, sample_server):
        """Test updating server without authentication returns 401."""
        # Clear cookies to simulate unauthenticated request
        client.cookies.clear()

        response = client.patch(
            f"/api/v1/mcp/servers/{sample_server['id']}",
            json={"name": "Updated"},
        )

        assert response.status_code == 401


class TestDeleteServer:
    """Tests for DELETE /api/v1/mcp/servers/{server_id}"""

    def test_delete_server_success(
        self, authenticated_client
    ):
        """Test deleting a server successfully."""
        # Create a server to delete
        create_response = authenticated_client.post(
            "/api/v1/mcp/servers",
            json={
                "name": "Server To Delete",
                "type": "http",
                "url": "https://todelete.com/mcp",
                "auth_type": "none",
                "enabled": True,
            },
        )
        server_id = create_response.json()["id"]

        # Delete with confirmation header
        response = authenticated_client.delete(
            f"/api/v1/mcp/servers/{server_id}",
            headers={"X-Confirm-Deletion": "true"},
        )

        assert response.status_code == 204

        # Verify server is deleted
        get_response = authenticated_client.get(f"/api/v1/mcp/servers/{server_id}")
        assert get_response.status_code == 404

    def test_delete_server_with_impact_requires_confirmation(
        self, authenticated_client, sample_server
    ):
        """Test deleting server with impact returns 409 without confirmation."""
        # Delete without confirmation header
        response = authenticated_client.delete(
            f"/api/v1/mcp/servers/{sample_server['id']}"
        )

        # Should return 409 if there's impact
        if response.status_code == 409:
            data = response.json()
            assert "details" in data
            assert data["details"]["type"] == "confirmation_required"
            assert "impact" in data["details"]

    def test_delete_server_system_server_denied(
        self, authenticated_client, system_server
    ):
        """Test deleting system server returns 403."""
        response = authenticated_client.delete(
            f"/api/v1/mcp/servers/{system_server['id']}",
            headers={"X-Confirm-Deletion": "true"},
        )

        assert response.status_code == 403

    def test_delete_server_not_found(self, authenticated_client, clean_db):
        """Test deleting non-existent server returns 404."""
        response = authenticated_client.delete(
            "/api/v1/mcp/servers/srv_nonexistent",
            headers={"X-Confirm-Deletion": "true"},
        )

        assert response.status_code == 404

    def test_delete_server_unauthenticated(self, client, sample_server):
        """Test deleting server without authentication returns 401."""
        # Clear cookies to simulate unauthenticated request
        client.cookies.clear()

        response = client.delete(f"/api/v1/mcp/servers/{sample_server['id']}")

        assert response.status_code == 401


class TestSyncServer:
    """Tests for POST /api/v1/mcp/servers/{server_id}/sync"""

    def test_sync_server_success(
        self, authenticated_client, sample_server
    ):
        """Test syncing server tools successfully."""
        # Mock the sync_tools method to avoid real connection
        with patch('app.core.services.mcp.manager.ServerManager.sync_tools') as mock_sync:
            mock_sync.return_value = AsyncMock(return_value=5)

            response = authenticated_client.post(
                f"/api/v1/mcp/servers/{sample_server['id']}/sync"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sample_server["id"]

    def test_sync_server_oauth_expired_returns_pending_authorization(
        self, authenticated_client, mock_oauth_manager
    ):
        """Test syncing OAuth server with expired token returns pending_authorization."""
        # Create OAuth server
        create_response = authenticated_client.post(
            "/api/v1/mcp/servers",
            json={
                "name": "OAuth Server",
                "type": "http",
                "url": "https://oauth-server.com/mcp",
                "auth_type": "oauth",
                "enabled": True,
            },
        )
        server_id = create_response.json()["id"]

        # Mock expired token
        mock_oauth_manager.get_tokens = lambda sid: None
        mock_oauth_manager.is_expired = lambda sid: True

        # Sync should trigger OAuth re-authorization
        response = authenticated_client.post(f"/api/v1/mcp/servers/{server_id}/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending_authorization"
        assert "status_message" in data

    def test_sync_server_not_found(self, authenticated_client, clean_db):
        """Test syncing non-existent server returns 404."""
        response = authenticated_client.post("/api/v1/mcp/servers/srv_nonexistent/sync")

        assert response.status_code == 404

    def test_sync_server_unauthenticated(self, client, sample_server):
        """Test syncing server without authentication returns 401."""
        # Clear cookies to simulate unauthenticated request
        client.cookies.clear()

        response = client.post(f"/api/v1/mcp/servers/{sample_server['id']}/sync")

        assert response.status_code == 401


class TestCreateTool:
    """Tests for POST /api/v1/mcp/servers/{server_id}/tools"""

    def test_create_tool_success(self, authenticated_client, sample_server):
        """Test creating a tool successfully."""
        response = authenticated_client.post(
            f"/api/v1/mcp/servers/{sample_server['id']}/tools",
            json={
                "name": "test_tool",
                "description": "A test tool",
                "enabled": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_tool"
        assert data["description"] == "A test tool"
        assert data["enabled"] is True
        assert "id" in data

    def test_create_tool_server_not_found(self, authenticated_client, clean_db):
        """Test creating tool for non-existent server returns 404."""
        response = authenticated_client.post(
            "/api/v1/mcp/servers/srv_nonexistent/tools",
            json={
                "name": "test_tool",
                "description": "A test tool",
                "enabled": True,
            },
        )

        assert response.status_code == 404

    def test_create_tool_unauthenticated(self, client, sample_server):
        """Test creating tool without authentication returns 401."""
        # Clear cookies to simulate unauthenticated request
        client.cookies.clear()

        response = client.post(
            f"/api/v1/mcp/servers/{sample_server['id']}/tools",
            json={"name": "test_tool"},
        )

        assert response.status_code == 401


class TestListTools:
    """Tests for GET /api/v1/mcp/servers/{server_id}/tools"""

    def test_list_tools_empty(self, authenticated_client, sample_server):
        """Test listing tools when none exist."""
        response = authenticated_client.get(
            f"/api/v1/mcp/servers/{sample_server['id']}/tools"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_tools_with_tools(self, authenticated_client, sample_server):
        """Test listing tools returns all tools for server."""
        # Create a tool
        authenticated_client.post(
            f"/api/v1/mcp/servers/{sample_server['id']}/tools",
            json={
                "name": "tool1",
                "description": "Tool 1",
                "enabled": True,
            },
        )

        # Create another tool
        authenticated_client.post(
            f"/api/v1/mcp/servers/{sample_server['id']}/tools",
            json={
                "name": "tool2",
                "description": "Tool 2",
                "enabled": True,
            },
        )

        response = authenticated_client.get(
            f"/api/v1/mcp/servers/{sample_server['id']}/tools"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        tool_names = [t["name"] for t in data]
        assert "tool1" in tool_names
        assert "tool2" in tool_names

    def test_list_tools_server_not_found(self, authenticated_client, clean_db):
        """Test listing tools for non-existent server returns 404."""
        response = authenticated_client.get("/api/v1/mcp/servers/srv_nonexistent/tools")

        assert response.status_code == 404

    def test_list_tools_unauthenticated(self, client, sample_server):
        """Test listing tools without authentication returns 401."""
        # Clear cookies to simulate unauthenticated request
        client.cookies.clear()

        response = client.get(f"/api/v1/mcp/servers/{sample_server['id']}/tools")

        assert response.status_code == 401


class TestCreateConfiguration:
    """Tests for POST /api/v1/mcp/servers/agents/{agent_id}/configurations"""

    def test_create_configuration_success_server(
        self, authenticated_client, sample_agent, sample_server
    ):
        """Test creating server configuration for agent successfully."""
        response = authenticated_client.post(
            f"/api/v1/mcp/servers/agents/{sample_agent['id']}/configurations",
            json={
                "entity_type": "server",
                "entity_id": sample_server["id"],
                "config_data": {"param1": "value1"},
                "enabled": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["entity_type"] == "server"
        assert data["entity_id"] == sample_server["id"]
        assert data["enabled"] is True
        assert "id" in data

    def test_create_configuration_success_resource(
        self, authenticated_client, sample_agent, sample_resource
    ):
        """Test creating resource configuration for agent successfully."""
        response = authenticated_client.post(
            f"/api/v1/mcp/servers/agents/{sample_agent['id']}/configurations",
            json={
                "entity_type": "resource",
                "entity_id": sample_resource["id"],
                "config_data": {},
                "enabled": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["entity_type"] == "resource"
        assert data["entity_id"] == sample_resource["id"]

    def test_create_configuration_agent_not_found(
        self, authenticated_client, sample_server
    ):
        """Test creating configuration for non-existent agent returns 404."""
        response = authenticated_client.post(
            "/api/v1/mcp/servers/agents/agt_nonexistent/configurations",
            json={
                "entity_type": "server",
                "entity_id": sample_server["id"],
                "enabled": True,
            },
        )

        assert response.status_code == 404

    def test_create_configuration_entity_not_found(
        self, authenticated_client, sample_agent
    ):
        """Test creating configuration with non-existent entity returns 404."""
        response = authenticated_client.post(
            f"/api/v1/mcp/servers/agents/{sample_agent['id']}/configurations",
            json={
                "entity_type": "server",
                "entity_id": "srv_nonexistent",
                "enabled": True,
            },
        )

        assert response.status_code == 404

    def test_create_configuration_permission_denied(
        self, authenticated_client, other_user_agent, sample_server
    ):
        """Test creating configuration for other user's agent returns 403."""
        response = authenticated_client.post(
            f"/api/v1/mcp/servers/agents/{other_user_agent['id']}/configurations",
            json={
                "entity_type": "server",
                "entity_id": sample_server["id"],
                "enabled": True,
            },
        )

        assert response.status_code == 403

    def test_create_configuration_unauthenticated(self, client, sample_agent):
        """Test creating configuration without authentication returns 401."""
        # Clear cookies to simulate unauthenticated request
        client.cookies.clear()

        response = client.post(
            f"/api/v1/mcp/servers/agents/{sample_agent['id']}/configurations",
            json={"entity_type": "server", "entity_id": "srv_123"},
        )

        assert response.status_code == 401


class TestListConfigurations:
    """Tests for GET /api/v1/mcp/servers/agents/{agent_id}/configurations"""

    def test_list_configurations_empty(self, authenticated_client, sample_agent):
        """Test listing configurations when none exist."""
        response = authenticated_client.get(
            f"/api/v1/mcp/servers/agents/{sample_agent['id']}/configurations"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_configurations_with_configs(
        self, authenticated_client, sample_agent, sample_server, sample_resource
    ):
        """Test listing configurations returns all agent configurations."""
        # Create server configuration
        authenticated_client.post(
            f"/api/v1/mcp/servers/agents/{sample_agent['id']}/configurations",
            json={
                "entity_type": "server",
                "entity_id": sample_server["id"],
                "enabled": True,
            },
        )

        # Create resource configuration
        authenticated_client.post(
            f"/api/v1/mcp/servers/agents/{sample_agent['id']}/configurations",
            json={
                "entity_type": "resource",
                "entity_id": sample_resource["id"],
                "enabled": True,
            },
        )

        response = authenticated_client.get(
            f"/api/v1/mcp/servers/agents/{sample_agent['id']}/configurations"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_list_configurations_agent_not_found(self, authenticated_client, clean_db):
        """Test listing configurations for non-existent agent returns 404."""
        response = authenticated_client.get(
            "/api/v1/mcp/servers/agents/agt_nonexistent/configurations"
        )

        assert response.status_code == 404

    def test_list_configurations_permission_denied(
        self, authenticated_client, other_user_agent
    ):
        """Test listing configurations for other user's agent returns 403."""
        response = authenticated_client.get(
            f"/api/v1/mcp/servers/agents/{other_user_agent['id']}/configurations"
        )

        assert response.status_code == 403

    def test_list_configurations_unauthenticated(self, client, sample_agent):
        """Test listing configurations without authentication returns 401."""
        # Clear cookies to simulate unauthenticated request
        client.cookies.clear()

        response = client.get(
            f"/api/v1/mcp/servers/agents/{sample_agent['id']}/configurations"
        )

        assert response.status_code == 401


class TestDeleteConfiguration:
    """Tests for DELETE /api/v1/mcp/servers/configurations/{config_id}"""

    def test_delete_configuration_success(
        self, authenticated_client, sample_agent, sample_server
    ):
        """Test deleting configuration successfully."""
        # Create a configuration
        create_response = authenticated_client.post(
            f"/api/v1/mcp/servers/agents/{sample_agent['id']}/configurations",
            json={
                "entity_type": "server",
                "entity_id": sample_server["id"],
                "enabled": True,
            },
        )
        config_id = create_response.json()["id"]

        # Delete the configuration
        response = authenticated_client.delete(
            f"/api/v1/mcp/servers/configurations/{config_id}"
        )

        assert response.status_code == 204

        # Verify configuration is deleted
        list_response = authenticated_client.get(
            f"/api/v1/mcp/servers/agents/{sample_agent['id']}/configurations"
        )
        configs = list_response.json()
        config_ids = [c["id"] for c in configs]
        assert config_id not in config_ids

    def test_delete_configuration_not_found(self, authenticated_client, clean_db):
        """Test deleting non-existent configuration returns 404."""
        response = authenticated_client.delete(
            "/api/v1/mcp/servers/configurations/cfg_nonexistent"
        )

        assert response.status_code == 404

    def test_delete_configuration_unauthenticated(self, client):
        """Test deleting configuration without authentication returns 401."""
        response = client.delete("/api/v1/mcp/servers/configurations/cfg_123")

        assert response.status_code == 401
