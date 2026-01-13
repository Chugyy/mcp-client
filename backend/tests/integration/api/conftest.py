"""Pytest configuration and fixtures for API integration tests.

These tests use FastAPI TestClient with real database connections.
External services (LLM, MCP) are mocked to avoid real API calls.
"""

import pytest
import asyncpg
import os
import contextlib
from typing import Dict
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import app.database.db as db_module
from .test_constants import (
    TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME, TEST_DB_USER, TEST_DB_PASSWORD,
    TEST_USER_EMAIL, TEST_USER_PASSWORD, TEST_USER_NAME,
    OTHER_USER_EMAIL, OTHER_USER_PASSWORD, OTHER_USER_NAME,
    DB_SEARCH_PATH
)


async def get_test_db_connection():
    """Create a test database connection with search_path configured.

    This helper centralizes DB connection logic to avoid duplication.

    Returns:
        asyncpg.Connection: A configured database connection
    """
    conn = await asyncpg.connect(
        host=TEST_DB_HOST,
        port=TEST_DB_PORT,
        database=TEST_DB_NAME,
        user=TEST_DB_USER,
        password=TEST_DB_PASSWORD
    )
    # Set search_path for multi-schema support
    await conn.execute(f"SET search_path TO {DB_SEARCH_PATH}")
    return conn


class LazyFakePool:
    """FakePool that creates connection lazily in current event loop.

    This avoids asyncio event loop conflicts by creating connections
    on-demand in the test's event loop.
    """

    def __init__(self):
        self._conn = None

    async def _get_or_create_conn(self):
        """Get existing connection or create new one in current event loop."""
        if self._conn is None:
            self._conn = await get_test_db_connection()
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


@pytest.fixture(autouse=True)
def mock_get_pool():
    """Override parent autouse mock to do nothing for API integration tests."""
    # Allow real get_pool() to work with test database via env vars
    yield


@pytest.fixture(autouse=True)
def mock_settings():
    """Override parent autouse mock to do nothing for API integration tests."""
    yield


@pytest.fixture(autouse=True)
def setup_test_db_env():
    """Setup test database environment variables.

    This ensures the app's lifespan creates a pool connected to test database.
    """
    import os
    original_env = {}
    test_env = {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "test_backend",
        "DB_USER": "hugohoarau",
        "DB_PASSWORD": ""
    }

    # Save original and set test values
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def clean_db():
    """Clean database before each test.

    Uses direct connection to truncate all tables.
    Runs synchronously using asyncio.run().
    """
    import asyncio

    async def _clean():
        conn = await get_test_db_connection()

        # Clean all tables
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

        await conn.close()

    asyncio.run(_clean())
    yield


@pytest.fixture
def test_db_pool_for_api(setup_test_db_env):
    """Create a test database pool and register it with db module.

    This allows get_pool() to find the test pool.
    """
    pool = LazyFakePool()

    # Set the test pool in db module so get_pool() can find it
    import app.database.db as db_module
    original = db_module._test_pool
    db_module._test_pool = pool

    yield pool

    # Restore original
    db_module._test_pool = original


@pytest.fixture
def client(test_db_pool_for_api):
    """FastAPI TestClient for API integration tests.

    Uses a simplified lifespan that skips migrations and infrastructure sync.
    """
    from fastapi import FastAPI
    from contextlib import asynccontextmanager
    from config.config import settings
    from app.core.utils.http_client import init_http_client, close_http_client

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        """Simplified lifespan for testing - no migrations or sync."""
        # Initialize HTTP client
        await init_http_client()

        # Re-initialize LLM adapters with pooled client
        from app.core.services.llm.gateway import llm_gateway
        await llm_gateway.reinit_with_pooled_client()

        yield

        # Cleanup
        await close_http_client()

    # Create test app with test lifespan
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.api.v1.routes import (
        auth, users, health, agents, teams, chats, uploads, resources,
        validations, servers, models, api_keys, services, user_providers,
        oauth, automations
    )
    from app.core.exceptions import AppException
    from app.api.v1.exception_handlers import app_exception_handler

    test_app = FastAPI(title="Test API", lifespan=test_lifespan)

    # Add exception handlers
    test_app.add_exception_handler(AppException, app_exception_handler)

    # Add CORS
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes (API v1)
    test_app.include_router(auth.router, prefix="/api/v1")
    test_app.include_router(users.router, prefix="/api/v1")
    test_app.include_router(agents.router, prefix="/api/v1")
    test_app.include_router(teams.router, prefix="/api/v1")
    test_app.include_router(chats.router, prefix="/api/v1")
    test_app.include_router(uploads.router, prefix="/api/v1")
    test_app.include_router(resources.router, prefix="/api/v1")
    test_app.include_router(validations.router, prefix="/api/v1")
    test_app.include_router(servers.router, prefix="/api/v1")
    test_app.include_router(models.router, prefix="/api/v1")
    test_app.include_router(api_keys.router, prefix="/api/v1")
    test_app.include_router(services.router, prefix="/api/v1")
    test_app.include_router(user_providers.router, prefix="/api/v1")
    test_app.include_router(oauth.router, prefix="/api/v1")
    test_app.include_router(automations.router, prefix="/api/v1")

    # Health routes (no version prefix - matches production)
    test_app.include_router(health.router)

    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture
def test_user(client, clean_db) -> Dict:
    """Create a test user via API registration.

    Returns user dict with plaintext password for authentication.
    """
    # Register a user via API
    response = client.post("/api/v1/auth/register", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "name": TEST_USER_NAME
    })

    assert response.status_code == 201, f"Registration failed: {response.text}"

    user_data = response.json()
    # Add id key (register returns user_id, but /me returns id)
    user_data["id"] = user_data["user_id"]
    user_data["plain_password"] = TEST_USER_PASSWORD
    return user_data


@pytest.fixture
def authenticated_client(client, test_user):
    """TestClient with authenticated user session.

    The test_user fixture already registered and logged in the user,
    so cookies are already set on the client.

    IMPORTANT: This returns the same client instance as 'client' fixture.
    For truly unauthenticated tests, use a fresh client without dependencies
    on authenticated fixtures.
    """
    # User is already logged in from registration
    # Just return the client which has the cookies
    return client


@pytest.fixture
def mock_llm_gateway():
    """Mock LLM gateway to avoid real API calls.

    Use this fixture in tests that interact with LLM (chats, models, etc).
    """
    with patch('app.core.services.llm.gateway.llm_gateway') as mock:
        # Mock stream_with_tools method (used by chat endpoints)
        async def mock_stream():
            yield {"type": "content_block_start", "index": 0}
            yield {"type": "content_block_delta", "delta": {"text": "Mocked"}}
            yield {"type": "content_block_delta", "delta": {"text": " stream"}}
            yield {"type": "content_block_stop"}
            yield {"type": "message_stop"}

        mock.stream_with_tools = AsyncMock(return_value=mock_stream())

        # Mock list_models method
        mock.list_models = AsyncMock(return_value={
            "openai": [{"id": "gpt-4", "name": "GPT-4"}],
            "anthropic": [{"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"}]
        })

        yield mock


@pytest.fixture
def mock_mcp_server_manager():
    """Mock MCP ServerManager to avoid real connections.

    Use this fixture in tests that interact with MCP servers.
    """
    with patch('app.core.services.mcp.manager.ServerManager') as mock_class:
        # Mock static methods
        mock_class.create = AsyncMock(return_value="srv_test123")
        mock_class.start_verify_async = AsyncMock(return_value=True)
        mock_class.delete = AsyncMock(return_value=True)
        mock_class.sync_tools = AsyncMock(return_value=5)  # 5 tools synced

        yield mock_class


