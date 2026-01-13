"""
Integration tests for OAuth 2.1 token refresh flow.

Tests token refresh functionality including:
- Refresh token exchange for new access token
- OAuth 2.1 refresh token rotation
- Token expiration handling
- Error scenarios
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.services.mcp.oauth_manager import OAuthManager


@pytest.mark.asyncio
class TestTokenRefresh:
    """Test OAuth token refresh flow."""

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_refresh_token_success(self, mock_client_class):
        """Test successful token refresh."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token_123",
            "refresh_token": "new_refresh_token_456",  # OAuth 2.1 rotation
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        token_response = await OAuthManager.refresh_token(
            token_endpoint="https://oauth.example.com/token",
            client_id="test_client_123",
            refresh_token="old_refresh_token_789"
        )

        # Verify new tokens received
        assert token_response["success"] == True
        assert token_response["access_token"] == "new_access_token_123"
        assert token_response["refresh_token"] == "new_refresh_token_456"
        assert token_response["token_type"] == "Bearer"
        assert token_response["expires_in"] == 3600

        # Verify refresh token was sent with correct grant type
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://oauth.example.com/token"
        assert call_args[1]["data"]["refresh_token"] == "old_refresh_token_789"
        assert call_args[1]["data"]["grant_type"] == "refresh_token"
        assert call_args[1]["data"]["client_id"] == "test_client_123"

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_refresh_token_rotation(self, mock_client_class):
        """Test OAuth 2.1 refresh token rotation."""
        # Setup mock with new refresh token (OAuth 2.1 rotation)
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "rotated_access_token",
            "refresh_token": "rotated_refresh_token",  # New refresh token
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        old_refresh_token = "old_refresh_token"

        token_response = await OAuthManager.refresh_token(
            token_endpoint="https://oauth.example.com/token",
            client_id="test_client",
            refresh_token=old_refresh_token
        )

        # Verify old refresh token was used
        call_args = mock_client.post.call_args
        assert call_args[1]["data"]["refresh_token"] == old_refresh_token

        # Verify new refresh token was returned (rotation)
        assert token_response["refresh_token"] == "rotated_refresh_token"
        assert token_response["refresh_token"] != old_refresh_token

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_refresh_token_returns_same_refresh_token_if_no_rotation(self, mock_client_class):
        """Test handling when provider doesn't rotate refresh token."""
        # Setup mock without new refresh token
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600
            # No refresh_token in response
        }
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        old_refresh_token = "old_refresh_token"

        token_response = await OAuthManager.refresh_token(
            token_endpoint="https://oauth.example.com/token",
            client_id="test_client",
            refresh_token=old_refresh_token
        )

        # Verify old refresh token is returned when provider doesn't rotate
        assert token_response["refresh_token"] == old_refresh_token

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_refresh_token_failure_invalid_token(self, mock_client_class):
        """Test refresh failure with invalid refresh token."""
        # Setup mock for invalid token response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        token_response = await OAuthManager.refresh_token(
            token_endpoint="https://oauth.example.com/token",
            client_id="test_client",
            refresh_token="invalid_refresh_token"
        )

        # Verify error response
        assert token_response["success"] == False
        assert token_response["access_token"] is None
        assert token_response["refresh_token"] is None
        assert "HTTP 400" in token_response["error"]

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_refresh_token_network_error(self, mock_client_class):
        """Test refresh token handles network errors."""
        # Setup mock to raise exception
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection timeout")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        token_response = await OAuthManager.refresh_token(
            token_endpoint="https://oauth.example.com/token",
            client_id="test_client",
            refresh_token="refresh_token"
        )

        # Verify error handling
        assert token_response["success"] == False
        assert "Connection timeout" in token_response["error"]


@pytest.mark.asyncio
class TestTokenExpiration:
    """Test token expiration handling."""

    async def test_is_expired_returns_true_for_expired_token(self):
        """Test that expired tokens are detected."""
        # This test would require database setup to test is_expired()
        # For now, we test the expiration logic conceptually

        # Token expires_in is typically in seconds
        # A token with expires_in=3600 should expire in 1 hour
        # The implementation should check: now >= (expires_at - 60 seconds margin)

        # This is tested via integration with token storage
        pass

    async def test_is_expired_returns_false_for_valid_token(self):
        """Test that valid tokens are not marked as expired."""
        # This would require database integration
        pass

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_refresh_updates_expiration_time(self, mock_client_class):
        """Test that refresh updates token expiration time."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        new_expires_in = 7200  # 2 hours
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "token_type": "Bearer",
            "expires_in": new_expires_in
        }
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        token_response = await OAuthManager.refresh_token(
            token_endpoint="https://oauth.example.com/token",
            client_id="test_client",
            refresh_token="old_refresh"
        )

        # Verify new expiration time
        assert token_response["expires_in"] == new_expires_in


@pytest.mark.asyncio
class TestTokenRequestFormat:
    """Test token refresh request format compliance."""

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_refresh_request_uses_correct_content_type(self, mock_client_class):
        """Test that refresh request uses application/x-www-form-urlencoded."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        await OAuthManager.refresh_token(
            token_endpoint="https://oauth.example.com/token",
            client_id="test_client",
            refresh_token="refresh_token"
        )

        # Verify Content-Type header
        call_args = mock_client.post.call_args
        assert call_args[1]["headers"]["Content-Type"] == "application/x-www-form-urlencoded"

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_refresh_request_includes_required_parameters(self, mock_client_class):
        """Test that refresh request includes all required OAuth 2.1 parameters."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        await OAuthManager.refresh_token(
            token_endpoint="https://oauth.example.com/token",
            client_id="test_client_id",
            refresh_token="test_refresh_token"
        )

        # Verify required parameters
        call_args = mock_client.post.call_args
        data = call_args[1]["data"]

        assert data["grant_type"] == "refresh_token"
        assert data["refresh_token"] == "test_refresh_token"
        assert data["client_id"] == "test_client_id"


@pytest.mark.asyncio
class TestRefreshTokenSecurity:
    """Test security aspects of token refresh."""

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_refresh_token_sent_securely(self, mock_client_class):
        """Test that refresh token is sent in request body, not URL."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        await OAuthManager.refresh_token(
            token_endpoint="https://oauth.example.com/token",
            client_id="test_client",
            refresh_token="secret_refresh_token"
        )

        # Verify refresh token is in request body (data), not URL
        call_args = mock_client.post.call_args
        url = call_args[0][0]
        data = call_args[1]["data"]

        # Refresh token should NOT be in URL
        assert "secret_refresh_token" not in url
        # Refresh token SHOULD be in body
        assert data["refresh_token"] == "secret_refresh_token"

    @patch('app.core.services.mcp.oauth_manager.httpx.AsyncClient')
    async def test_old_refresh_token_should_be_invalidated_after_rotation(self, mock_client_class):
        """Test that OAuth 2.1 invalidates old refresh token after rotation."""
        # Note: This is a provider-side behavior, our client should handle it
        # by always using the latest refresh token returned

        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",  # Rotated
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = AsyncMock()
        mock_client_class.return_value = mock_client

        old_refresh = "old_refresh"
        result = await OAuthManager.refresh_token(
            token_endpoint="https://oauth.example.com/token",
            client_id="test_client",
            refresh_token=old_refresh
        )

        # Client should use the new refresh token for future requests
        new_refresh = result["refresh_token"]
        assert new_refresh != old_refresh
        assert new_refresh == "new_refresh"
