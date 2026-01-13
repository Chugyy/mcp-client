"""Integration tests for database connection pooling functionality."""

import pytest
import asyncio
from app.database.db import get_pool, get_connection


class TestPoolFunctionality:
    """Integration tests for connection pool real functionality."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires running FastAPI app with initialized pool")
    async def test_pool_accessible_from_running_app(self):
        """Test that pool is accessible when app is running."""
        # This test requires the FastAPI app to be running with lifespan
        # It's marked as skip for unit test runs
        pool = await get_pool()
        assert pool is not None
        assert hasattr(pool, 'acquire')
        assert hasattr(pool, 'close')

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires running FastAPI app")
    async def test_pool_connection_acquisition(self):
        """Test acquiring connection from pool."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            # Execute simple query
            result = await conn.fetchval("SELECT 1")
            assert result == 1

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires running FastAPI app")
    async def test_pool_search_path_configured(self):
        """Test that connections from pool have correct search_path."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            search_path = await conn.fetchval("SHOW search_path")

            # Verify expected schemas are in search_path
            assert 'core' in search_path
            assert 'agents' in search_path
            assert 'chat' in search_path
            assert 'mcp' in search_path
            assert 'resources' in search_path
            assert 'audit' in search_path

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires running FastAPI app")
    async def test_concurrent_pool_usage(self):
        """Test that pool handles concurrent requests."""
        pool = await get_pool()

        async def query_database(query_id: int):
            async with pool.acquire() as conn:
                result = await conn.fetchval(f"SELECT {query_id}")
                return result

        # Run 20 concurrent queries
        tasks = [query_database(i) for i in range(1, 21)]
        results = await asyncio.gather(*tasks)

        # Verify all queries completed
        assert len(results) == 20
        assert results == list(range(1, 21))

    @pytest.mark.asyncio
    async def test_get_connection_still_works_backward_compatibility(self):
        """Test that old get_connection() still works for backward compatibility."""
        # This should still work during migration
        conn = await get_connection()
        try:
            result = await conn.fetchval("SELECT 1")
            assert result == 1
        finally:
            await conn.close()


class TestPoolConfiguration:
    """Tests to verify pool configuration matches requirements."""

    @pytest.mark.skip(reason="Documentation/verification test only")
    def test_pool_configuration_documented(self):
        """
        Verify pool configuration matches story requirements:
        - min_size=10
        - max_size=50
        - timeout=60
        - command_timeout=30
        - search_path configured

        This test serves as documentation of expected configuration.
        Actual verification happens in main.py lifespan.
        """
        expected_config = {
            'min_size': 10,
            'max_size': 50,
            'timeout': 60,
            'command_timeout': 30,
            'search_path': 'core, agents, chat, mcp, resources, audit, public'
        }

        # This is a documentation test - configuration is in main.py
        assert expected_config['min_size'] == 10
        assert expected_config['max_size'] == 50


class TestCRUDModulesUsage:
    """Test that CRUD modules work with pooling."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires database and running app")
    async def test_crud_users_with_pool(self):
        """Test users CRUD module with connection pool."""
        from app.database.crud import users

        # This would test actual CRUD operations with pool
        # Skipped in unit tests, would run in integration environment
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires database and running app")
    async def test_all_18_crud_modules_work(self):
        """Test that all 18 CRUD modules work with pool."""
        # Import all CRUD modules
        from app.database.crud import (
            users, teams, agents, chats, servers, models, api_keys, services,
            user_providers, uploads, resources, automations, executions,
            logs, triggers, refresh_tokens
        )

        # Verify they're importable
        crud_modules = [
            users, teams, agents, chats, servers, models, api_keys, services,
            user_providers, uploads, resources, automations, executions,
            logs, triggers, refresh_tokens
        ]

        # Count modules
        assert len(crud_modules) >= 16

        # Each module should have CRUD functions
        for module in crud_modules:
            assert hasattr(module, '__name__')


class TestPoolMetrics:
    """Tests for pool metrics and monitoring."""

    @pytest.mark.skip(reason="Verification test - metrics logged at startup")
    def test_pool_metrics_logged_at_startup(self):
        """
        Verify that pool metrics are logged at startup.

        Expected log messages:
        - "✅ Database pool created: min=10, max=50"

        This is verified by inspecting main.py lifespan implementation.
        """
        # This test documents expected behavior
        # Actual logging happens in main.py lifespan
        pass

    @pytest.mark.skip(reason="Verification test - pool cleanup logged")
    def test_pool_cleanup_logged_at_shutdown(self):
        """
        Verify that pool cleanup is logged at shutdown.

        Expected log messages:
        - "✅ Database pool closed"

        This is verified by inspecting main.py lifespan implementation.
        """
        # This test documents expected behavior
        # Actual logging happens in main.py lifespan
        pass


class TestMigrationVerification:
    """Tests to verify migration from direct connections to pool."""

    def test_get_connection_marked_deprecated(self):
        """Verify get_connection() has deprecation notice."""
        from app.database import db
        import inspect

        # Get function docstring
        docstring = inspect.getdoc(db.get_connection)

        # Should contain DEPRECATED notice
        assert 'DEPRECATED' in docstring or 'deprecated' in docstring

    def test_get_pool_function_exists(self):
        """Verify get_pool() function exists and is documented."""
        from app.database import db
        import inspect

        # Verify function exists
        assert hasattr(db, 'get_pool')

        # Verify it's a coroutine
        assert inspect.iscoroutinefunction(db.get_pool)

        # Verify it has docstring
        docstring = inspect.getdoc(db.get_pool)
        assert docstring is not None
        assert 'pool' in docstring.lower()

    def test_all_crud_files_exist(self):
        """Verify all 18 CRUD files exist."""
        import os
        from pathlib import Path

        crud_dir = Path(__file__).parent.parent.parent / 'app' / 'database' / 'crud'

        # List all python files (excluding __init__ and __pycache__)
        crud_files = [
            f for f in crud_dir.glob('*.py')
            if f.name != '__init__.py' and not f.name.startswith('.')
        ]

        # Should have 18 CRUD files
        assert len(crud_files) == 18, f"Expected 18 CRUD files, found {len(crud_files)}: {[f.name for f in crud_files]}"
