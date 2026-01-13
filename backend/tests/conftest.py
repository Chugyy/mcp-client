"""Pytest configuration and shared fixtures for all tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from cryptography.fernet import Fernet

# Patch settings module BEFORE any imports happen to avoid timedelta issues
# This must happen at module level, before test collection
import sys
from unittest.mock import MagicMock as MockClass

# Create a proper settings mock that can be used by oauth_cache
class SettingsMock:
    def __init__(self):
        self.encryption_master_key = Fernet.generate_key().decode()
        self.jwt_secret_key = "test-jwt-secret-key-min-32-chars-long-12345"
        self.jwt_algorithm = "HS256"
        self.db_host = "localhost"
        self.db_port = 5432
        self.db_name = "testdb"
        self.db_user = "testuser"
        self.db_password = "testpassword"
        self.oauth_metadata_cache_ttl = 3600  # INT, not MagicMock
        self.oauth_client_id = "test-client-id"
        self.oauth_client_secret = "test-client-secret"
        self.log_level = "INFO"  # For logger
        self.app_name = "APP - Backend"  # For logger
        self.embedding_model = "text-embedding-3-large"  # For RAG
        self.embedding_dim = 3072  # For RAG
        self.chunk_size = 500  # For RAG chunking
        self.chunk_overlap = 100  # For RAG chunking
        self.openai_api_key = "test-api-key"  # For embeddings

    def __getattr__(self, name):
        # Return sensible defaults for any unknown attributes
        return None


# Patch config.config.settings at module level to prevent import errors
import config.config
config.config.settings = SettingsMock()

# Import oauth_cache to trigger module load with patched settings
import app.core.utils.oauth_cache


@pytest.fixture
def mock_db_pool():
    """Mock asyncpg database pool for unit tests."""
    # Create mock connection
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetchval = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[])

    # Create mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMockContextManager(mock_conn))

    return mock_pool, mock_conn


@pytest.fixture(autouse=True)
def mock_get_pool(mock_db_pool):
    """Auto-mock get_pool() for all tests to avoid database dependency."""
    mock_pool, _ = mock_db_pool

    with patch('app.database.db.get_pool', new_callable=AsyncMock) as mock:
        mock.return_value = mock_pool
        yield mock


@pytest.fixture
def mock_fernet_key():
    """Generate a valid Fernet encryption key for testing."""
    return Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def mock_settings(mock_fernet_key):
    """Auto-mock settings for all tests."""
    # Need to patch where settings is imported, not where it's defined
    patches = [
        patch('app.core.utils.auth.settings'),
        patch('app.core.utils.encryption.settings'),
        patch('config.config.settings'),
        patch('app.core.utils.oauth_cache.settings'),
        patch('config.logger.settings')
    ]

    with patches[0] as mock_auth_settings, \
         patches[1] as mock_encrypt_settings, \
         patches[2] as mock_config_settings, \
         patches[3] as mock_oauth_cache_settings, \
         patches[4] as mock_logger_settings:

        # Configure all mocks the same way
        for mock in [mock_auth_settings, mock_encrypt_settings, mock_config_settings, mock_oauth_cache_settings, mock_logger_settings]:
            mock.encryption_master_key = mock_fernet_key
            mock.jwt_secret_key = "test-jwt-secret-key-min-32-chars-long-12345"
            mock.jwt_algorithm = "HS256"
            mock.db_host = "localhost"
            mock.db_port = 5432
            mock.db_name = "testdb"
            mock.db_user = "testuser"
            mock.db_password = "testpassword"
            mock.oauth_metadata_cache_ttl = 3600  # Add this for oauth_cache
            mock.oauth_client_id = "test-client-id"
            mock.oauth_client_secret = "test-client-secret"
            mock.log_level = "INFO"  # For logger
            mock.app_name = "APP - Backend"  # For logger
            mock.embedding_model = "text-embedding-3-large"  # For RAG
            mock.embedding_dim = 3072  # For RAG
            mock.chunk_size = 500  # For RAG chunking
            mock.chunk_overlap = 100  # For RAG chunking

        yield mock_auth_settings


class AsyncMockContextManager:
    """Helper class to create async context manager from mock."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# ============================================================================
# MCP Test Fixtures
# ============================================================================

