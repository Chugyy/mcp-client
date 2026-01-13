#!/usr/bin/env python3
# app/core/utils/http_client.py
"""Shared HTTP client with connection pooling for external API calls."""

import httpx
from typing import Optional
from config.logger import logger


_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """
    Returns the shared HTTP client with connection pooling.

    Returns:
        httpx.AsyncClient: The shared HTTP client instance

    Raises:
        RuntimeError: If HTTP client not initialized
    """
    global _http_client
    if _http_client is None:
        raise RuntimeError("HTTP client not initialized. Call init_http_client() first.")
    return _http_client


async def init_http_client():
    """
    Initialize HTTP client with connection pooling.

    Configuration:
    - max_connections=100: Maximum concurrent connections across all hosts
    - max_keepalive_connections=20: Persistent connections kept alive for reuse
    - timeout=60s total, 10s connect: Connection timeout settings
    - http2=True if available: Enable HTTP/2 for connection multiplexing (graceful fallback to HTTP/1.1)
    """
    global _http_client

    # Try to enable HTTP/2, fallback to HTTP/1.1 if h2 package not installed
    http2_enabled = True
    try:
        import h2  # noqa
    except ImportError:
        http2_enabled = False
        logger.warning("h2 package not installed, HTTP/2 support disabled (falling back to HTTP/1.1)")

    _http_client = httpx.AsyncClient(
        limits=httpx.Limits(
            max_connections=100,        # Maximum concurrent connections
            max_keepalive_connections=20  # Keep-alive pool size
        ),
        timeout=httpx.Timeout(60.0, connect=10.0),
        http2=http2_enabled  # Enable HTTP/2 if available
    )
    logger.info(
        "✅ HTTP client pool initialized",
        extra={
            "max_connections": 100,
            "max_keepalive_connections": 20,
            "http2_enabled": http2_enabled,
            "timeout_total": 60.0,
            "timeout_connect": 10.0
        }
    )


async def close_http_client():
    """Close HTTP client and cleanup connections."""
    global _http_client
    if _http_client:
        await _http_client.aclose()
        logger.info("✅ HTTP client pool closed")
        _http_client = None
