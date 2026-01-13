# CRUD Operations Test Suite

Comprehensive integration tests for all 18 CRUD modules covering create, read, update, delete, and list operations.

## Test Coverage

This test suite provides **113 test cases** across **18 CRUD modules**:

1. **users** (13 tests) - User management CRUD operations
2. **agents** (16 tests) - Agent CRUD with tags normalization
3. **chats** (10 tests) - Chat sessions and messages
4. **teams** (6 tests) - Team configuration management
5. **servers** (6 tests) - MCP server management
6. **models** (5 tests) - LLM model operations
7. **services** (5 tests) - LLM service management
8. **resources** (5 tests) - Resource operations by agent
9. **uploads** (5 tests) - File upload tracking
10. **api_keys** (5 tests) - Encrypted API key management
11. **user_providers** (5 tests) - User-service provider credentials
12. **automations** (5 tests) - Automation configuration
13. **logs** (5 tests) - Audit log operations
14. **validations** (5 tests) - Tool validation requests
15. **workflow_steps** (5 tests) - Automation workflow steps
16. **triggers** (5 tests) - Automation triggers
17. **executions** (5 tests) - Automation execution records
18. **refresh_tokens** (5 tests) - Authentication token management

## Test Infrastructure

### Fixtures (conftest.py)

- **test_db_pool**: Session-scoped database connection pool
- **clean_db**: Automatic database cleanup before each test
- **mock_pool_for_crud**: Test pool injection into CRUD modules
- **sample_user**: Pre-created test user
- **sample_agent**: Pre-created test agent
- **sample_service**: Pre-created test LLM service
- **sample_team**: Pre-created test team

### Database Setup

Tests require a PostgreSQL test database with the following environment variables:

```bash
export TEST_DB_HOST=localhost
export TEST_DB_PORT=5432
export TEST_DB_NAME=test_backend
export TEST_DB_USER=postgres
export TEST_DB_PASSWORD=postgres
```

## Running the Tests

### Setup Test Database

1. Create the test database:
```bash
createdb test_backend
```

2. Run migrations on test database:
```bash
python -m app.database.migrations --db test_backend
```

### Run All CRUD Tests

```bash
# Run all CRUD tests
pytest tests/test_crud/ -v

# Run with coverage
pytest tests/test_crud/ --cov=app/database/crud --cov-report=html

# Run specific module tests
pytest tests/test_crud/test_users.py -v

# Run tests in parallel
pytest tests/test_crud/ -n auto
```

### Expected Performance

- **Test Suite Duration**: <60 seconds (target)
- **Test Coverage**: 85%+ for CRUD layer
- **Test Isolation**: Each test runs in clean database state

## Test Patterns

### CREATE Operations
- Valid data insertion
- Constraint violation handling
- Default value verification

### READ Operations
- Get by ID
- Get by filters (email, name, etc.)
- Not found scenarios (return None)

### UPDATE Operations
- Partial updates
- Multiple field updates
- Not found scenarios (return False)

### DELETE Operations
- Successful deletion
- Cascade behavior verification
- Not found scenarios (return False)

### LIST Operations
- Pagination support
- Filtering (enabled/disabled, by user, etc.)
- Ordering verification (most recent first)

## Multi-Schema Support

Tests cover all 6 database schemas:
- **core**: users, api_keys, services, models
- **agents**: agents, teams, memberships
- **chat**: chats, messages
- **mcp**: servers, tools, oauth_tokens
- **resources**: resources, uploads, embeddings
- **audit**: logs, validations

## Connection Pooling Validation

Tests verify database pool usage from Story 0.1:
- Pool acquisition and release
- Connection reuse across operations
- Proper async context manager usage

## Notes

- Tests use **real database transactions** (not mocks)
- Automatic cleanup via CASCADE truncation
- Independent test execution (no shared state)
- Async/await patterns with pytest-asyncio
