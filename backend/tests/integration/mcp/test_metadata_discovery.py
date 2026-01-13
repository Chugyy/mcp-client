"""
Integration tests for OAuth metadata discovery.

Tests OAuth metadata discovery from .well-known endpoints including:
- Protected resource metadata discovery
- Authorization server metadata discovery
- Metadata parsing and validation
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.services.mcp.oauth_manager import OAuthManager


@pytest.mark.asyncio
class TestProtectedResourceMetadata:
    """Test discovery of OAuth protected resource metadata."""

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_fetch_protected_resource_success(self, mock_client_class):
        """Test successful protected resource metadata fetch."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resource": "https://mcp.example.com",
            "authorization_servers": ["https://oauth.example.com"],
            "scopes_supported": ["read", "write", "admin"]
        }
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        metadata_url = "https://mcp.example.com/.well-known/oauth-protected-resource"
        metadata = await OAuthManager.fetch_protected_resource(metadata_url)

        # Verify metadata parsed correctly
        assert metadata["success"] == True
        assert metadata["resource"] == "https://mcp.example.com"
        assert metadata["authorization_servers"] == ["https://oauth.example.com"]
        assert "read" in metadata["scopes_supported"]
        assert "write" in metadata["scopes_supported"]

        # Verify correct URL was called
        mock_client.get.assert_called_once_with(metadata_url)

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_fetch_protected_resource_missing_required_fields(self, mock_client_class):
        """Test handling of incomplete protected resource metadata."""
        # Setup mock with missing fields
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resource": "https://mcp.example.com"
            # Missing authorization_servers
        }
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        metadata = await OAuthManager.fetch_protected_resource(
            "https://mcp.example.com/.well-known/oauth-protected-resource"
        )

        # Verify error handling
        assert metadata["success"] == False
        assert "Missing required fields" in metadata["error"]

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_fetch_protected_resource_http_error(self, mock_client_class):
        """Test handling of HTTP errors during metadata fetch."""
        # Setup mock for 404 response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        metadata = await OAuthManager.fetch_protected_resource(
            "https://mcp.example.com/.well-known/oauth-protected-resource"
        )

        # Verify error response
        assert metadata["success"] == False
        assert "HTTP 404" in metadata["error"]

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_fetch_protected_resource_network_error(self, mock_client_class):
        """Test handling of network errors."""
        # Setup mock to raise exception
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        metadata = await OAuthManager.fetch_protected_resource(
            "https://mcp.example.com/.well-known/oauth-protected-resource"
        )

        # Verify error handling
        assert metadata["success"] == False
        assert "Connection refused" in metadata["error"]


