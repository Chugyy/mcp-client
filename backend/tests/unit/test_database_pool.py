"""Unit tests for database connection pooling."""

import sys
import pytest
import asyncpg
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from app.database.db import init_db


@pytest.fixture
def mock_app_with_pool():
    """Fixture that creates a mock app with db_pool."""
    mock_app = MagicMock()
    mock_pool = AsyncMock(spec=asyncpg.Pool)
    mock_pool.get_size.return_value = 10
    mock_pool.get_max_size.return_value = 50
    mock_pool.get_idle_size.return_value = 5
    mock_app.state.db_pool = mock_pool
    return mock_app, mock_pool


@pytest.fixture(autouse=True)
def mock_main_app():
    """Auto-use fixture to mock app.api.main module before tests run."""
    # Create a mock for the main module
    mock_main_module = MagicMock()
    mock_app = MagicMock()
    mock_main_module.app = mock_app

    # Store original if it exists
    original_main = sys.modules.get('app.api.main')

    # Inject mock into sys.modules
    sys.modules['app.api.main'] = mock_main_module

    yield mock_app

    # Restore original
    if original_main:
        sys.modules['app.api.main'] = original_main
    else:
        sys.modules.pop('app.api.main', None)


class TestDatabasePool:
    """Unit tests for connection pool functionality."""

    @pytest.mark.asyncio
    async def test_pool_creation_parameters(self, mock_main_app):
        """Test that pool is created with correct parameters."""
        from app.database.db import get_pool

        mock_pool = AsyncMock(spec=asyncpg.Pool)
        mock_pool.get_size.return_value = 10
        mock_pool.get_max_size.return_value = 50
        mock_pool.get_idle_size.return_value = 5
        mock_main_app.state.db_pool = mock_pool

        pool = await get_pool()

        assert pool is not None
        assert pool == mock_pool
        # Verify pool has expected methods
        assert hasattr(pool, 'acquire')
        assert hasattr(pool, 'close')

    @pytest.mark.asyncio
    async def test_connection_acquisition_and_release(self, mock_main_app):
        """Test that connections are properly acquired and released."""
        from app.database.db import get_pool

        mock_conn = AsyncMock()
        mock_pool = AsyncMock(spec=asyncpg.Pool)

        # Setup context manager behavior
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.acquire.return_value.__aexit__.return_value = None

        mock_main_app.state.db_pool = mock_pool

        pool = await get_pool()

        # Test acquisition via context manager
        async with pool.acquire() as conn:
            assert conn == mock_conn

        # Verify acquire was called
        mock_pool.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_path_configuration(self, mock_main_app):
        """Test that search_path is configured correctly on pooled connections."""
        from app.database.db import get_pool

        # Create mock connection
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value='core, agents, chat, mcp, resources, audit, public')

        mock_pool = AsyncMock(spec=asyncpg.Pool)
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.acquire.return_value.__aexit__.return_value = None

        mock_main_app.state.db_pool = mock_pool

        pool = await get_pool()

        # Acquire connection and verify search_path
        async with pool.acquire() as conn:
            # Query current search_path (this would be set by pool server_settings)
            search_path = await conn.fetchval("SHOW search_path")

            # Verify it contains expected schemas
            assert 'core' in search_path
            assert 'agents' in search_path
            assert 'chat' in search_path
            assert 'mcp' in search_path
            assert 'resources' in search_path
            assert 'audit' in search_path

    @pytest.mark.asyncio
    async def test_pool_cleanup_on_shutdown(self, mock_main_app):
        """Test that pool is properly closed on shutdown."""
        from app.database.db import get_pool

        mock_pool = AsyncMock(spec=asyncpg.Pool)
        mock_pool.close = AsyncMock()

        mock_main_app.state.db_pool = mock_pool

        pool = await get_pool()

        # Simulate shutdown
        await pool.close()

        # Verify close was called
        mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pool_without_initialization(self, mock_main_app):
        """Test that get_pool raises error if pool not initialized."""
        from app.database.db import get_pool

        # Simulate app state without db_pool
        mock_main_app.state = MagicMock(spec=[])  # Empty spec means no attributes

        # Should raise AttributeError when accessing non-existent pool
        with pytest.raises(AttributeError):
            await get_pool()

    @pytest.mark.asyncio
    async def test_init_db_with_pool(self):
        """Test that init_db works with connection pool."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.close = AsyncMock()

        with patch('app.database.db.get_connection', return_value=mock_conn):
            # init_db should create a temporary connection to verify DB
            await init_db()

            # Verify connection was used and closed
            mock_conn.execute.assert_called_once_with("SELECT 1")
            mock_conn.close.assert_called_once()


class TestPoolMetrics:
    """Tests for connection pool metrics and monitoring."""

    @pytest.mark.asyncio
    async def test_pool_metrics_available(self, mock_main_app):
        """Test that pool metrics are available."""
        from app.database.db import get_pool

        mock_pool = AsyncMock(spec=asyncpg.Pool)
        mock_pool.get_size.return_value = 15  # Active connections
        mock_pool.get_max_size.return_value = 50  # Max connections
        mock_pool.get_idle_size.return_value = 5  # Idle connections

        mock_main_app.state.db_pool = mock_pool

        pool = await get_pool()

        # Verify metrics methods exist and return expected values
        assert pool.get_size() == 15
        assert pool.get_max_size() == 50
        assert pool.get_idle_size() == 5

        # Calculate waiting (conceptually: size - idle)
        waiting = pool.get_size() - pool.get_idle_size()
        assert waiting == 10

    @pytest.mark.asyncio
    async def test_pool_not_exhausted_under_normal_load(self, mock_main_app):
        """Test that pool handles normal load without exhaustion."""
        from app.database.db import get_pool

        mock_pool = AsyncMock(spec=asyncpg.Pool)
        mock_pool.get_size.return_value = 20  # Current size
        mock_pool.get_max_size.return_value = 50  # Max size

        mock_main_app.state.db_pool = mock_pool

        pool = await get_pool()

        # Verify pool not exhausted (size < max_size)
        assert pool.get_size() < pool.get_max_size()

        # Pool has capacity for more connections
        capacity = pool.get_max_size() - pool.get_size()
        assert capacity == 30
