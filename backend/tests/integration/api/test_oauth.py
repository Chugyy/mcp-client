"""Integration tests for OAuth endpoints.

Tests cover:
- OAuth 2.1 PKCE callback endpoint for MCP server authorization
- Success flow (code → token exchange → server verification)
- Error scenarios (invalid session, server not found, metadata failures)

Note: Complex OAuth flows (authorization initiation, token refresh) are deferred to Story 1.10.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_oauth_callback_missing_state_param(client):
    """Test GET /api/v1/oauth/callback without state parameter returns 422."""
    response = client.get("/api/v1/oauth/callback?code=test_code")

    assert response.status_code == 422


def test_oauth_callback_invalid_session(client):
    """Test GET /api/v1/oauth/callback with invalid/expired session returns 400."""
    with patch("app.core.services.mcp.oauth_manager.OAuthManager.get_session", new_callable=AsyncMock) as mock_get_session:
        mock_get_session.return_value = None  # Session not found

        response = client.get("/api/v1/oauth/callback?code=test_code&state=invalid_state")

    assert response.status_code == 400
    data = response.json()
    assert "OAuth session" in data["detail"]


def test_oauth_callback_server_not_found(client, authenticated_client, sample_server):
    """Test GET /api/v1/oauth/callback with nonexistent server_id returns 404."""
    with patch("app.core.services.mcp.oauth_manager.OAuthManager.get_session", new_callable=AsyncMock) as mock_get_session, \
         patch("app.database.crud.get_server", new_callable=AsyncMock) as mock_get_server:

        # Mock session with nonexistent server_id
        mock_get_session.return_value = {
            "server_id": "nonexistent_server",
            "code_verifier": "test_verifier",
            "redirect_uri": "http://localhost:3000/callback"
        }
        mock_get_server.return_value = None  # Server not found

        response = client.get("/api/v1/oauth/callback?code=test_code&state=valid_state")

    assert response.status_code == 404
    data = response.json()
    assert "Server not found" in data["detail"]


def test_oauth_callback_metadata_discovery_failure(client, authenticated_client, sample_server):
    """Test GET /api/v1/oauth/callback when OAuth metadata discovery fails returns 400."""
    with patch("app.core.services.mcp.oauth_manager.OAuthManager.get_session", new_callable=AsyncMock) as mock_get_session, \
         patch("app.database.crud.get_server", new_callable=AsyncMock) as mock_get_server, \
         patch("app.core.services.mcp.oauth_manager.OAuthManager.discover_metadata", new_callable=AsyncMock) as mock_discover, \
         patch("app.database.crud.update_server_status", new_callable=AsyncMock) as mock_update_status:

        mock_get_session.return_value = {
            "server_id": sample_server["id"],
            "code_verifier": "test_verifier",
            "redirect_uri": "http://localhost:3000/callback"
        }
        mock_get_server.return_value = sample_server
        mock_discover.return_value = {
            "success": False,
            "error": "Metadata endpoint unreachable"
        }

        response = client.get("/api/v1/oauth/callback?code=test_code&state=valid_state")

    assert response.status_code == 400
    data = response.json()
    assert "OAuth discovery failed" in data["detail"]
    # Verify server status was updated to failed
    mock_update_status.assert_called_once()


def test_oauth_callback_token_exchange_failure(client, authenticated_client, sample_server):
    """Test GET /api/v1/oauth/callback when token exchange fails returns 400."""
    with patch("app.core.services.mcp.oauth_manager.OAuthManager.get_session", new_callable=AsyncMock) as mock_get_session, \
         patch("app.database.crud.get_server", new_callable=AsyncMock) as mock_get_server, \
         patch("app.core.services.mcp.oauth_manager.OAuthManager.discover_metadata", new_callable=AsyncMock) as mock_discover, \
         patch("app.core.services.mcp.oauth_manager.OAuthManager.fetch_protected_resource", new_callable=AsyncMock) as mock_fetch_prm, \
         patch("app.core.services.mcp.oauth_manager.OAuthManager.fetch_authorization_server", new_callable=AsyncMock) as mock_fetch_asm, \
         patch("app.core.services.mcp.oauth_manager.OAuthManager.exchange_code", new_callable=AsyncMock) as mock_exchange, \
         patch("app.database.crud.update_server_status", new_callable=AsyncMock) as mock_update_status:

        mock_get_session.return_value = {
            "server_id": sample_server["id"],
            "code_verifier": "test_verifier",
            "redirect_uri": "http://localhost:3000/callback"
        }
        mock_get_server.return_value = sample_server
        mock_discover.return_value = {
            "success": True,
            "resource_metadata_url": "https://example.com/.well-known/resource-metadata"
        }
        mock_fetch_prm.return_value = {
            "success": True,
            "authorization_servers": ["https://example.com/oauth"]
        }
        mock_fetch_asm.return_value = {
            "success": True,
            "token_endpoint": "https://example.com/oauth/token"
        }
        mock_exchange.return_value = {
            "success": False,
            "error": "invalid_grant"
        }

        response = client.get("/api/v1/oauth/callback?code=invalid_code&state=valid_state")

    assert response.status_code == 400
    data = response.json()
    assert "Token exchange failed" in data["detail"]
    # Verify server status was updated to failed
    assert mock_update_status.call_count >= 1


@pytest.mark.skip(reason="Complex OAuth success flow - requires full mock infrastructure (deferred to Story 1.10)")
def test_oauth_callback_success(client, authenticated_client, sample_server):
    """Test GET /oauth/callback success flow (code → token → server verification).

    This test is deferred to Story 1.10 (OAuth MCP Integration Tests) because it requires:
    - Complete OAuth metadata discovery mock chain
    - Token storage mock
    - ServerManager.verify() mock
    - Session cleanup mock
    - Frontend redirect response validation
    """
    pass
