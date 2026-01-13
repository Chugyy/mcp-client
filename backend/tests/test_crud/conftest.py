"""Pytest configuration and fixtures for CRUD integration tests.

These tests require a real PostgreSQL test database connection.
The autouse mocks from the parent conftest are disabled here.
"""

import pytest
import asyncpg
import os
import contextlib
from typing import Dict
import app.database.db as db_module


class FakePool:
    """Wraps a single asyncpg connection to mimic Pool interface.

    This allows us to use direct connections in tests while maintaining
    compatibility with code that expects pool.acquire() context manager.
    Avoids asyncio event loop conflicts with real connection pooling.
    """

    def __init__(self, conn):
        self._conn = conn

    @contextlib.asynccontextmanager
    async def acquire(self):
        """Mimic pool.acquire() context manager by yielding the connection."""
        yield self._conn

    async def release(self, conn):
        """Mimic pool.release() - no-op for single connection."""
        pass

    async def close(self):
        """Close the underlying connection."""
        await self._conn.close()


@pytest.fixture(autouse=True)
def mock_get_pool():
    """Override parent autouse mock to do nothing for CRUD integration tests."""
    # This fixture overrides the autouse mock_get_pool from parent conftest.py
    # by being more specific (closer to the test files). It does nothing, allowing
    # the real get_pool() function to work, which is then patched by mock_pool_for_crud.
    yield


@pytest.fixture(autouse=True)
def mock_settings():
    """Override parent autouse mock to do nothing for CRUD integration tests."""
    # This fixture overrides the autouse mock_settings from parent conftest.py
    yield


async def init_connection(conn):
    """Initialize connection with search_path."""
    await conn.execute("""
        SET search_path TO core, agents, chat, mcp, resources, audit, automation, public
    """)


@pytest.fixture
def test_db_pool():
    """Test database connection factory wrapped as FakePool for CRUD integration tests.

    Returns a FakePool that creates connections lazily in the current event loop.
    This avoids event loop conflicts by creating connections on-demand.
    """
    class LazyFakePool:
        """FakePool that creates connection lazily in current event loop."""

        def __init__(self):
            self._conn = None

        async def _get_or_create_conn(self):
            """Get existing connection or create new one in current event loop."""
            if self._conn is None:
                self._conn = await asyncpg.connect(
                    host=os.getenv("TEST_DB_HOST", "localhost"),
                    port=int(os.getenv("TEST_DB_PORT", "5432")),
                    database=os.getenv("TEST_DB_NAME", "test_backend"),
                    user=os.getenv("TEST_DB_USER", "hugohoarau"),
                    password=os.getenv("TEST_DB_PASSWORD", "")
                )
                await init_connection(self._conn)
            return self._conn

        @contextlib.asynccontextmanager
        async def acquire(self):
            """Mimic pool.acquire() by yielding the lazy connection."""
            conn = await self._get_or_create_conn()
            yield conn

        async def release(self, conn):
            """Mimic pool.release() - no-op for single connection."""
            pass

        async def close(self):
            """Close the underlying connection if it exists."""
            if self._conn is not None:
                await self._conn.close()
                self._conn = None

    fake_pool = LazyFakePool()
    yield fake_pool

    # No async cleanup needed here - will be handled per test


@pytest.fixture(autouse=True)
def mock_pool_for_crud(test_db_pool):
    """Set test pool for CRUD tests.

    This autouse fixture sets db_module._test_pool which get_pool() will use.
    The lazy pool ensures connections are created in the correct event loop.
    """
    # Store original
    original = db_module._test_pool

    # Set test pool
    db_module._test_pool = test_db_pool

    yield

    # Restore original
    db_module._test_pool = original


@pytest.fixture
async def clean_db(test_db_pool):
    """Clean database before each test.

    Truncates all tables across all 7 schemas.
    Uses CASCADE to handle foreign key constraints.
    """
    async with test_db_pool.acquire() as conn:
        # Use a single TRUNCATE statement to avoid multiple transactions
        await conn.execute("""
            TRUNCATE TABLE
                core.users,
                core.reset_tokens,
                core.refresh_tokens,
                core.api_keys,
                core.services,
                core.models,
                core.user_providers,
                agents.agents,
                agents.teams,
                agents.memberships,
                agents.configurations,
                chat.chats,
                chat.messages,
                mcp.servers,
                mcp.tools,
                mcp.oauth_tokens,
                resources.resources,
                resources.uploads,
                resources.embeddings,
                audit.logs,
                audit.validations,
                automation.automations,
                automation.workflow_steps,
                automation.triggers,
                automation.executions,
                automation.execution_step_logs
            CASCADE
        """)

    yield


@pytest.fixture
async def sample_user(clean_db, mock_pool_for_crud) -> Dict:
    """Create a sample user for testing.

    Returns a dict with user data that can be used in tests.
    """
    from app.database.crud import users
    from app.core.utils.auth import hash_password

    # Create user with hashed password
    hashed_pw = hash_password("password123")
    user_id = await users.create_user(
        email="test@example.com",
        password=hashed_pw,
        name="Test User"
    )
    user = await users.get_user(user_id)
    return user


@pytest.fixture
async def sample_agent(clean_db, sample_user, mock_pool_for_crud) -> Dict:
    """Create a sample agent for testing.

    Depends on sample_user fixture.
    Returns a dict with agent data.
    """
    from app.database.crud import agents

    agent_id = await agents.create_agent(
        user_id=sample_user["id"],
        name="Test Agent",
        description="A test agent",
        system_prompt="Test instructions",
        tags=["test"]
    )
    agent = await agents.get_agent(agent_id)
    return agent


@pytest.fixture
async def sample_service(clean_db, mock_pool_for_crud) -> Dict:
    """Create a sample LLM service for testing.

    Returns a dict with service data.
    """
    from app.database.crud import services

    service_id = await services.create_service(
        name="Test Service",
        provider="openai",
        description="Test service"
    )
    service = await services.get_service(service_id)
    return service


@pytest.fixture
async def sample_team(clean_db, sample_user, mock_pool_for_crud) -> Dict:
    """Create a sample team for testing.

    Depends on sample_user fixture.
    Returns a dict with team data.
    """
    from app.database.crud import teams

    team_id = await teams.create_team(
        name="Test Team",
        system_prompt="Test system prompt",
        description="A test team"
    )
    team = await teams.get_team(team_id)
    return team