@pytest.fixture(autouse=True)
def mock_mcp_verification():
    """Auto-mock MCP server verification to avoid real network calls.

    This only mocks the verification step, allowing real CRUD operations.
    """
    # Import the actual class to ensure module is loaded
    from app.core.services.mcp.manager import ServerManager

    with patch.object(ServerManager, 'start_verify_async', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = True
        yield mock_verify


@pytest.fixture
def mock_oauth_manager():
    """Mock OAuth manager to avoid real OAuth flows.

    Use this fixture in tests that interact with OAuth.
    """
    with patch('app.core.services.mcp.oauth_manager.OAuthManager') as mock_class:
        # Mock instance methods
        mock_instance = AsyncMock()
        mock_instance.discover_metadata = AsyncMock(return_value={
            "authorization_endpoint": "https://example.com/oauth/authorize",
            "token_endpoint": "https://example.com/oauth/token"
        })
        mock_instance.exchange_code_for_token = AsyncMock(return_value={
            "access_token": "mocked_access_token",
            "refresh_token": "mocked_refresh_token",
            "expires_in": 3600
        })
        mock_instance.refresh_access_token = AsyncMock(return_value={
            "access_token": "mocked_refreshed_token",
            "expires_in": 3600
        })

        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_agent(authenticated_client, test_user) -> Dict:
    """Create a sample agent via API.

    Depends on authenticated_client fixture.
    Note: Agent endpoint expects Form data, not JSON.
    """
    import json as json_module

    response = authenticated_client.post("/api/v1/agents", data={
        "name": "Test Agent",
        "description": "A test agent",
        "system_prompt": "You are a helpful test assistant",
        "tags": json_module.dumps(["test"]),  # JSON string for array
        "enabled": "true"
    })

    assert response.status_code == 201, f"Agent creation failed: {response.text}"
    return response.json()


@pytest.fixture
def sample_chat(authenticated_client, sample_agent) -> Dict:
    """Create a sample chat session via API.

    Depends on authenticated_client and sample_agent fixtures.
    """
    response = authenticated_client.post("/api/v1/chats", json={
        "agent_id": sample_agent["id"],
        "title": "Test Chat"
    })

    assert response.status_code == 201, f"Chat creation failed: {response.text}"
    return response.json()


@pytest.fixture
def sample_team(authenticated_client) -> Dict:
    """Create a sample team via API."""
    response = authenticated_client.post("/api/v1/teams", json={
        "name": "Test Team",
        "system_prompt": "Team test prompt",
        "description": "A test team"
    })

    assert response.status_code == 201, f"Team creation failed: {response.text}"
    return response.json()


@pytest.fixture
def sample_server(authenticated_client) -> Dict:
    """Create a sample MCP server via API."""
    response = authenticated_client.post("/api/v1/mcp/servers", json={
        "name": "Test MCP Server",
        "description": "A test MCP server",
        "type": "http",
        "url": "https://test-server.com/mcp",
        "auth_type": "none",
        "enabled": True
    })

    assert response.status_code == 201, f"Server creation failed: {response.text}"
    return response.json()


@pytest.fixture
def system_server(authenticated_client) -> Dict:
    """Create a system MCP server for testing protection.

    Note: This fixture creates a regular server and manually marks it as system
    by directly updating the database, since the API doesn't allow creating system servers.
    """
    import asyncio
    import asyncpg

    # Create a regular server first
    response = authenticated_client.post("/api/v1/mcp/servers", json={
        "name": "System Server",
        "description": "A system server for testing",
        "type": "http",
        "url": "https://system-server.com/mcp",
        "auth_type": "none",
        "enabled": True
    })

    assert response.status_code == 201, f"Server creation failed: {response.text}"
    server = response.json()
    server_id = server["id"]

    # Mark it as system server via direct DB update
    async def mark_as_system():
        conn = await get_test_db_connection()
        await conn.execute("""
            UPDATE mcp.servers SET is_system = true WHERE id = $1
        """, server_id)
        await conn.close()

    asyncio.run(mark_as_system())

    # Fetch updated server
    get_response = authenticated_client.get(f"/api/v1/mcp/servers/{server_id}")
    return get_response.json()


@pytest.fixture
def other_user_agent(client, clean_db, test_user) -> Dict:
    """Create an agent belonging to a different user.

    This fixture creates a second user and an agent for them,
    useful for testing authorization and permission checks.
    """
    # Register a second user
    register_response = client.post("/api/v1/auth/register", json={
        "email": OTHER_USER_EMAIL,
        "password": OTHER_USER_PASSWORD,
        "name": OTHER_USER_NAME
    })
    assert register_response.status_code == 201

    # Login as the other user
    login_response = client.post("/api/v1/auth/login", json={
        "email": OTHER_USER_EMAIL,
        "password": OTHER_USER_PASSWORD
    })
    assert login_response.status_code == 200

    # Create an agent as the other user (client has cookies from login)
    # Note: Agent endpoint expects Form data, not JSON
    import json as json_module

    agent_response = client.post("/api/v1/agents", data={
        "name": "Other User Agent",  # No apostrophe - validation requires alphanumeric + space/dash/underscore/dot only
        "description": "An agent belonging to another user",
        "system_prompt": "You are a test assistant",
        "enabled": "true"
    })
    assert agent_response.status_code == 201

    agent_data = agent_response.json()

    # CRITICAL: Restore original user's cookies for authenticated_client
    # Since authenticated_client returns the same client instance,
    # we must re-login as the original user to restore the session
    restore_login = client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": test_user["plain_password"]
    })
    assert restore_login.status_code == 200

    return agent_data


@pytest.fixture
def sample_resource(authenticated_client, sample_agent, test_user) -> Dict:
    """Create a sample resource via database.

    Resources belong to users (not agents). They are linked to agents via configurations.
    Schema: id, name, description, enabled, status, user_id, is_public, etc.
    """
    import asyncio
    from app.core.utils.id_generator import generate_id

    # Resources are created via database since they require complex setup
    async def create_resource():
        conn = await get_test_db_connection()

        # Create a resource with minimal required fields
        resource_id = generate_id('resource')
        await conn.execute("""
            INSERT INTO resources.resources
            (id, user_id, name, description, status, enabled)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, resource_id, test_user["id"], "Test Resource", "A test resource", "ready", True)

        # Fetch the created resource
        resource = await conn.fetchrow("""
            SELECT * FROM resources.resources WHERE id = $1
        """, resource_id)

        await conn.close()
        return dict(resource)

    resource = asyncio.run(create_resource())
    return resource