@pytest.mark.asyncio
class TestAuthorizationServerMetadata:
    """Test discovery of OAuth authorization server metadata."""

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_fetch_authorization_server_success(self, mock_client_class):
        """Test successful authorization server metadata fetch."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issuer": "https://oauth.example.com",
            "authorization_endpoint": "https://oauth.example.com/authorize",
            "token_endpoint": "https://oauth.example.com/token",
            "jwks_uri": "https://oauth.example.com/.well-known/jwks.json",
            "scopes_supported": ["read", "write", "admin"]
        }
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        metadata = await OAuthManager.fetch_authorization_server("https://oauth.example.com")

        # Verify metadata parsed correctly
        assert metadata["success"] == True
        assert metadata["authorization_endpoint"] == "https://oauth.example.com/authorize"
        assert metadata["token_endpoint"] == "https://oauth.example.com/token"
        assert metadata["jwks_uri"] == "https://oauth.example.com/.well-known/jwks.json"
        assert "read" in metadata["scopes_supported"]

        # Verify well-known URL was constructed correctly
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args[0]
        assert ".well-known/oauth-authorization-server" in call_args[0]

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_fetch_authorization_server_constructs_well_known_url(self, mock_client_class):
        """Test that authorization server URL is constructed from base URL."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issuer": "https://oauth.example.com",
            "authorization_endpoint": "https://oauth.example.com/authorize",
            "token_endpoint": "https://oauth.example.com/token",
            "jwks_uri": "https://oauth.example.com/.well-known/jwks.json"
        }
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        base_url = "https://oauth.example.com"
        await OAuthManager.fetch_authorization_server(base_url)

        # Verify .well-known URL construction
        expected_url = f"{base_url}/.well-known/oauth-authorization-server"
        mock_client.get.assert_called_once_with(expected_url)

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_fetch_authorization_server_handles_trailing_slash(self, mock_client_class):
        """Test that trailing slash in base URL is handled correctly."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "authorization_endpoint": "https://oauth.example.com/authorize",
            "token_endpoint": "https://oauth.example.com/token"
        }
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        # Base URL with trailing slash
        base_url_with_slash = "https://oauth.example.com/"
        await OAuthManager.fetch_authorization_server(base_url_with_slash)

        # Verify URL doesn't have double slashes
        call_url = mock_client.get.call_args[0][0]
        assert "//.well-known" not in call_url
        assert "/.well-known/oauth-authorization-server" in call_url

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_fetch_authorization_server_http_error(self, mock_client_class):
        """Test handling of HTTP errors."""
        # Setup mock for 500 error
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        metadata = await OAuthManager.fetch_authorization_server("https://oauth.example.com")

        # Verify error response
        assert metadata["success"] == False
        assert "HTTP 500" in metadata["error"]


@pytest.mark.asyncio
class TestMetadataDiscoveryFlow:
    """Test complete metadata discovery flow."""

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_discover_metadata_triggers_401_for_metadata_url(self, mock_client_class):
        """Test that discover_metadata triggers 401 to get WWW-Authenticate header."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.headers.get.return_value = 'Bearer resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"'
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        server_url = "https://mcp.example.com"
        result = await OAuthManager.discover_metadata(server_url)

        # Verify 401 was triggered on /mcp/ endpoint
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/mcp/" in call_args[0][0]

        # Verify WWW-Authenticate header was parsed
        assert result["success"] == True
        assert result["resource_metadata_url"] == "https://mcp.example.com/.well-known/oauth-protected-resource"

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_discover_metadata_uses_default_well_known_if_no_header(self, mock_client_class):
        """Test fallback to default .well-known URL when WWW-Authenticate doesn't have resource_metadata."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.headers.get.return_value = 'Bearer realm="oauth"'  # No resource_metadata
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        server_url = "https://mcp.example.com"
        result = await OAuthManager.discover_metadata(server_url)

        # Verify fallback to default .well-known URL
        assert result["success"] == True
        assert result["resource_metadata_url"] == "https://mcp.example.com/.well-known/oauth-protected-resource"

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_discover_metadata_fails_on_non_401_response(self, mock_client_class):
        """Test that discovery fails if server doesn't return 401."""
        # Setup mock for 200 response (should be 401)
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        server_url = "https://mcp.example.com"
        result = await OAuthManager.discover_metadata(server_url)

        # Verify error
        assert result["success"] == False
        assert "Expected 401, got 200" in result["error"]

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_discover_metadata_network_error(self, mock_client_class):
        """Test handling of network errors during discovery."""
        # Setup mock to raise exception
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("DNS resolution failed")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        server_url = "https://mcp.example.com"
        result = await OAuthManager.discover_metadata(server_url)

        # Verify error handling
        assert result["success"] == False
        assert "DNS resolution failed" in result["error"]


@pytest.mark.asyncio
class TestMetadataValidation:
    """Test metadata validation and parsing."""

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_metadata_contains_required_oauth_endpoints(self, mock_client_class):
        """Test that metadata includes required OAuth endpoints."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issuer": "https://oauth.example.com",
            "authorization_endpoint": "https://oauth.example.com/authorize",
            "token_endpoint": "https://oauth.example.com/token",
            "jwks_uri": "https://oauth.example.com/.well-known/jwks.json"
        }
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        metadata = await OAuthManager.fetch_authorization_server("https://oauth.example.com")

        # Verify required endpoints are present
        assert metadata["success"] == True
        assert "authorization_endpoint" in metadata
        assert "token_endpoint" in metadata
        assert metadata["authorization_endpoint"].startswith("https://")
        assert metadata["token_endpoint"].startswith("https://")

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_metadata_scopes_supported_is_parsed(self, mock_client_class):
        """Test that supported scopes are parsed correctly."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "authorization_endpoint": "https://oauth.example.com/authorize",
            "token_endpoint": "https://oauth.example.com/token",
            "scopes_supported": ["openid", "profile", "email", "read", "write"]
        }
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        metadata = await OAuthManager.fetch_authorization_server("https://oauth.example.com")

        # Verify scopes are parsed
        assert metadata["success"] == True
        assert "scopes_supported" in metadata
        assert isinstance(metadata["scopes_supported"], list)
        assert "read" in metadata["scopes_supported"]
        assert "write" in metadata["scopes_supported"]

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_metadata_handles_missing_optional_fields(self, mock_client_class):
        """Test that missing optional fields are handled gracefully."""
        # Setup mock with minimal metadata
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "authorization_endpoint": "https://oauth.example.com/authorize",
            "token_endpoint": "https://oauth.example.com/token"
            # No scopes_supported, jwks_uri, etc.
        }
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        metadata = await OAuthManager.fetch_authorization_server("https://oauth.example.com")

        # Verify optional fields have defaults
        assert metadata["success"] == True
        assert metadata["scopes_supported"] == []  # Default empty list
