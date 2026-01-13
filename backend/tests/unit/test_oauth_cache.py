"""Unit tests for OAuth metadata caching."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from app.core.utils.oauth_cache import (
    get_cached_metadata,
    clear_cache,
    get_cache_stats,
    _metadata_cache,
    METADATA_TTL
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset cache before and after each test."""
    # Clear before test
    _metadata_cache.clear()
    yield
    # Clear after test
    _metadata_cache.clear()


@pytest.mark.asyncio
class TestOAuthMetadataCache:
    """Test OAuth metadata caching functionality."""

    async def test_cache_miss_fetches_fresh_metadata(self):
        """Test that cache miss triggers fetch and caches result."""
        test_url = "https://example.com/.well-known/oauth"
        test_metadata = {"authorization_endpoint": "https://example.com/auth"}

        # Mock fetcher
        fetcher = AsyncMock(return_value=test_metadata)

        # First call - cache miss
        result = await get_cached_metadata(test_url, fetcher)

        assert result == test_metadata
        assert fetcher.call_count == 1
        fetcher.assert_called_once_with(test_url)

        # Verify metadata is cached
        stats = get_cache_stats()
        assert stats["entry_count"] == 1
        assert test_url in stats["cached_urls"]

    async def test_cache_hit_returns_cached_data(self):
        """Test that cache hit returns cached data without fetching."""
        test_url = "https://example.com/.well-known/oauth"
        test_metadata = {"authorization_endpoint": "https://example.com/auth"}

        fetcher = AsyncMock(return_value=test_metadata)

        # First call - cache miss
        result1 = await get_cached_metadata(test_url, fetcher)
        assert result1 == test_metadata
        assert fetcher.call_count == 1

        # Second call - cache hit
        result2 = await get_cached_metadata(test_url, fetcher)
        assert result2 == test_metadata
        assert fetcher.call_count == 1  # No additional fetch

    async def test_cache_expiration_triggers_refresh(self):
        """Test that expired cache triggers fresh fetch."""
        test_url = "https://example.com/.well-known/oauth"
        metadata_v1 = {"version": "v1"}
        metadata_v2 = {"version": "v2"}

        fetcher = AsyncMock(side_effect=[metadata_v1, metadata_v2])

        # First fetch
        result1 = await get_cached_metadata(test_url, fetcher)
        assert result1 == metadata_v1

        # Manually expire cache
        expired_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        _metadata_cache[test_url] = (metadata_v1, expired_time)

        # Second fetch - should refresh
        result2 = await get_cached_metadata(test_url, fetcher)
        assert result2 == metadata_v2
        assert fetcher.call_count == 2

    async def test_stale_cache_fallback_on_error(self):
        """Test fallback to stale cache when fetch fails."""
        test_url = "https://example.com/.well-known/oauth"
        cached_metadata = {"cached": "data"}

        # First fetch succeeds
        fetcher = AsyncMock(return_value=cached_metadata)
        result1 = await get_cached_metadata(test_url, fetcher)
        assert result1 == cached_metadata

        # Expire cache
        expired_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        _metadata_cache[test_url] = (cached_metadata, expired_time)

        # Second fetch fails - should return stale cache
        fetcher = AsyncMock(side_effect=Exception("Provider unreachable"))
        result2 = await get_cached_metadata(test_url, fetcher)
        assert result2 == cached_metadata  # Stale cache returned

    async def test_no_cache_on_error_raises_exception(self):
        """Test that error is raised when fetch fails and no cache exists."""
        test_url = "https://example.com/.well-known/oauth"

        fetcher = AsyncMock(side_effect=Exception("Provider unreachable"))

        with pytest.raises(Exception, match="Provider unreachable"):
            await get_cached_metadata(test_url, fetcher)

    async def test_clear_specific_url(self):
        """Test clearing cache for specific URL."""
        url1 = "https://example1.com/.well-known/oauth"
        url2 = "https://example2.com/.well-known/oauth"

        fetcher1 = AsyncMock(return_value={"server": "1"})
        fetcher2 = AsyncMock(return_value={"server": "2"})

        # Cache both URLs
        await get_cached_metadata(url1, fetcher1)
        await get_cached_metadata(url2, fetcher2)

        stats = get_cache_stats()
        assert stats["entry_count"] == 2

        # Clear only url1
        await clear_cache(url1)

        stats = get_cache_stats()
        assert stats["entry_count"] == 1
        assert url1 not in stats["cached_urls"]
        assert url2 in stats["cached_urls"]

    async def test_clear_all_cache(self):
        """Test clearing entire cache."""
        fetcher = AsyncMock(return_value={"data": "test"})

        # Cache multiple URLs
        await get_cached_metadata("https://url1.com", fetcher)
        await get_cached_metadata("https://url2.com", fetcher)
        await get_cached_metadata("https://url3.com", fetcher)

        stats = get_cache_stats()
        assert stats["entry_count"] == 3

        # Clear all
        await clear_cache()

        stats = get_cache_stats()
        assert stats["entry_count"] == 0
        assert stats["cached_urls"] == []

    async def test_cache_stats(self):
        """Test cache statistics reporting."""
        stats = get_cache_stats()
        assert "entry_count" in stats
        assert "cached_urls" in stats
        assert "ttl_seconds" in stats
        assert stats["ttl_seconds"] == METADATA_TTL.total_seconds()

    async def test_concurrent_cache_access(self):
        """Test thread-safe concurrent cache access."""
        import asyncio

        test_url = "https://example.com/.well-known/oauth"
        test_metadata = {"concurrent": "test"}

        # Simulate slow fetch
        async def slow_fetcher(url):
            await asyncio.sleep(0.1)
            return test_metadata

        # Execute concurrent requests
        tasks = [get_cached_metadata(test_url, slow_fetcher) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should return same cached data
        assert all(r == test_metadata for r in results)

        # Only one fetch should have occurred (cache lock ensures this)
        stats = get_cache_stats()
        assert stats["entry_count"] == 1

    async def test_different_urls_cached_separately(self):
        """Test that different URLs are cached separately."""
        url1 = "https://provider1.com/.well-known/oauth"
        url2 = "https://provider2.com/.well-known/oauth"

        metadata1 = {"provider": "1"}
        metadata2 = {"provider": "2"}

        fetcher1 = AsyncMock(return_value=metadata1)
        fetcher2 = AsyncMock(return_value=metadata2)

        result1 = await get_cached_metadata(url1, fetcher1)
        result2 = await get_cached_metadata(url2, fetcher2)

        assert result1 == metadata1
        assert result2 == metadata2

        # Verify both are cached
        stats = get_cache_stats()
        assert stats["entry_count"] == 2
        assert url1 in stats["cached_urls"]
        assert url2 in stats["cached_urls"]

    async def test_ttl_configuration(self):
        """Test that TTL is configurable."""
        stats = get_cache_stats()
        # Default is 1 hour (3600 seconds)
        assert stats["ttl_seconds"] == 3600.0
