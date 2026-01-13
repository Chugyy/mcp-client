"""Integration tests for OAuth metadata caching with OAuthManager."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.services.mcp.oauth_manager import OAuthManager
from app.core.utils.oauth_cache import _metadata_cache, get_cache_stats


@pytest.fixture(autouse=True)
def clear_cache_before_test():
    """Clear cache before each test."""
    _metadata_cache.clear()
    yield
    _metadata_cache.clear()


@pytest.mark.asyncio
class TestOAuthManagerCaching:
    """Test OAuth metadata caching in OAuthManager."""

    async def test_fetch_protected_resource_with_caching(self):
        """Test that fetch_protected_resource uses cache."""
        test_url = "https://example.com/.well-known/oauth-protected-resource"
        test_response = {
            "resource": "https://example.com/mcp/",
            "authorization_servers": ["https://auth.example.com"]
        }

        # Mock HTTP client pool
        with patch('app.core.utils.http_client.get_http_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value=test_response)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            # First call - cache miss
            result1 = await OAuthManager.fetch_protected_resource(test_url)

            assert result1["success"] is True
            assert result1["resource"] == test_response["resource"]
            assert result1["authorization_servers"] == test_response["authorization_servers"]
            assert mock_client.get.call_count == 1

            # Second call - cache hit (no additional HTTP request)
            result2 = await OAuthManager.fetch_protected_resource(test_url)

            assert result2["success"] is True
            assert result2 == result1
            assert mock_client.get.call_count == 1  # No additional fetch

            # Verify cache
            stats = get_cache_stats()
            assert stats["entry_count"] == 1
            assert test_url in stats["cached_urls"]

    async def test_fetch_authorization_server_with_caching(self):
        """Test that fetch_authorization_server uses cache."""
        auth_server_url = "https://auth.example.com"
        metadata_url = f"{auth_server_url}/.well-known/oauth-authorization-server"
        test_response = {
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "jwks_uri": "https://auth.example.com/jwks"
        }

        with patch('app.core.utils.http_client.get_http_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value=test_response)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            # First call - cache miss
            result1 = await OAuthManager.fetch_authorization_server(auth_server_url)

            assert result1["success"] is True
            assert result1["authorization_endpoint"] == test_response["authorization_endpoint"]
            assert result1["token_endpoint"] == test_response["token_endpoint"]
            assert mock_client.get.call_count == 1

            # Second call - cache hit
            result2 = await OAuthManager.fetch_authorization_server(auth_server_url)

            assert result2["success"] is True
            assert result2 == result1
            assert mock_client.get.call_count == 1  # No additional fetch

            # Verify cache
            stats = get_cache_stats()
            assert stats["entry_count"] == 1
            assert metadata_url in stats["cached_urls"]

    async def test_stale_cache_fallback_on_provider_failure(self):
        """Test fallback to stale cache when provider is unreachable."""
        test_url = "https://example.com/.well-known/oauth-protected-resource"
        test_response = {
            "resource": "https://example.com/mcp/",
            "authorization_servers": ["https://auth.example.com"]
        }

        with patch('app.core.utils.http_client.get_http_client') as mock_get_client:
            mock_client = AsyncMock()

            # First call succeeds
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value=test_response)
            mock_client.get = AsyncMock(return_value=mock_response)


            mock_get_client.return_value = mock_client

            result1 = await OAuthManager.fetch_protected_resource(test_url)
            assert result1["success"] is True

            # Expire cache manually
            from app.core.utils.oauth_cache import _metadata_cache
            from datetime import datetime, timedelta, timezone
            if test_url in _metadata_cache:
                metadata, _ = _metadata_cache[test_url]
                expired_time = datetime.now(timezone.utc) - timedelta(seconds=1)
                _metadata_cache[test_url] = (metadata, expired_time)

            # Second call fails (provider down) - should use stale cache
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

            result2 = await OAuthManager.fetch_protected_resource(test_url)

            # Should return stale cache
            assert result2["success"] is True
            assert result2["resource"] == test_response["resource"]

    async def test_multiple_providers_cached_separately(self):
        """Test that different providers are cached independently."""
        provider1_url = "https://provider1.com/.well-known/oauth-protected-resource"
        provider2_url = "https://provider2.com/.well-known/oauth-protected-resource"

        response1 = {
            "resource": "https://provider1.com/mcp/",
            "authorization_servers": ["https://auth1.com"]
        }
        response2 = {
            "resource": "https://provider2.com/mcp/",
            "authorization_servers": ["https://auth2.com"]
        }

        with patch('app.core.utils.http_client.get_http_client') as mock_get_client:
            mock_client = AsyncMock()

            # Setup responses for different URLs
            def get_response(url):
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                if "provider1" in url:
                    mock_resp.json = MagicMock(return_value=response1)
                else:
                    mock_resp.json = MagicMock(return_value=response2)
                return mock_resp

            mock_client.get = AsyncMock(side_effect=lambda url: get_response(url))


            mock_get_client.return_value = mock_client

            # Fetch both providers
            result1 = await OAuthManager.fetch_protected_resource(provider1_url)
            result2 = await OAuthManager.fetch_protected_resource(provider2_url)

            assert result1["resource"] == response1["resource"]
            assert result2["resource"] == response2["resource"]

            # Verify both are cached
            stats = get_cache_stats()
            assert stats["entry_count"] == 2
            assert provider1_url in stats["cached_urls"]
            assert provider2_url in stats["cached_urls"]

    async def test_cache_hit_rate_monitoring(self):
        """Test cache hit rate can be monitored via stats."""
        test_url = "https://example.com/.well-known/oauth-protected-resource"
        test_response = {
            "resource": "https://example.com/mcp/",
            "authorization_servers": ["https://auth.example.com"]
        }

        with patch('app.core.utils.http_client.get_http_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value=test_response)
            mock_client.get = AsyncMock(return_value=mock_response)


            mock_get_client.return_value = mock_client

            # Execute multiple requests
            for _ in range(10):
                await OAuthManager.fetch_protected_resource(test_url)

            # Only 1 actual HTTP request should have been made (9 cache hits)
            assert mock_client.get.call_count == 1

            # Cache hit rate = 9/10 = 90%
            stats = get_cache_stats()
            assert stats["entry_count"] == 1

    async def test_oauth_flow_with_cached_metadata(self):
        """Test complete OAuth flow benefits from cached metadata."""
        server_url = "https://mcp-server.com"
        resource_metadata_url = f"{server_url}/.well-known/oauth-protected-resource"
        auth_server_url = "https://auth-server.com"
        auth_metadata_url = f"{auth_server_url}/.well-known/oauth-authorization-server"

        resource_response = {
            "resource": f"{server_url}/mcp/",
            "authorization_servers": [auth_server_url]
        }
        auth_response = {
            "authorization_endpoint": f"{auth_server_url}/authorize",
            "token_endpoint": f"{auth_server_url}/token",
            "jwks_uri": f"{auth_server_url}/jwks"
        }

        with patch('app.core.utils.http_client.get_http_client') as mock_get_client:
            mock_client = AsyncMock()

            def get_response(url):
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                if "oauth-protected-resource" in url:
                    mock_resp.json = MagicMock(return_value=resource_response)
                else:
                    mock_resp.json = MagicMock(return_value=auth_response)
                return mock_resp

            mock_client.get = AsyncMock(side_effect=lambda url: get_response(url))


            mock_get_client.return_value = mock_client

            # Simulate OAuth flow: fetch both metadata types
            prm = await OAuthManager.fetch_protected_resource(resource_metadata_url)
            asm = await OAuthManager.fetch_authorization_server(auth_server_url)

            assert prm["success"] is True
            assert asm["success"] is True
            assert mock_client.get.call_count == 2

            # Repeat flow - should use cache
            prm2 = await OAuthManager.fetch_protected_resource(resource_metadata_url)
            asm2 = await OAuthManager.fetch_authorization_server(auth_server_url)

            assert prm2 == prm
            assert asm2 == asm
            assert mock_client.get.call_count == 2  # No additional fetches

            # Verify cache stats
            stats = get_cache_stats()
            assert stats["entry_count"] == 2
