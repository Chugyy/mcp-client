#!/usr/bin/env python3
# app/core/utils/oauth_cache.py

"""
OAuth Metadata Caching Layer

Implements in-memory caching for OAuth 2.1 provider metadata with TTL
to reduce latency and improve resilience for authorization flows.

Cache-aside pattern:
1. Check cache for metadata
2. If hit and not expired → return cached data
3. If miss or expired → fetch from provider, update cache
4. If fetch fails → return stale cache if available, else raise error
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Callable, Any
import asyncio
from config.logger import logger
from config.config import settings


# In-memory cache: {url: (metadata_dict, expires_at_datetime)}
_metadata_cache: Dict[str, tuple[dict, datetime]] = {}

# Lock for thread-safe cache operations
_cache_lock = asyncio.Lock()


def _get_metadata_ttl() -> timedelta:
    """Get TTL from settings (lazy evaluation for testability)."""
    return timedelta(seconds=getattr(settings, 'oauth_metadata_cache_ttl', 3600))


async def get_cached_metadata(url: str, fetcher: Callable) -> dict:
    """
    Get cached OAuth metadata or fetch if expired.

    Args:
        url: Metadata URL to fetch/cache
        fetcher: Async callable that fetches metadata from the provider
                 Should return dict with metadata

    Returns:
        dict: OAuth metadata from cache or freshly fetched

    Raises:
        Exception: If fetch fails and no stale cache available
    """
    async with _cache_lock:
        # Check cache for hit
        if url in _metadata_cache:
            metadata, expires_at = _metadata_cache[url]
            if datetime.now(timezone.utc) < expires_at:
                logger.info(f"Cache HIT for {url}")
                return metadata  # Cache hit - return cached data

        # Cache miss or expired - fetch new metadata
        logger.info(f"Cache MISS for {url} - fetching fresh metadata")
        try:
            metadata = await fetcher(url)
            ttl = _get_metadata_ttl()
            _metadata_cache[url] = (metadata, datetime.now(timezone.utc) + ttl)
            logger.info(f"Cached metadata for {url}, expires in {ttl.total_seconds()}s")
            return metadata

        except Exception as e:
            # Fallback to stale cache if available
            if url in _metadata_cache:
                metadata, expired_at = _metadata_cache[url]
                logger.warning(
                    f"Using stale cached metadata for {url} due to fetch error: {e}. "
                    f"Cache expired at {expired_at.isoformat()}"
                )
                return metadata

            # No cache available - propagate error
            logger.error(f"Failed to fetch metadata for {url} and no cache available: {e}")
            raise


async def clear_cache(url: Optional[str] = None):
    """
    Clear cached metadata.

    Args:
        url: Specific URL to clear, or None to clear all cache

    Used for testing/debugging or manual cache invalidation.
    """
    async with _cache_lock:
        if url:
            if url in _metadata_cache:
                del _metadata_cache[url]
                logger.info(f"Cleared cache for {url}")
        else:
            _metadata_cache.clear()
            logger.info("Cleared all cached OAuth metadata")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics for monitoring.

    Returns:
        dict: Cache statistics including entry count and URLs
    """
    return {
        "entry_count": len(_metadata_cache),
        "cached_urls": list(_metadata_cache.keys()),
        "ttl_seconds": _get_metadata_ttl().total_seconds()
    }