@pytest.fixture
async def mock_mcp_server():
    """Mock MCP server process for testing."""
    import subprocess
    import asyncio
    import os

    # Get path to mock server
    mock_server_path = os.path.join(
        os.path.dirname(__file__),
        "mocks",
        "mock_mcp_server.py"
    )

    # Start mock server process
    process = subprocess.Popen(
        ["python", mock_server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    # Wait for server ready (read initialized notification)
    await asyncio.sleep(0.5)

    yield process

    # Cleanup
    try:
        process.terminate()
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest.fixture
def sample_server_config():
    """Sample MCP server configuration for stdio."""
    import os

    mock_server_path = os.path.join(
        os.path.dirname(__file__),
        "mocks",
        "mock_mcp_server.py"
    )

    return {
        "name": "Test Server",
        "description": "Mock MCP server for testing",
        "type": "stdio",
        "command": "python",
        "args": [mock_server_path],
        "env": {"TEST_MODE": "true"},
        "timeout": 30
    }


@pytest.fixture
def sample_http_server_config():
    """Sample HTTP MCP server configuration."""
    return {
        "name": "Test HTTP Server",
        "description": "Mock HTTP MCP server for testing",
        "type": "http",
        "url": "http://localhost:8080/mcp",
        "auth_type": "none",
        "timeout": 30
    }


# ============================================================================
# Real Database Fixtures (for integration tests)
# ============================================================================

@pytest.fixture(scope="function")
async def db_pool_test():
    """Real asyncpg pool connected to test database."""
    import asyncpg
    import app.database.db as db_module

    pool = await asyncpg.create_pool(
        host="localhost",
        port=5432,
        database="ai_client_db_test",
        user="hugohoarau",
        password="",
        min_size=1,
        max_size=5,
        # Set search_path to include all schemas
        server_settings={'search_path': 'mcp,agents,chat,core,resources,automation,audit,public'}
    )

    # Set test pool globally so get_pool() uses it
    db_module._test_pool = pool

    yield pool

    # Clean up
    db_module._test_pool = None
    await pool.close()


@pytest.fixture
async def db_server(db_pool_test):
    """Create test Server in real DB and return model."""
    from app.core.utils.id_generator import generate_id

    server_id = generate_id('server')

    async with db_pool_test.acquire() as conn:
        # Create server (user_id is nullable, so use NULL for test isolation)
        await conn.execute(
            """INSERT INTO mcp.servers
               (id, name, description, type, url, auth_type, enabled, status, user_id, is_system, args, env)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb)""",
            server_id,
            "Integration Test Server",
            "Server for integration testing",
            "http",
            "http://localhost:8080",
            "none",
            True,
            "active",
            None,  # user_id is nullable
            False,
            "[]",
            "{}"
        )

        # Fetch and return
        result = await conn.fetchrow("SELECT * FROM mcp.servers WHERE id = $1", server_id)
        server = dict(result)

    yield server

    # Cleanup
    async with db_pool_test.acquire() as conn:
        await conn.execute("DELETE FROM mcp.servers WHERE id = $1", server_id)


@pytest.fixture
async def db_tool(db_pool_test, db_server):
    """Create test Tool in real DB and return model."""
    from app.core.utils.id_generator import generate_id

    tool_id = generate_id('tool')
    server_id = db_server['id']

    async with db_pool_test.acquire() as conn:
        # Create tool (no input_schema column in actual DB)
        await conn.execute(
            """INSERT INTO mcp.tools
               (id, server_id, name, description, enabled)
               VALUES ($1, $2, $3, $4, $5)""",
            tool_id,
            server_id,
            "test_integration_tool",
            "Tool for integration testing",
            True
        )

        # Fetch and return
        result = await conn.fetchrow("SELECT * FROM mcp.tools WHERE id = $1", tool_id)
        tool = dict(result)

    yield tool

    # Cleanup
    async with db_pool_test.acquire() as conn:
        await conn.execute("DELETE FROM mcp.tools WHERE id = $1", tool_id)


@pytest.fixture
async def db_test_user(db_pool_test):
    """Create test user in real DB for agents that require user_id."""
    from app.core.utils.id_generator import generate_id

    user_id = "test-user-" + generate_id('user')[:8]

    async with db_pool_test.acquire() as conn:
        # Create test user
        await conn.execute(
            """INSERT INTO core.users
               (id, email, password, name)
               VALUES ($1, $2, $3, $4)""",
            user_id,
            f"{user_id}@test.com",
            "hashed_password_for_tests",
            "Test User"
        )

    yield user_id

    # Cleanup
    async with db_pool_test.acquire() as conn:
        await conn.execute("DELETE FROM core.users WHERE id = $1", user_id)


@pytest.fixture
async def db_agent(db_pool_test, db_test_user):
    """Create test Agent in real DB and return model."""
    from app.core.utils.id_generator import generate_id

    agent_id = generate_id('agent')

    async with db_pool_test.acquire() as conn:
        # Create agent (user_id is NOT nullable for agents)
        await conn.execute(
            """INSERT INTO agents.agents
               (id, user_id, name, description, system_prompt, enabled)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            agent_id,
            db_test_user,  # Use test user
            "Integration Test Agent",
            "Agent for integration testing",
            "You are a test agent.",
            True
        )

        # Fetch and return
        result = await conn.fetchrow("SELECT * FROM agents.agents WHERE id = $1", agent_id)
        agent = dict(result)

    yield agent

    # Cleanup
    async with db_pool_test.acquire() as conn:
        await conn.execute("DELETE FROM agents.agents WHERE id = $1", agent_id)


# ============================================================================
# Mock Simplification Fixtures
# ============================================================================

@pytest.fixture
def mock_validators():
    """Mock all ServerValidator methods at once to simplify test setup."""
    with patch.multiple(
        'app.core.validators.mcp.ServerValidator',
        validate_type=MagicMock(return_value=(True, None)),
        validate_name_unique=AsyncMock(),
        validate_config=MagicMock(return_value=(True, None)),
        validate_server_quota=AsyncMock()
    ) as mocks:
        yield mocks


@pytest.fixture
def mock_create_server():
    """Mock create_server CRUD function for server creation tests."""
    with patch('app.database.crud.create_server', new_callable=AsyncMock) as mock:
        mock.return_value = "test-server-id"
        yield mock
