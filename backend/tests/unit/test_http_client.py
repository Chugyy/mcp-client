#!/usr/bin/env python3
"""Unit tests for HTTP client pool management."""

import pytest
import httpx
from app.core.utils import http_client


@pytest.mark.asyncio
async def test_http_client_not_initialized():
    """Test that get_http_client raises RuntimeError if not initialized."""
    # Reset module state
    http_client._http_client = None

    with pytest.raises(RuntimeError, match="HTTP client not initialized"):
        await http_client.get_http_client()


@pytest.mark.asyncio
async def test_http_client_initialization():
    """Test HTTP client initialization with correct configuration."""
    # Reset module state
    http_client._http_client = None

    # Initialize client
    await http_client.init_http_client()

    # Verify client was created
    client = await http_client.get_http_client()
    assert client is not None
    assert isinstance(client, httpx.AsyncClient)

    # Verify timeout configuration (public attribute)
    assert client.timeout.connect == 10.0
    # Total timeout is read timeout when not streaming
    assert client.timeout.read == 60.0

    # Cleanup
    await http_client.close_http_client()


@pytest.mark.asyncio
async def test_http_client_singleton():
    """Test that get_http_client returns the same instance."""
    # Reset module state
    http_client._http_client = None

    # Initialize client
    await http_client.init_http_client()

    # Get client twice
    client1 = await http_client.get_http_client()
    client2 = await http_client.get_http_client()

    # Verify same instance
    assert client1 is client2

    # Cleanup
    await http_client.close_http_client()


@pytest.mark.asyncio
async def test_http_client_close():
    """Test HTTP client cleanup."""
    # Reset module state
    http_client._http_client = None

    # Initialize client
    await http_client.init_http_client()
    client = await http_client.get_http_client()
    assert client is not None

    # Close client
    await http_client.close_http_client()

    # Verify client is None after close
    assert http_client._http_client is None

    # Verify get_http_client raises error after close
    with pytest.raises(RuntimeError, match="HTTP client not initialized"):
        await http_client.get_http_client()


@pytest.mark.asyncio
async def test_http_client_reinitialize():
    """Test re-initializing HTTP client after close."""
    # Reset module state
    http_client._http_client = None

    # Initialize, close, and re-initialize
    await http_client.init_http_client()
    await http_client.close_http_client()
    await http_client.init_http_client()

    # Verify client works after re-initialization
    client = await http_client.get_http_client()
    assert client is not None
    assert isinstance(client, httpx.AsyncClient)

    # Cleanup
    await http_client.close_http_client()


@pytest.mark.asyncio
async def test_http_client_close_idempotent():
    """Test that closing an already closed client is safe."""
    # Reset module state
    http_client._http_client = None

    # Initialize and close
    await http_client.init_http_client()
    await http_client.close_http_client()

    # Close again - should not raise error
    await http_client.close_http_client()

    # Verify client is still None
    assert http_client._http_client is None


@pytest.mark.asyncio
async def test_http_client_pool_limits():
    """Test that pool limits are configured correctly."""
    # Reset module state
    http_client._http_client = None

    # Initialize client
    await http_client.init_http_client()

    # Get client and verify pool limits
    client = await http_client.get_http_client()

    # Access pool via transport (implementation-specific to httpx/httpcore)
    pool = client._transport._pool
    assert pool._max_connections == 100
    assert pool._max_keepalive_connections == 20

    # Cleanup
    await http_client.close_http_client()
